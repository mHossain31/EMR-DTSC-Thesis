"""Package a paper version for an optional arXiv upload (docs/SPECIFICATION.md M9). Nothing is uploaded; whether to post, and
under which license and category, is the authors' decision.

    python scripts/make_arxiv_bundle.py                    # technical report (paper/main.tex)
    python scripts/make_arxiv_bundle.py --variant journal  # journal-style preprint (paper/journal/main.tex)

arXiv compiles the source itself and does not run BibTeX, so a bundle holds the LaTeX source, every file it inputs,
the figures it uses and a compiled ``main.bbl``. The journal preprint lives in ``paper/journal/`` and reads shared
files through ``../`` paths; its bundle is flattened (``\\input{../macros.tex}`` becomes ``\\input{macros.tex}``,
figures go to ``figures/``), compiled once with tectonic from the staged folder itself (which proves the bundle is
complete) and written to ``paper/journal/arxiv/journal_preprint_arxiv.tar.gz`` with ``arxiv_metadata.md``: the
plain-text title, authors, abstract and comments for the submission form, generated from the same macros.
"""

from __future__ import annotations

import argparse
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
ARXIV_ABSTRACT_MAX = 1920  # characters, arXiv submission form


def _engine() -> str | None:
    local = ROOT / "tools" / ("tectonic.exe" if os.name == "nt" else "tectonic")
    return str(local) if local.is_file() else shutil.which("tectonic")


def _compile(src_dir: Path, outdir: Path) -> Path:
    """Compile ``src_dir/main.tex`` with tectonic keeping intermediates; return the ``.bbl``."""
    engine = _engine()
    if engine is None:
        raise SystemExit("tectonic not found (tools/tectonic.exe or PATH); it is needed to compile main.bbl")
    env = {**os.environ}
    env.setdefault("TECTONIC_CACHE_DIR", (ROOT / "tools" / "tectonic-cache").as_posix())
    proc = subprocess.run([engine, "-X", "compile", "main.tex", "--outdir", str(outdir), "--keep-intermediates"],
                          cwd=src_dir, env=env, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"tectonic failed:\n{(proc.stdout + proc.stderr)[-3000:]}")
    bbl = outdir / "main.bbl"
    if not bbl.is_file():
        raise SystemExit("tectonic finished without writing main.bbl")
    return bbl


# ---------------------------------------------------------------- technical report (paper/main.tex)

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


def bundle_report() -> None:
    files = collect()
    out = PAPER / "build" / "arxiv_bundle.tar.gz"
    out.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="arxiv_bbl_") as tmp:
        bbl = _compile(PAPER, Path(tmp)) if _engine() else PAPER / "build" / "main.bbl"
        with tarfile.open(out, "w:gz") as tar:
            for name in files:
                tar.add(PAPER / name, arcname=name)
            has_bbl = bbl.is_file()
            if has_bbl:
                tar.add(bbl, arcname="main.bbl")
            else:
                print("warning: no TeX engine kept a main.bbl; the bundle has no bibliography", file=sys.stderr)
    print(f"wrote {out.relative_to(ROOT).as_posix()} ({len(files) + has_bbl} files)")


# ---------------------------------------------------------------- journal preprint (paper/journal/main.tex)

def _flat(name: str) -> str:
    return name[3:] if name.startswith("../") else name


