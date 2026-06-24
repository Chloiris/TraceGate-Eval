from __future__ import annotations

import re


def estimate_tokens(text: str) -> int:
    """Cheap token estimate that behaves reasonably for mixed Chinese/English text."""
    cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    punctuation = len(re.findall(r"[^\w\s\u4e00-\u9fff]", text))
    return max(1, cjk_chars + latin_words + punctuation // 4) if text.strip() else 0

