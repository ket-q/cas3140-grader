"""Save the submission token once per Python environment.

Where the token is stored, in the order a token is looked up:
1. an explicit ``token=`` argument (never stored).
2. the ``CAS3140_TOKEN`` environment variable.
3. ``<sys.prefix>/.cas3140/account.json``: inside the current Python
   environment (virtual environment, conda environment, ...), so deleting the
   environment deletes the token.
4. ``~/.cas3140/account.json``: used only when the environment itself cannot
   be written to (e.g., a shared, read-only Python). The token
   is saved for the user account instead and a message says so.

``CAS3140_CONFIG_DIR`` overrides 3 and 4 with a single directory.

The file is written atomically with owner-only permissions (0600 in a 0700
directory) on POSIX systems. For Windows, the file instead
relies on the protection of the user's own profile or environment directory.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

CONFIG_DIR_ENV = "CAS3140_CONFIG_DIR"
TOKEN_ENV = "CAS3140_TOKEN"
_FILE_NAME = "account.json"
_MIN_TOKEN_LENGTH = 43  # the server only accepts tokens with at least 256 bits

NO_TOKEN_MESSAGE = (
    "No submission token is available. Run save_account() once to save it for this "
    "Python environment, or pass token=... to this call."
)


class _CorruptAccountFile(Exception):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.path = path


def _candidate_directories() -> list[tuple[str, Path]]:
    """Storage locations in priority order."""
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        return [("custom", Path(override).expanduser())]
    candidates = [("environment", Path(sys.prefix) / ".cas3140")]
    try:
        candidates.append(("user", Path.home() / ".cas3140"))
    except RuntimeError:  # no home directory could be determined
        pass
    return candidates


def _clean_token(token: Any) -> str:
    if not isinstance(token, str):
        raise TypeError(f"The token must be a string, not {type(token).__name__}.")
    cleaned = token.strip()
    if not cleaned:
        raise ValueError("The token is empty.")
    if any(character.isspace() for character in cleaned):
        raise ValueError("The token contains spaces or line breaks; copy it exactly as you received it.")
    if len(cleaned) < _MIN_TOKEN_LENGTH:
        raise ValueError(
            f"The token is too short ({len(cleaned)} characters; expected at least {_MIN_TOKEN_LENGTH}). "
            "Copy the whole token exactly as you received it."
        )
    return cleaned


def _read(path: Path) -> str | None:
    """Return the token stored at ``path``, None if there is no file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return None
    except (OSError, UnicodeDecodeError) as error:
        raise _CorruptAccountFile(path) from error
    try:
        token = json.loads(text)["token"]
    except (ValueError, KeyError, TypeError) as error:
        raise _CorruptAccountFile(path) from error
    if not isinstance(token, str) or not token:
        raise _CorruptAccountFile(path)
    return token


def _write(path: Path, token: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".account-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"version": 1, "token": token}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "posix":
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _find_saved() -> tuple[str, str, Path] | None:
    """Return ``(token, scope, path)`` of the first saved token; raise _CorruptAccountFile if unreadable."""
    for scope, directory in _candidate_directories():
        path = directory / _FILE_NAME
        token = _read(path)
        if token is not None:
            return token, scope, path
    return None


def _mask(token: str) -> str:
    return token[:4] + "…" if len(token) > 8 else "…"


def resolve_token(token: str | None = None) -> str:
    """Return the token to use for a request: explicit argument, environment variable, then saved file."""
    if token is not None:
        return token
    from_environment = os.environ.get(TOKEN_ENV, "").strip()
    if from_environment:
        return _clean_token(from_environment)
    try:
        found = _find_saved()
    except _CorruptAccountFile as error:
        raise RuntimeError(
            f"The saved token file {error.path} is unreadable. "
            "Run save_account(overwrite=True) to replace it, or delete_account() to remove it."
        ) from error
    if found is None:
        raise RuntimeError(NO_TOKEN_MESSAGE)
    return found[0]


def save_account(token: str | None = None, *, overwrite: bool = False) -> None:
    """Save the submission token for this Python environment.

    Call it without arguments to be asked for the token with hidden input, which
    keeps the token out of your notebook. Raises ``RuntimeError`` if a token is
    already saved, unless ``overwrite=True`` is specified.
    """
    if token is None:
        token = getpass.getpass("CAS3140 submission token (input is hidden): ")
    token = _clean_token(token)
    try:
        existing = _find_saved()
    except _CorruptAccountFile:
        existing = None 
    if existing is not None and not overwrite:
        raise RuntimeError(
            f"A token is already saved ({existing[2]}). Call save_account(overwrite=True) to replace it."
        )
    candidates = _candidate_directories()
    problems: list[str] = []
    for index, (scope, directory) in enumerate(candidates):
        target = directory / _FILE_NAME
        try:
            _write(target, token)
        except OSError as error:
            problems.append(f"{target}: {error.strerror or error}")
            continue
        # Remove copies elsewhere so an old token cannot come back later.
#         for _other_scope, other_directory in candidates:
#             other = other_directory / _FILE_NAME
#             if other != target:
#                 try:
#                     other.unlink()
#                 except OSError:
#                     pass
        if index == 0:
            print(f"Token saved for this Python environment ({target}).")
        else:
            print(
                f"This Python environment cannot be written to ({problems[0]}); "
                f"the token was saved for your user account instead ({target})."
            )
        return
    raise RuntimeError("The token could not be saved. " + "; ".join(problems))


def saved_account() -> dict[str, str] | None:
    """Describe the saved token without revealing it, or return None if nothing is saved."""
    try:
        found = _find_saved()
    except _CorruptAccountFile as error:
        return {"location": str(error.path), "scope": "unreadable", "token": "(unreadable file)"}
    if found is None:
        return None
    token, scope, path = found
    return {"token": _mask(token), "scope": scope, "location": str(path)}


def delete_account() -> bool:
    """Delete the saved token. Returns True if a file was removed."""
    removed: list[Path] = []
    for _scope, directory in _candidate_directories():
        path = directory / _FILE_NAME
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise RuntimeError(f"Could not delete {path}: {error.strerror or error}") from error
        removed.append(path)
    if removed:
        print("Deleted the saved token: " + ", ".join(str(path) for path in removed))
        return True
    print("No saved token was found.")
    return False


__all__ = ["delete_account", "resolve_token", "save_account", "saved_account"]