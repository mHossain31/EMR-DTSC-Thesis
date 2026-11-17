"""``verify-all``: the automated checks of docs/SPECIFICATION.md section 9, end to end.

1. pytest, all markers (unit, API contract, determinism, pairing, reconciliation, leakage, shadow parity,
   alpha = 0 sanity, artifact demonstration, hygiene, regression);
2. ruff on src, tests and scripts;
3. ``experiment verify`` for every final experiment that has a plan (completeness, pairing by route hash, schema);
   the preregistration came before the test seeds and the analysis code still has its frozen hash (or the change
   is in docs/DEVIATIONS.md);
4. the paper: macros regenerated; every macro main.tex uses is defined; no percentage or decimal typed in its body;
5. ``docs/OPEN_ITEMS.md`` holds only items labelled out-of-scope-by-design or environment-limited;
6. the smoke harness tests from a clean clone of the committed tree whose path contains a space.

Check 6 clones the last commit, so it covers committed code only.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from nycemis.paths import docs_dir, repo_root

FINAL_EXPERIMENTS = ("pilot", "dataset", "validation", "confirmatory")
OPEN_ITEM_LABELS = ("out-of-scope-by-design", "environment-limited")
LATEX_UPPER = {"LaTeX", "TeX"}  # LaTeX commands with an uppercase initial that are not project macros
ALLOWED_NUMBERS = (r"HBEFA~4\.2", r"95\\% BCa")  # a model version and the confidence level, not results
SPACE_PATH_TESTS = ("tests/integration/test_harness.py::test_reconciliation_within_tolerance",
                    "tests/integration/test_harness.py::test_determinism_same_spec_twice")


def _run(cmd: list[str], cwd: Path, env: dict | None = None, timeout: float = 7200) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)
    out = (proc.stdout + proc.stderr).strip().splitlines()
    return proc.returncode == 0, "\n".join(out[-15:])


def check_pytest() -> tuple[bool, str]:
    return _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], repo_root())


def check_ruff() -> tuple[bool, str]:
    return _run([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"], repo_root())


def check_experiments() -> tuple[bool, str]:
    from nycemis.experiments.plan import exp_dir
    from nycemis.experiments.verify import verify

    lines, ok = [], True
    for exp in FINAL_EXPERIMENTS:
        if not (exp_dir(exp) / "plan.json").is_file():
            lines.append(f"{exp}: no plan")
            ok &= exp != "confirmatory"
            continue
        res = verify(exp)
        ok &= bool(res["ok"])
        lines.append(f"{exp}: {res['done']}/{res['planned']} done, {len(res['problems'])} problems")
    return ok, "\n".join(lines)


def _strip_tex(text: str) -> str:
    text = re.sub(r"(?<!\\)%.*", "", text)  # comments
    body = text.split(r"\begin{document}", 1)[-1]
    return re.sub(r"\[[^\]]*\]", "", body)  # optional arguments such as [width=0.9\linewidth]


def check_paper() -> tuple[bool, str]:
    from nycemis.analysis.paper import PAPER, write_macros

    write_macros()
    defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", (PAPER / "macros.tex").read_text(encoding="utf-8")))
    body = _strip_tex((PAPER / "main.tex").read_text(encoding="utf-8"))
    used = set(re.findall(r"\\([A-Z][A-Za-z]*)", body)) - LATEX_UPPER
    missing = sorted(used - defined)
    for pat in ALLOWED_NUMBERS:
        body = re.sub(pat, "", body)
    typed = sorted(set(re.findall(r"(?<![A-Za-z\\])\d+(?:\.\d+)?\\%|(?<![A-Za-z\\])\d+\.\d+", body)))
    msg = []
    if missing:
        msg.append(f"macros used but not generated (missing results?): {', '.join(missing)}")
    if typed:
        msg.append(f"numbers typed in main.tex: {', '.join(typed)}")
    return not (missing or typed), "\n".join(msg) or f"{len(used)} macros used, all generated; no typed numbers"


def check_open_items() -> tuple[bool, str]:
    rows = [r for r in (docs_dir() / "OPEN_ITEMS.md").read_text(encoding="utf-8").splitlines()
            if re.match(r"\|\s*\d+\s*\|", r)]
    bad = [r for r in rows if r.rstrip(" |").rsplit("|", 1)[-1].strip() not in OPEN_ITEM_LABELS]
    return not bad, "\n".join(bad) or f"{len(rows)} items, all labelled {' or '.join(OPEN_ITEM_LABELS)}"


def check_prereg() -> tuple[bool, str]:
    """The preregistration came first and still holds: the freeze and its tag exist; the confirmatory plan and every
    confirmatory run are newer than the tagged commit; the analysis code has the frozen hash, or
    ``docs/DEVIATIONS.md`` records the new hash."""
    import json

    from nycemis.experiments.plan import exp_dir
    from nycemis.experiments.prereg import analysis_code_sha256
    from nycemis.paths import results_dir

    path = results_dir() / "validation" / "prereg_freeze.json"
    if not path.is_file():
        return False, "no preregistration freeze (python -m nycemis prereg)"
    frozen = json.loads(path.read_text(encoding="utf-8"))
    ok, tag_time = _run(["git", "log", "-1", "--format=%ct", frozen["tag"]], repo_root(), timeout=60)
    if not ok:
        return False, f"tag {frozen['tag']} not found"
    tagged = float(tag_time.strip())
    msg, good = [f"tag {frozen['tag']} at {tagged:.0f}"], True
    d = exp_dir("confirmatory")
    if (d / "plan.json").is_file():
        early = [p.parent.name for p in [d / "plan.json", *d.glob("*/DONE")] if p.stat().st_mtime < tagged]
        good &= not early
        msg.append(f"confirmatory files older than the tag: {early[:5]}" if early else
                   "confirmatory plan and runs are newer than the tag")
    current = analysis_code_sha256()
    if current == frozen["analysis_code_sha256"]:
        msg.append("analysis code matches the frozen hash")
    elif current in (docs_dir() / "DEVIATIONS.md").read_text(encoding="utf-8"):
        msg.append(f"analysis code changed after the freeze; recorded in DEVIATIONS.md ({current[:12]})")
    else:
        good = False
        msg.append(f"analysis code changed after the freeze ({current[:12]}) and DEVIATIONS.md does not record it")
    return good, "\n".join(msg)


def _force_remove(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)  # git marks pack files read-only on Windows
    func(path)


def check_space_path() -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="nycemis verify "))
    clone = tmp / "repo with space"
    try:
        ok, msg = _run(["git", "clone", "--quiet", str(repo_root()), str(clone)], tmp, timeout=600)
        if not ok:
            return False, f"git clone failed: {msg}"
        env = {**os.environ, "PYTHONPATH": str(clone / "src")}
        ok, msg = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *SPACE_PATH_TESTS],
                       clone, env=env)
        return ok, f"{clone}\n{msg}"
    finally:
        shutil.rmtree(tmp, onexc=_force_remove)


CHECKS = {"pytest": check_pytest, "ruff": check_ruff, "experiments": check_experiments, "prereg": check_prereg,
          "paper": check_paper, "open_items": check_open_items, "space_path": check_space_path}


def verify_all(only: list[str] | None = None) -> dict:
    results = {}
    for name, fn in CHECKS.items():
        if only and name not in only:
            continue
        ok, msg = fn()
        results[name] = {"ok": ok, "detail": msg}
    return {"ok": all(r["ok"] for r in results.values()), "checks": results}
