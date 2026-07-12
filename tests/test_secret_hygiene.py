from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.check_secret_hygiene import PATTERNS, SUSPICIOUS_FILENAMES


def _labels(value: bytes) -> set[str]:
    return {label for label, pattern in PATTERNS.items() if pattern.search(value)}


def test_secret_patterns_cover_current_provider_and_fine_grained_tokens() -> None:
    assert "GitHub token" in _labels(b"github_pat_" + b"A" * 32)
    assert "OpenAI-compatible API key" in _labels(b"sk-" + b"a1" * 20)
    assert "AWS access key" in _labels(b"AKIA" + b"A1" * 8)
    assert "provider API key assignment" in _labels(
        b"DEEPSEEK_API_KEY=" + b"z" * 32
    )


def test_secret_patterns_do_not_reject_documented_variable_names() -> None:
    assert _labels(b"DEEPSEEK_API_KEY=configured") == set()
    assert _labels(b"export TRACEGATE_LLM_API_KEY") == set()
    assert _labels(b"sk-<redacted>") == set()


def test_sensitive_filename_patterns_cover_credentials_and_local_data() -> None:
    blocked = (
        ".env.local",
        "config/credentials.json",
        "keys/id_ed25519",
        "state/studio.sqlite3",
        "logs/model.log",
        "certs/signing.p12",
    )
    for path in blocked:
        assert any(pattern.search(path) for pattern in SUSPICIOUS_FILENAMES), path
