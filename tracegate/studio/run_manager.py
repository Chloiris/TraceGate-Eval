from __future__ import annotations

import asyncio
import logging
import os

from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from tracegate.agent import TraceGateAgentWorkflow, WorkflowCancelled
from tracegate.models import ModelConfigurationError, OpenAICompatibleProvider
from tracegate.tools import create_read_only_registry

from .models import AgentRun, AppSettings


logger = logging.getLogger("tracegate.studio.runs")


def configured_model(session: Session) -> OpenAICompatibleProvider:
    settings = session.get(AppSettings, 1)
    if settings is None or not settings.model_provider or not settings.model_name:
        raise ModelConfigurationError("Model provider and model name are not configured")
    api_key = os.environ.get("TRACEGATE_LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ModelConfigurationError("Model credential is not configured")
    provider = settings.model_provider.casefold()
    base_url = settings.model_base_url
    if provider == "deepseek" and not base_url:
        base_url = "https://api.deepseek.com"
    if not base_url:
        raise ModelConfigurationError("Custom model providers require an explicit Base URL")
    return OpenAICompatibleProvider(
        api_key=SecretStr(api_key),
        base_url=base_url,
        model=settings.model_name,
        native_structured_output=False,
    )


class RunManager:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self._tasks: dict[str, asyncio.Task[object]] = {}

    def start(self, run_id: str, model: OpenAICompatibleProvider) -> None:
        existing = self._tasks.get(run_id)
        if existing and not existing.done():
            return
        workflow = TraceGateAgentWorkflow(
            self.session_factory,
            model,
            create_read_only_registry(),
        )
        task = asyncio.create_task(workflow.run(run_id), name=f"tracegate-run-{run_id}")
        self._tasks[run_id] = task
        task.add_done_callback(lambda completed, key=run_id: self._finished(key, completed))

    def cancel(self, run_id: str) -> bool:
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run is None or run.status in {"completed", "failed", "cancelled"}:
                return False
            run.cancellation_requested = True
            session.commit()
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        return True

    def active_count(self) -> int:
        return sum(1 for task in self._tasks.values() if not task.done())

    async def shutdown(self) -> None:
        tasks = [task for task in self._tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def _finished(self, run_id: str, task: asyncio.Task[object]) -> None:
        self._tasks.pop(run_id, None)
        try:
            task.result()
        except (WorkflowCancelled, asyncio.CancelledError):
            logger.info("agent_run_cancelled run_id=%s", run_id)
        except Exception as exc:
            logger.error("agent_run_failed run_id=%s error_type=%s", run_id, type(exc).__name__)
        else:
            logger.info("agent_run_completed run_id=%s", run_id)
