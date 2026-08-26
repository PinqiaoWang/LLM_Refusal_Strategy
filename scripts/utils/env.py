"""Minimal .env loader.

Keeps API keys out of the shell history and out of the repo: `.env` is already
in .gitignore.  Deliberately dependency-free (no python-dotenv) so that a fresh
clone needs nothing beyond requirements.txt.

Real environment variables always win, so `OPENROUTER_API_KEY=... python ...`
still overrides the file.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / ".env"

_loaded = False


def load_env_file(path: Path = ENV_PATH) -> None:
    """Read KEY=VALUE lines from .env into os.environ. Safe to call repeatedly."""
    global _loaded
    if _loaded or not path.exists():
        return
    _loaded = True
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require(name: str, hint: str = "") -> str:
    load_env_file()
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Put it in {ENV_PATH} as `{name}=...` "
            f"or export it in your shell. {hint}".strip()
        )
    return value
