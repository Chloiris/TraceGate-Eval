#!/usr/bin/env python3
"""Fail when tracked source contains credential material, without printing values."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIPPED_NAMES = {"pnpm-lock.yaml", "uv.lock", "Cargo.lock"}
PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+)?PRIVATE KEY-----"),
    "GitHub token": re.compile(
        rb"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[opsru]_[A-Za-z0-9]{30,})\b"
    ),
    "OpenAI-compatible API key": re.compile(
        rb"\b(?:sk-proj-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,})\b"
    ),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "provider API key assignment": re.compile(
        rb"(?i)\b(?:DEEPSEEK|OPENAI|TRACEGATE_LLM)_API_KEY[ \t]*=[ \t]*['\"]?[A-Za-z0-9_-]{20,}"
    ),
}
SUSPICIOUS_FILENAMES = (
    re.compile(r"(^|/)\.env(?:\.|$)", re.IGNORECASE),
    re.compile(r"(^|/)id_(?:rsa|dsa|ecdsa|ed25519)(?:\.|$)", re.IGNORECASE),
    re.compile(r"(^|/)(?:credentials|secrets?)(?:\.(?:json|ya?ml))?$", re.IGNORECASE),
    re.compile(r"\.(?:db|sqlite3?|log|pem|p12|pfx|key)$", re.IGNORECASE),
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def scan() -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.name in SKIPPED_NAMES:
            continue
        if relative != ".env.example" and any(
            pattern.search(relative) for pattern in SUSPICIOUS_FILENAMES
        ):
            findings.append((relative, "sensitive filename"))
        try:
            content = path.read_bytes()
        except OSError:
            continue
        if b"\0" in content[:4096]:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append((relative, label))
    return findings


def main() -> int:
    findings = scan()
    for relative, label in findings:
        print(f"{relative}: possible {label}; value suppressed")
    if findings:
        print(f"secret hygiene failed with {len(findings)} finding(s)")
        return 1
    print("secret hygiene passed for tracked files and non-binary contents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
