"""Package the paper sources for an optional arXiv upload (docs/SPECIFICATION.md M9).

Writes ``paper/build/arxiv_bundle.tar.gz`` holding ``main.tex``, ``macros.tex``, ``refs.bib``, a compiled
``main.bbl`` (arXiv does not run BibTeX on every submission) and every file under ``figures/`` and ``tables/`` that
``main.tex`` or a table references. Nothing is uploaded; whether to post, and with which co-authors, is the
author's decision.

``python -m nycemis paper`` compiles with tectonic, which discards the ``.bbl``, so this script compiles once more
into a temporary directory with ``--keep-intermediates`` and packages that ``.bbl``. Without tectonic it uses the
``paper/build/main.bbl`` that latexmk leaves, and warns if there is none.

Usage: python scripts/make_arxiv_bundle.py
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
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
    return sorted(files)


def tectonic_bbl(outdir: Path) -> Path | None:
    """Compile with tectonic keeping intermediates and return the ``.bbl``; None if tectonic is not available."""
    local = ROOT / "tools" / ("tectonic.exe" if os.name == "nt" else "tectonic")
    engine = str(local) if local.is_file() else shutil.which("tectonic")
    if engine is None:
        return None
    env = {**os.environ}
    env.setdefault("TECTONIC_CACHE_DIR", (ROOT / "tools" / "tectonic-cache").as_posix())
    proc = subprocess.run([engine, "-X", "compile", "main.tex", "--outdir", str(outdir), "--keep-intermediates"],
                          cwd=PAPER, env=env, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"tectonic failed:\n{(proc.stdout + proc.stderr)[-3000:]}")
    bbl = outdir / "main.bbl"
    if not bbl.is_file():
        raise SystemExit("tectonic finished without writing main.bbl")
    return bbl


def main() -> None:
    files = collect()
    out = PAPER / "build" / "arxiv_bundle.tar.gz"
    out.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="arxiv_bbl_") as tmp:
        bbl = tectonic_bbl(Path(tmp)) or PAPER / "build" / "main.bbl"
        with tarfile.open(out, "w:gz") as tar:
            for name in files:
                tar.add(PAPER / name, arcname=name)
            has_bbl = bbl.is_file()
            if has_bbl:
                tar.add(bbl, arcname="main.bbl")
            else:
                print("warning: no TeX engine kept a main.bbl; the bundle has no bibliography", file=sys.stderr)
    print(f"wrote {out.relative_to(ROOT).as_posix()} ({len(files) + has_bbl} files)")


if __name__ == "__main__":
    main()
