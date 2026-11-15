"""Repository hygiene (docs/SPECIFICATION.md P9, 9.10): no unfinished-work markers, no absolute paths.

The markers are assembled from fragments so this file does not match itself. Exempt files quote the legacy
material or the specification verbatim; the list and the reasons are in docs/DESIGN.md.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from nycemis.paths import repo_root

MARKERS_CASE_SENSITIVE = ["TO" + "DO", "FIX" + "ME", "X" + "XX"]
MARKERS_ANY_CASE = ["place" + "holder", "replace" + " with", "lo" + "rem"]

EXEMPT_PREFIXES = (
    "legacy/",
    "results/legacy_audit/",
)
EXEMPT_FILES = {
    "docs/SPECIFICATION.md",
    "docs/LEGACY_AUDIT.md",
    "src/nycemis/legacy/audit.py",
    "src/nycemis/legacy/report.py",
}
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".txt", ".json", ".xml", ".cfg", ".tex", ".bib", ".csv",
                 ".sumocfg", ".ini"}
ABS_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s]|/Users/[A-Za-z]|/home/[A-Za-z]")


def _repo_text_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo_root()), "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for name in out.stdout.splitlines():
        if name in EXEMPT_FILES or name.startswith(EXEMPT_PREFIXES):
            continue
        path = repo_root() / name
        if path.suffix.lower() in TEXT_SUFFIXES and path.is_file() and path.stat().st_size < 5_000_000:
            files.append(name)
    return files


@pytest.fixture(scope="module")
def text_files() -> list[str]:
    files = _repo_text_files()
    assert files, "no files to scan"
    return files


def test_no_unfinished_work_markers(text_files: list[str]) -> None:
    hits = []
    any_case = re.compile("|".join(re.escape(m) for m in MARKERS_ANY_CASE), re.IGNORECASE)
    exact = re.compile("|".join(r"\b" + re.escape(m) + r"\b" for m in MARKERS_CASE_SENSITIVE))
    for name in text_files:
        for ln, line in enumerate((repo_root() / name).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if exact.search(line) or any_case.search(line):
                hits.append(f"{name}:{ln}: {line.strip()[:100]}")
    assert not hits, "unfinished-work markers found:\n" + "\n".join(hits)


def test_no_absolute_paths(text_files: list[str]) -> None:
    hits = []
    for name in text_files:
        for ln, line in enumerate((repo_root() / name).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if ABS_PATH.search(line):
                hits.append(f"{name}:{ln}: {line.strip()[:100]}")
    assert not hits, "absolute paths found:\n" + "\n".join(hits)
