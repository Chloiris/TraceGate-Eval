from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from tracegate.github import GitHubDeviceFlow, GitHubOAuthError


@pytest.mark.asyncio
async def test_device_flow_keeps_device_and_access_tokens_out_of_public_response() -> None:
    responses = iter(
        [
            {
                "device_code": "device-code-secret-material",
                "user_code": "ABCD-EFGH",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 5,
            },
            {"error": "authorization_pending"},
            {
                "access_token": "github-access-token-secret-material",
                "token_type": "bearer",
                "scope": "repo",
            },
        ]
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=next(responses))

    client = httpx.AsyncClient(
        base_url="https://github.com",
        transport=httpx.MockTransport(handler),
    )
    stored: list[SecretStr] = []
    flow = GitHubDeviceFlow("client-id-123", stored.append, client=client)
    session = await flow.begin()
    public = session.public.model_dump(mode="json")
    assert public["user_code"] == "ABCD-EFGH"
    assert "device_code" not in public
    assert "token" not in json.dumps(public).casefold()

    assert await flow.poll(session) == "pending"
    with pytest.raises(GitHubOAuthError) as too_fast:
        await flow.poll(session)
    assert too_fast.value.code == "poll_interval"
    session.next_poll_monotonic = 0
    assert await flow.poll(session) == "authorized"
    assert stored[0].get_secret_value() == "github-access-token-secret-material"
    assert all(b"device-code-secret-material" not in request.url.raw_path for request in requests)
    await client.aclose()
