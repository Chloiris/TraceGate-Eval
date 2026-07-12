from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from tracegate.repository import RepositoryBoundary, RepositoryPathError

from .errors import AutofixError
from .schemas import PatchInspection


@dataclass(frozen=True)
class PatchLimits:
    max_files: int = 8
    max_changed_lines: int = 800
    max_changed_lines_per_file: int = 400

    def __post_init__(self) -> None:
        if not 1 <= self.max_files <= 32:
            raise ValueError("max_files must be between 1 and 32")
        if not 1 <= self.max_changed_lines <= 5_000:
            raise ValueError("max_changed_lines must be between 1 and 5000")
        if not 1 <= self.max_changed_lines_per_file <= self.max_changed_lines:
            raise ValueError("per-file changed-line limit is invalid")


_DIFF_PATH = re.compile(r"^(?:---|\+\+\+) ([^\t]+)")
_SENSITIVE_SUFFIXES = {
    ".cer",
    ".crt",
    ".db",
    ".der",
    ".key",
    ".keystore",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
}
_SENSITIVE_NAMES = {
    ".git",
    ".gitconfig",
    ".npmrc",
    ".pypirc",
    "authorized_keys",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
    "netrc",
    "secrets",
    "secrets.json",
}
_SENSITIVE_PARTS = {".aws", ".azure", ".git", ".gnupg", ".kube", ".ssh", "gcloud"}
_CONFIG_NAMES = {
    "cargo.toml",
    "dockerfile",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "settings.gradle",
    "settings.gradle.kts",
}
_LOCKFILE_NAMES = {
    "cargo.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}


def normalize_patch(patch: str) -> str:
    if "\x00" in patch:
        raise AutofixError("fix_patch_unsafe", "Patch contains a NUL byte")
    normalized = patch.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        raise AutofixError("fix_patch_missing", "Patch is empty")
    return normalized.rstrip("\n") + "\n"


def compute_patch_hash(patch: str) -> str:
    return hashlib.sha256(normalize_patch(patch).encode("utf-8")).hexdigest()


def _clean_diff_path(raw_path: str) -> str | None:
    if raw_path == "/dev/null":
        return None
    if raw_path.startswith('"') or raw_path.endswith('"'):
        raise AutofixError("fix_patch_unsafe", "Quoted diff paths are not supported")
    if raw_path.startswith(("a/", "b/")):
        raw_path = raw_path[2:]
    pure = PurePosixPath(raw_path)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise AutofixError("fix_patch_unsafe", "Patch contains an absolute or traversing path")
    return pure.as_posix()


def _is_sensitive_path(relative_path: str) -> bool:
    pure = PurePosixPath(relative_path)
    lowered = [part.casefold() for part in pure.parts]
    name = lowered[-1]
    return (
        any(part in _SENSITIVE_PARTS for part in lowered)
        or name == ".env"
        or name.startswith(".env.")
        or name in _SENSITIVE_NAMES
        or name.startswith(("secret.", "secrets."))
        or PurePosixPath(name).suffix.casefold() in _SENSITIVE_SUFFIXES
    )


def _reject_symlink_path(boundary: RepositoryBoundary, relative_path: str) -> None:
    candidate = boundary.root
    for part in PurePosixPath(relative_path).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise AutofixError("fix_patch_unsafe", "Patch targets a symbolic link")
        if not candidate.exists():
            break


def _filtered_git_environment() -> dict[str, str]:
    allowed = ("LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TEMP", "TMP")
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


class PatchSafetyValidator:
    def __init__(self, boundary: RepositoryBoundary, limits: PatchLimits | None = None) -> None:
        self.boundary = boundary
        self.limits = limits or PatchLimits()

    def validate(
        self,
        patch: str,
        *,
        expected_head_sha: str,
        expected_files: list[str] | None = None,
        require_clean: bool = True,
    ) -> PatchInspection:
        normalized = normalize_patch(patch)
        if "GIT binary patch" in normalized or "Binary files " in normalized:
            raise AutofixError("fix_patch_unsafe", "Binary patches are forbidden")
        if "diff --cc " in normalized or "diff --combined " in normalized:
            raise AutofixError("fix_patch_unsafe", "Combined diffs are not supported")

        current_file: str | None = None
        changed_files: list[str] = []
        additions = 0
        deletions = 0
        per_file: dict[str, int] = {}
        deleted_files: set[str] = set()
        previous_header: str | None = None

        for line in normalized.splitlines():
            matched = _DIFF_PATH.match(line)
            if matched:
                raw_path = matched.group(1)
                cleaned = _clean_diff_path(raw_path)
                if line.startswith("--- "):
                    previous_header = cleaned
                    continue
                current_file = cleaned or previous_header
                if cleaned is None and previous_header is not None:
                    deleted_files.add(previous_header)
                if current_file is not None and current_file not in changed_files:
                    changed_files.append(current_file)
                continue
            if current_file is None or line.startswith(("+++", "---")):
                continue
            if line.startswith("+"):
                additions += 1
                per_file[current_file] = per_file.get(current_file, 0) + 1
            elif line.startswith("-"):
                deletions += 1
                per_file[current_file] = per_file.get(current_file, 0) + 1

        if not changed_files:
            raise AutofixError("fix_patch_unsafe", "Patch has no bounded file headers")
        if len(changed_files) > self.limits.max_files:
            raise AutofixError(
                "fix_patch_unsafe",
                f"Patch changes {len(changed_files)} files; the limit is {self.limits.max_files}",
            )
        changed_lines = additions + deletions
        if changed_lines == 0 or changed_lines > self.limits.max_changed_lines:
            raise AutofixError(
                "fix_patch_unsafe",
                f"Patch changes {changed_lines} lines; the limit is {self.limits.max_changed_lines}",
            )
        oversized = [path for path, count in per_file.items() if count > self.limits.max_changed_lines_per_file]
        if oversized:
            raise AutofixError(
                "fix_patch_unsafe",
                f"Patch exceeds the per-file line limit for {oversized[0]}",
            )

        expected = set(expected_files or [])
        if expected and expected != set(changed_files):
            raise AutofixError(
                "fix_patch_unsafe",
                "Patch file headers do not match the structured changed_files list",
            )

        warnings: list[str] = []
        for relative_path in changed_files:
            if _is_sensitive_path(relative_path):
                raise AutofixError("fix_patch_unsafe", f"Patch targets sensitive path {relative_path}")
            _reject_symlink_path(self.boundary, relative_path)
            try:
                absolute = self.boundary.resolve(relative_path, allow_missing=True)
            except RepositoryPathError as exc:
                raise AutofixError("fix_patch_unsafe", str(exc)) from exc
            if absolute.exists() and absolute.is_file():
                raw = absolute.read_bytes()[:4096]
                if b"\x00" in raw:
                    raise AutofixError("fix_patch_unsafe", f"Patch targets binary file {relative_path}")
            lowered = relative_path.casefold()
            name = PurePosixPath(lowered).name
            if relative_path in deleted_files:
                warnings.append(f"deletes file: {relative_path}")
            if name in _LOCKFILE_NAMES:
                warnings.append(f"changes lockfile: {relative_path}")
            if name in _CONFIG_NAMES or "/.github/" in f"/{lowered}/" or lowered.startswith(".github/"):
                warnings.append(f"changes configuration or CI: {relative_path}")
            if any(part in lowered for part in ("auth", "security", "permission", "credential")):
                warnings.append(f"changes security-sensitive code: {relative_path}")

        head = self._git("rev-parse", "HEAD").stdout.strip()
        if head != expected_head_sha:
            raise AutofixError("fix_head_stale", "Fix workspace Head SHA no longer matches the proposal")
        if require_clean and self._git("status", "--porcelain").stdout.strip():
            raise AutofixError("fix_workspace_unavailable", "Fix workspace is not clean before patch validation")

        process = subprocess.run(
            ["git", "-C", str(self.boundary.root), "apply", "--check", "--whitespace=nowarn", "-"],
            input=normalized,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            env=_filtered_git_environment(),
            check=False,
        )
        if process.returncode != 0:
            raise AutofixError(
                "fix_patch_unsafe",
                process.stderr[:2_000].strip() or "git apply --check rejected the patch",
            )
        return PatchInspection(
            patch_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            changed_files=changed_files,
            changed_lines=changed_lines,
            additions=additions,
            deletions=deletions,
            warnings=list(dict.fromkeys(warnings)),
            requires_confirmation=True,
        )

    def apply(self, patch: str, *, expected_head_sha: str) -> None:
        normalized = normalize_patch(patch)
        head = self._git("rev-parse", "HEAD").stdout.strip()
        if head != expected_head_sha:
            raise AutofixError("fix_head_stale", "Fix workspace Head SHA changed before apply")
        process = subprocess.run(
            ["git", "-C", str(self.boundary.root), "apply", "--whitespace=nowarn", "-"],
            input=normalized,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            env=_filtered_git_environment(),
            check=False,
        )
        if process.returncode != 0:
            raise AutofixError(
                "fix_patch_apply_failed",
                process.stderr[:2_000].strip() or "git apply rejected the confirmed patch",
            )

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            ["git", "-C", str(self.boundary.root), *arguments],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=20,
            env=_filtered_git_environment(),
            check=False,
        )
        if process.returncode != 0:
            raise AutofixError(
                "fix_workspace_unavailable",
                process.stderr[:2_000].strip() or "Git workspace check failed",
            )
        return process
