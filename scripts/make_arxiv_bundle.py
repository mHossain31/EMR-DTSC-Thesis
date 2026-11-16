"""Package the paper sources for an optional arXiv upload (docs/SPECIFICATION.md M9).

Writes ``paper/build/arxiv_bundle.tar.gz`` holding ``main.tex``, ``macros.tex``, ``refs.bib``, the compiled
``main.bbl`` (arXiv does not run BibTeX on every submission) and every file under ``figures/`` and ``tables/`` that
``main.tex`` or a table references. Nothing is uploaded; whether to post, and with which co-authors, is the
author's decision.

Usage: python scripts/make_arxiv_bundle.py
"""

from __future__ import annotations

import re
import sys
import tarfile
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "paper"
REQUIRED = ("main.tex", "macros.tex", "refs.bib")
REF = re.compile(r"\\(?:input|include|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}")


def referenced(tex: Path) -> set[str]:
    out = set()
    for name in REF.findall(tex.read_text(encoding="utf-8")):
        out.add(name if Path(name).suffix else f"{name}.tex")
    return out


def collect() -> list[str]:
    missing = [f for f in REQUIRED if not (PAPER / f).is_file()]
    if missing:
        raise SystemExit(f"missing {missing}: run `python -m nycemis paper` first")
    files = set(REQUIRED)
    todo = [PAPER / "main.tex"]
    while todo:
        tex = todo.pop()
        for name in referenced(tex):
            path = PAPER / name
            if not path.is_file():
                raise SystemExit(f"{tex.name} references {name}, which does not exist")
            if name not in files:
                files.add(name)
                if path.suffix == ".tex":
                    todo.append(path)
    bbl = PAPER / "build" / "main.bbl"
    if bbl.is_file():
        files.add("build/main.bbl")
    else:
        print("warning: paper/build/main.bbl not found; compile the paper first so arXiv gets the bibliography",
              file=sys.stderr)
    return sorted(files)


def main() -> None:
    files = collect()
    out = PAPER / "build" / "arxiv_bundle.tar.gz"
    out.parent.mkdir(exist_ok=True)
    with tarfile.open(out, "w:gz") as tar:
        for name in files:
            arcname = "main.bbl" if name == "build/main.bbl" else name
            tar.add(PAPER / name, arcname=arcname)
    print(f"wrote {out.relative_to(PAPER.parent).as_posix()} ({len(files)} files)")


if __name__ == "__main__":
    main()
