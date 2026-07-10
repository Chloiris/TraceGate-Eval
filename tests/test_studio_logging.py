from __future__ import annotations

import json
import logging
from pathlib import Path

from tracegate.studio.logging_config import (
    LOG_BACKUP_COUNT,
    MAX_LOG_BYTES,
    JsonRedactingFormatter,
    create_rotating_handler,
    redact_text,
)


def test_redaction_removes_bearer_and_provider_credentials() -> None:
    token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    message = f"Authorization: Bearer {token} api_key=sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    redacted = redact_text(message)
    assert token not in redacted
    assert "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in redacted
    assert redacted.count("<redacted>") == 2


def test_json_formatter_uses_structured_bounded_fields() -> None:
    record = logging.LogRecord(
        name="tracegate.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="token=%s",
        args=("secret-value-that-must-not-survive",),
        exc_info=None,
    )
    payload = json.loads(JsonRedactingFormatter().format(record))
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "tracegate.test"
    assert payload["event"] == "token=<redacted>"
    assert payload["timestamp"].endswith("+00:00")


def test_rotating_handler_has_finite_retention(tmp_path: Path) -> None:
    handler = create_rotating_handler(tmp_path)
    try:
        assert handler.maxBytes == MAX_LOG_BYTES
        assert handler.backupCount == LOG_BACKUP_COUNT
        assert Path(handler.baseFilename).parent == tmp_path
    finally:
        handler.close()