def stage_journal(staging: Path) -> list[str]:
    """Copy the journal preprint and everything it uses into ``staging`` with flat relative paths."""
    src_dir = PAPER / "journal"
    text = (src_dir / "main.tex").read_text(encoding="utf-8")
    gp = re.search(r"\\graphicspath\{\{([^}]*)\}\}", text)
    graphics_dir = (src_dir / gp.group(1)) if gp else src_dir
    copied = []
    for name in re.findall(r"\\input\{([^}]+)\}", text):
        src = (src_dir / name).resolve()
        if not src.is_file():
            raise SystemExit(f"journal/main.tex inputs {name}, which does not exist")
        dest = staging / _flat(name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied.append(_flat(name))
    for name in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        src = graphics_dir / name
        if not src.is_file():
            raise SystemExit(f"journal/main.tex uses figure {name}, which does not exist")
        dest = staging / "figures" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied.append(f"figures/{name}")
    bib = re.search(r"\\bibliography\{([^}]+)\}", text).group(1)
    shutil.copyfile((src_dir / f"{bib}.bib").resolve(), staging / f"{_flat(bib)}.bib")
    copied.append(f"{_flat(bib)}.bib")
    text = re.sub(r"\\graphicspath\{\{[^}]*\}\}", lambda _: r"\graphicspath{{figures/}}", text)
    text = re.sub(r"\\(input|bibliography)\{\.\./", lambda m: "\\" + m.group(1) + "{", text)
    (staging / "main.tex").write_text(text, encoding="utf-8")
    return ["main.tex", *sorted(set(copied))]


def _macros() -> dict[str, str]:
    vals: dict[str, str] = {}
    for name in ("macros.tex", "macros_sensitivity.tex"):
        for key, val in re.findall(r"^\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}$",
                                   (PAPER / name).read_text(encoding="utf-8"), flags=re.MULTILINE):
            vals[key] = val
    return vals


def plain_text(tex: str, macros: dict[str, str]) -> str:
    """LaTeX of the title or abstract to the plain text the arXiv form expects."""
    s = tex.replace("\\noindent", "").replace("\\\\", " ")
    s = re.sub(r"NO\$_x\$", "NOx", s)
    s = re.sub(r"CO\$_2\$", "CO2", s)
    # a macro followed by a control space (\ ) keeps that space; by {} nothing
    s = re.sub(r"\\([A-Za-z]+)(\\ |\{\})?",
               lambda m: (macros[m.group(1)] + (" " if m.group(2) == "\\ " else "")) if m.group(1) in macros
               else m.group(0), s)
    s = s.replace("\\%", "%").replace("~", " ").replace("$-$", "-").replace("$", "")
    s = re.sub(r"\s+", " ", s).strip()
    if "\\" in s:
        raise SystemExit(f"unconverted LaTeX left in: {s[:200]}")
    return s


def write_metadata(path: Path, pages: int) -> None:
    text = (PAPER / "journal" / "main.tex").read_text(encoding="utf-8")
    macros = _macros()
    title = plain_text(re.search(r"\\title\{(.*?)\}\n\\author", text, flags=re.S).group(1), macros)
    authors = ", ".join(re.findall(r"\\author\{([^}]+)\}", text))
    abstract = plain_text(re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, flags=re.S).group(1), macros)
    figures = len(re.findall(r"\\begin\{figure\}", text))
    tables = len(re.findall(r"\\begin\{table\}", text))
    if len(abstract) > ARXIV_ABSTRACT_MAX:
        raise SystemExit(f"abstract has {len(abstract)} characters, arXiv allows {ARXIV_ABSTRACT_MAX}")
    lines = [
        "# arXiv submission metadata: journal-style preprint", "",
        "Generated by `python scripts/make_arxiv_bundle.py --variant journal` from `paper/journal/main.tex` and the "
        "generated macros; do not edit by hand. Paste each field into the arXiv form. Nothing has been submitted.", "",
        "## Title", "", title, "",
        "## Authors", "", authors, "",
        f"## Abstract ({len(abstract)} of {ARXIV_ABSTRACT_MAX} characters)", "", abstract, "",
        "## Comments", "", f"{pages} pages, {figures} figures, {tables} tables. Code, preregistration and result files "
        "are in the project repository.", "",
        "## Choices left to the authors", "",
        "- Primary category and cross-lists (arXiv moderators may reclassify). Candidates that match the content: "
        "physics.soc-ph (Physics and Society, where traffic simulation is common), stat.AP (Statistics, "
        "Applications) and cs.CY (Computers and Society).",
        "- License (arXiv offers several, for example CC BY 4.0 or the arXiv non-exclusive license).",
        "- Whether both authors agree to post, and whether Prof. X. Huang should see the preprint first.",
        "- First-time submitters may need an endorsement from an established author in the chosen category.", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def bundle_journal() -> None:
    out_dir = PAPER / "journal" / "arxiv"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "journal_preprint_arxiv.tar.gz"
    with tempfile.TemporaryDirectory(prefix="arxiv_journal_") as tmp:
        staging, build = Path(tmp) / "src", Path(tmp) / "build"
        staging.mkdir()
        build.mkdir()
        files = stage_journal(staging)
        bbl = _compile(staging, build)  # compiling the staged copy proves the bundle is complete
        shutil.copyfile(bbl, staging / "main.bbl")
        files.append("main.bbl")
        pages = _pdf_pages(build / "main.pdf")
        with tarfile.open(out, "w:gz") as tar:
            for name in files:
                tar.add(staging / name, arcname=name)
    meta = out_dir / "arxiv_metadata.md"
    write_metadata(meta, pages)
    print(f"wrote {out.relative_to(ROOT).as_posix()} ({len(files)} files; compiled from the staged copy, "
          f"{pages} pages)")
    print(f"wrote {meta.relative_to(ROOT).as_posix()}")


def _pdf_pages(pdf: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(pdf)).pages)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", choices=("report", "journal"), default="report")
    args = ap.parse_args()
    bundle_journal() if args.variant == "journal" else bundle_report()


if __name__ == "__main__":
    main()
