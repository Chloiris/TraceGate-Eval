from __future__ import annotations

import pytest

from tracegate.studio.cli import build_parser, run
from tracegate.studio.config import StudioConfigurationError, StudioSettings
from tracegate.studio.parent_watchdog import (
    parent_process_is_alive,
    process_is_alive,
    start_parent_watchdog,
)


def test_sidecar_settings_use_env_contract_and_redact_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "env-sidecar-token-0123456789-abcdef"
    monkeypatch.setenv("TRACEGATE_LOCAL_API_TOKEN", token)
    monkeypatch.setenv("TRACEGATE_HOST", "127.0.0.1")
    monkeypatch.setenv("TRACEGATE_PORT", "49152")
    settings = StudioSettings.from_env()
    assert settings.host == "127.0.0.1"
    assert settings.port == 49152
    assert settings.local_api_token.get_secret_value() == token
    assert token not in repr(settings)


def test_sidecar_requires_token_and_rejects_non_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRACEGATE_LOCAL_API_TOKEN", raising=False)
    with pytest.raises(StudioConfigurationError, match="required"):
        StudioSettings.from_env()

    monkeypatch.setenv("TRACEGATE_LOCAL_API_TOKEN", "loopback-test-token-0123456789-abcdef")
    monkeypatch.setenv("TRACEGATE_HOST", "0.0.0.0")
    with pytest.raises(StudioConfigurationError, match="127.0.0.1"):
        StudioSettings.from_env()


def test_sidecar_cli_has_no_token_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["serve", "--token", "must-not-enter-process-list"])

    monkeypatch.delenv("TRACEGATE_LOCAL_API_TOKEN", raising=False)
    assert run(["health"]) == 2


def test_parent_watchdog_is_opt_in_and_current_parent_is_alive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    monkeypatch.delenv("TRACEGATE_PARENT_WATCHDOG", raising=False)
    assert start_parent_watchdog() is None
    assert parent_process_is_alive(os.getppid()) is True
    assert process_is_alive(os.getpid()) is True
    assert parent_process_is_alive(1) is False
