from __future__ import annotations

from fastapi.testclient import TestClient

from tracegate.web.app import app


client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_returns_project_name() -> None:
    response = client.get("/api/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["project_name"] == "TraceGate Eval"
    assert body["total_runs"] == 160


def test_context_groups_returns_non_empty_list() -> None:
    response = client.get("/api/context-groups")
    assert response.status_code == 200
    body = response.json()
    assert body
    assert body[0]["name"]


def test_evidence_status_returns_non_empty_list() -> None:
    response = client.get("/api/evidence-status")
    assert response.status_code == 200
    body = response.json()
    assert body
    assert {item["evidence_status"] for item in body} >= {"active", "stale", "unknown", "conflicting"}


def test_analyze_demo_returns_decision_and_plan() -> None:
    response = client.post(
        "/api/analyze-demo",
        json={
            "claim": "Payment signature verification must keep using amountInCent.",
            "evidence": "The migration record is unavailable and no owner has confirmed the canonical amount unit.",
            "context_group": "tracegate_verify_first",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["suggested_decision"] == "verify_first"
    assert body["verification_plan"]

