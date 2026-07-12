from __future__ import annotations

import hashlib
import os
import re
import subprocess
from collections.abc import Callable
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
_DIFF_GIT_PATHS = re.compile(r"^diff --git (\S+) (\S+)$")
_UNSUPPORTED_DIFF_METADATA = re.compile(
    r"^(?:old mode|new mode|similarity index|dissimilarity index|"
    r"rename from|rename to|copy from|copy to) "
)
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
_MAX_EOL_INSPECTION_BYTES = 1_048_576


def normalize_patch(patch: str) -> str:
    if "\x00" in patch:
        raise AutofixError("fix_patch_unsafe", "Patch contains a NUL byte")
    normalized = patch.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        raise AutofixError("fix_patch_missing", "Patch is empty")
    return normalized.rstrip("\n") + "\n"


def compute_patch_hash(patch: str) -> str:
    return hashlib.sha256(normalize_patch(patch).encode("utf-8")).hexdigest()


def prepare_patch_bytes(
    patch: str,
    boundary: RepositoryBoundary,
    *,
    content_loader: Callable[[str], bytes | None] | None = None,
) -> bytes:
    """Preserve a target file's uniform LF/CRLF convention without relaxing context.

    Model and API patches are normalized to LF for a stable confirmation hash. Git
    blobs may legitimately contain CRLF, especially on Windows. Rather than asking
    ``git apply`` to ignore whitespace, adapt only hunk-body line terminators to the
    existing target file and keep every context byte otherwise exact.
    """
    normalized = normalize_patch(patch)
    output: list[bytes] = []
    previous_path: str | None = None
    target_eol = b"\n"
    in_hunk = False

    for line in normalized.splitlines(keepends=True):
        stripped = line.removesuffix("\n")
        matched = _DIFF_PATH.match(stripped)
        if matched:
            path = _clean_diff_path(matched.group(1))
            if stripped.startswith("--- "):
                previous_path = path
                in_hunk = False
            else:
                target_path = path or previous_path
                target_eol = _target_line_ending(
                    boundary, target_path, content_loader=content_loader
                )
                in_hunk = False
            output.append(line.encode("utf-8"))
            continue
        if stripped.startswith("@@"):
            in_hunk = True
            output.append(line.encode("utf-8"))
            continue
        if stripped.startswith("diff --git "):
            previous_path = None
            target_eol = b"\n"
            in_hunk = False
            output.append(line.encode("utf-8"))
            continue
        if in_hunk and stripped.startswith((" ", "+", "-")):
            output.append(stripped.encode("utf-8") + target_eol)
            continue
        output.append(line.encode("utf-8"))
    return b"".join(output)


def _target_line_ending(
    boundary: RepositoryBoundary,
    relative_path: str | None,
    *,
    content_loader: Callable[[str], bytes | None] | None,
) -> bytes:
    if relative_path is None:
        return b"\n"
    path = boundary.resolve(relative_path, allow_missing=True)
    if content_loader is None:
        if not path.is_file():
            return b"\n"
        with path.open("rb") as handle:
            raw = handle.read(_MAX_EOL_INSPECTION_BYTES + 1)
    else:
        loaded = content_loader(relative_path)
        if loaded is None:
            return b"\n"
        raw = loaded
    if len(raw) > _MAX_EOL_INSPECTION_BYTES:
        raise AutofixError(
            "fix_patch_unsafe",
            f"Patch target exceeds the newline-safety inspection limit: {relative_path}",
        )
    without_crlf = raw.replace(b"\r\n", b"")
    if b"\r" in without_crlf or (b"\r\n" in raw and b"\n" in without_crlf):
        raise AutofixError(
            "fix_patch_unsafe",
            f"Patch target has mixed or unsupported line endings: {relative_path}",
        )
    return b"\r\n" if b"\r\n" in raw else b"\n"


def _decode_git_error(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")[:2_000].strip()


def _git_command(root: Path, *arguments: str) -> list[str]:
    command = ["git"]
    if os.name == "nt":
        command.extend(["-c", "core.autocrlf=true", "-c", "core.safecrlf=false"])
    command.extend(["-C", str(root), *arguments])
    return command


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
        if re.search(
            r"^(?:(?:new|old) file mode|new mode) 120000$",
            normalized,
            flags=re.MULTILINE,
        ):
            raise AutofixError(
                "fix_patch_unsafe",
                "Patches may not create or convert files into symbolic links",
            )
        if "diff --cc " in normalized or "diff --combined " in normalized:
            raise AutofixError("fix_patch_unsafe", "Combined diffs are not supported")

        current_file: str | None = None
        changed_files: list[str] = []
        additions = 0
        deletions = 0
        per_file: dict[str, int] = {}
        deleted_files: set[str] = set()
        previous_header: str | None = None
        metadata_paths: set[str] = set()

        for line in normalized.splitlines():
            if _UNSUPPORTED_DIFF_METADATA.match(line):
                raise AutofixError(
                    "fix_patch_unsafe",
                    "Mode, rename, and copy metadata are not supported in Autofix patches",
                )
            diff_git = _DIFF_GIT_PATHS.match(line)
            if diff_git:
                # Validate both sides even before ---/+++ parsing. This prevents a
                # hidden metadata-only section from escaping the structured file set.
                for raw_path in diff_git.groups():
                    cleaned = _clean_diff_path(raw_path)
                    if cleaned is not None:
                        metadata_paths.add(cleaned)
                current_file = None
                previous_header = None
                continue
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
        if metadata_paths and not metadata_paths.issubset(set(changed_files)):
            raise AutofixError(
                "fix_patch_unsafe",
                "Patch contains a diff section without a bounded text hunk",
            )
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

        prepared = prepare_patch_bytes(normalized, self.boundary)
        process = subprocess.run(
            _git_command(
                self.boundary.root,
                "apply",
                "--check",
                "--whitespace=nowarn",
                "-",
            ),
            input=prepared,
            capture_output=True,
            timeout=30,
            env=_filtered_git_environment(),
            check=False,
        )
        if process.returncode != 0:
            raise AutofixError(
                "fix_patch_unsafe",
                _decode_git_error(process.stderr) or "git apply --check rejected the patch",
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
        prepared = prepare_patch_bytes(normalized, self.boundary)
        process = subprocess.run(
            _git_command(
                self.boundary.root, "apply", "--whitespace=nowarn", "-"
            ),
            input=prepared,
            capture_output=True,
            timeout=30,
            env=_filtered_git_environment(),
            check=False,
        )
        if process.returncode != 0:
            raise AutofixError(
                "fix_patch_apply_failed",
                _decode_git_error(process.stderr) or "git apply rejected the confirmed patch",
            )

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            _git_command(self.boundary.root, *arguments),
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
