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


@pytest.mark.asyncio
async def test_provider_streams_structured_output_and_records_usage() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        assert '"stream":true' in body
        assert '"include_usage":true' in body
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                'data: {"choices":[{"delta":{"content":"{\\"verdict\\":"}}]}\n\n'
                'data: {"choices":[{"delta":{"content":"\\"verified\\"}"}}]}\n\n'
                'data: {"choices":[],"usage":{"prompt_tokens":9,"completion_tokens":3}}\n\n'
                "data: [DONE]\n\n"
            ).encode(),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://model.test/v1/")
    provider = OpenAICompatibleProvider(
        api_key=SecretStr("provider-secret-for-test"),
        base_url="https://model.test/v1",
        model="real-model",
        streaming_enabled=True,
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
    assert result.payload == {"verdict": "verified"}
    assert result.input_tokens == 9
    assert result.output_tokens == 3
    assert result.provider_mode == "compatibility_json_streaming"


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
async def test_provider_tool_selection_labels_native_and_compatibility_modes(native: bool) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if native:
            assert '"tools"' in body
            message = {
                "tool_calls": [
                    {"function": {"name": "search_code", "arguments": '{"query":"token"}'}}
                ]
            }
        else:
            assert "compatibility mode" in body
            message = {"content": '{"tool_name":"search_code","arguments":{"query":"token"}}'}
        return httpx.Response(
            200,
            json={"choices": [{"message": message}], "usage": {"prompt_tokens": 7, "completion_tokens": 2}},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://model.test/")
    provider = OpenAICompatibleProvider(
        api_key=SecretStr("provider-secret-for-test"),
        base_url="https://model.test",
        model="real-model",
        native_tool_calling=native,
        client=client,
    )
    try:
        result = await provider.select_tool(
            system_prompt="Choose a bounded retrieval tool.",
            user_prompt="Find token validation.",
            tools=[
                {
                    "name": "search_code",
                    "description": "Search indexed source.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
                }
            ],
        )
    finally:
        await client.aclose()
    assert result.tool_call is not None
    assert result.tool_call.name == "search_code"
    assert result.tool_call.arguments == {"query": "token"}
    assert result.provider_mode == ("native_tool_calling" if native else "compatibility_tool_selection")
