from __future__ import annotations


class AutofixError(RuntimeError):
    """A stable, user-visible Autofix failure without secret-bearing detail."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
