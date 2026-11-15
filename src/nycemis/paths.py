"""Repository paths. Every path in the project is built from ``repo_root()``; nothing is absolute in config."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the repository root: the nearest parent of this file that holds ``pyproject.toml``."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "nycemis").is_dir():
            return parent
    raise RuntimeError(f"cannot locate the repository root above {here}")


def rel(path: Path) -> str:
    """Path relative to the repository root, with forward slashes (for manifests and reports)."""
    return Path(path).resolve().relative_to(repo_root()).as_posix()


def configs_dir() -> Path:
    return repo_root() / "configs"


def docs_dir() -> Path:
    return repo_root() / "docs"


def legacy_dir() -> Path:
    return repo_root() / "legacy"


def data_dir() -> Path:
    return repo_root() / "data"


def scenarios_dir() -> Path:
    return repo_root() / "scenarios"


def results_dir() -> Path:
    return repo_root() / "results"


def models_dir() -> Path:
    return repo_root() / "models"
