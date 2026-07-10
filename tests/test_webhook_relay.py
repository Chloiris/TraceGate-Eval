from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ADMIN_TOKEN = "admin-token-that-is-at-least-thirty-two-characters"
GITHUB_SECRET = "github-secret-that-is-at-least-thirty-two-chars"


def _load_relay_module():
    path = Path(__file__).parents[1] / "services" / "webhook-relay" / "app.py"
    spec = importlib.util.spec_from_file_location("tracegate_webhook_relay", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _signature(body: bytes) -> str:
    return "sha256=" + hmac.new(GITHUB_SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_pairing_is_one_time_and_webhook_is_authenticated_deduplicated_and_scoped() -> None:
    relay = _load_relay_module()
    app = relay.create_app(admin_token=ADMIN_TOKEN, github_secret=GITHUB_SECRET)
    client = TestClient(app)

    unauthorized = client.post("/v1/pairing-codes", json={"repositories": ["acme/repo"]})
    assert unauthorized.status_code == 401
    pairing = client.post(
        "/v1/pairing-codes",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"repositories": ["acme/repo"]},
    )
    assert pairing.status_code == 200
    code = pairing.json()["pairing_code"]
    paired = client.post(
        "/v1/devices/pair",
        json={"pairing_code": code, "device_id": "macbook.local"},
    )
    assert paired.status_code == 200
    token = paired.json()["device_token"]
    assert len(token) >= 48
    replay_pairing = client.post(
        "/v1/devices/pair",
        json={"pairing_code": code, "device_id": "other-device"},
    )
    assert replay_pairing.status_code == 401
    assert client.get("/v1/events").status_code == 401

    payload = {
        "action": "synchronize",
        "repository": {"full_name": "acme/repo"},
        "pull_request": {"number": 7, "head": {"sha": "a" * 40}},
        "sender": {"login": "octocat"},
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "X-GitHub-Delivery": "delivery-1",
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": _signature(body),
        "Content-Type": "application/json",
    }
    assert client.post("/v1/github", headers={**headers, "X-Hub-Signature-256": "sha256=bad"}, content=body).status_code == 401
    delivered = client.post("/v1/github", headers=headers, content=body)
    assert delivered.status_code == 200
    assert delivered.json() == {"accepted": True, "duplicate": False, "delivered_devices": 1}
    duplicate = client.post("/v1/github", headers=headers, content=body)
    assert duplicate.json() == {"accepted": True, "duplicate": True, "delivered_devices": 0}
    device = app.state.relay.authenticate_device(f"Bearer {token}")
    queued = device.queue.get_nowait()
    assert queued["repository"] == "acme/repo"
    assert queued["head_sha"] == "a" * 40
    assert "access_token" not in json.dumps(queued)

    different = json.dumps({**payload, "action": "closed"}, separators=(",", ":")).encode()
    mismatch = client.post(
        "/v1/github",
        headers={**headers, "X-Hub-Signature-256": _signature(different)},
        content=different,
    )
    assert mismatch.status_code == 409


def test_webhook_rejects_unsupported_events_and_unknown_repository_subscriptions() -> None:
    relay = _load_relay_module()
    app = relay.create_app(admin_token=ADMIN_TOKEN, github_secret=GITHUB_SECRET)
    client = TestClient(app)
    body = b'{"repository":{"full_name":"other/repo"}}'
    unsupported = client.post(
        "/v1/github",
        headers={
            "X-GitHub-Delivery": "delivery-2",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": _signature(body),
        },
        content=body,
    )
    assert unsupported.status_code == 422
