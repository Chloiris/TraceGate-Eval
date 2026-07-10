from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from tracegate.models import ModelProviderError, OpenAICompatibleProvider


class Answer(BaseModel):
    verdict: str


@pytest.mark.asyncio
async def test_compatible_provider_validates_structured_output_and_usage() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["authorization"] == "Bearer provider-secret-for-test"
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"verdict":"verified"}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://model.test/v1/")
    provider = OpenAICompatibleProvider(
        api_key=SecretStr("provider-secret-for-test"),
        base_url="https://model.test/v1",
        model="real-model",
        client=client,
    )
    try:
        result = await provider.complete_structured(
            system_prompt="Review evidence.",
            user_prompt="UNTRUSTED_EVIDENCE\ncode",
            output_schema=Answer,
        )
    finally:
        await client.aclose()
    assert calls == 1
    assert result.payload == {"verdict": "verified"}
    assert result.input_tokens == 12
    assert result.provider_mode == "compatibility_json"


@pytest.mark.asyncio
async def test_provider_fails_on_invalid_output_without_rule_fallback() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://model.test")
    provider = OpenAICompatibleProvider(
        api_key=SecretStr("provider-secret-for-test"),
        base_url="https://model.test",
        model="real-model",
        client=client,
    )
    try:
        with pytest.raises(ModelProviderError, match="invalid structured output"):
            await provider.complete_structured(
                system_prompt="Review evidence.",
                user_prompt="UNTRUSTED_EVIDENCE\ncode",
                output_schema=Answer,
            )
    finally:
        await client.aclose()
