"""Extract the legacy files and compute every number the audit cites, directly from the files.

Inputs (read-only, in ``legacy/``): the 48-page report, the 31-page slides and the zip holding the notebook.
Outputs: ``legacy/notebook_code.py`` (outputs stripped), ``legacy/notebook_outputs.txt`` (text outputs, long streams
truncated with counts), ``legacy/report_text.md`` and ``legacy/slides_text.md`` (text per PDF page), the full
notebook in the gitignored ``legacy/extracted/``, and ``results/legacy_audit/audit_numbers.json``.

Page numbers below are PDF page indices (1-based); the report's printed page numbers are one lower.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from nycemis.paths import legacy_dir, rel, results_dir

REPORT_PDF = "ML_SUMO_ProjectReport.pdf"
SLIDES_PDF = "SUMO_ML_Project.pdf"
NOTEBOOK_ZIP = "pynb_file.zip"
NOTEBOOK_MEMBER = "pynb_file/car_emission_air_pollution.ipynb"
EXPECTED_PAGES = {REPORT_PDF: 48, SLIDES_PDF: 31}
STREAM_KEEP_CHARS = 4000

# Notebook cells the audit refers to (0-based, as stored in the .ipynb).
CELL_COLLECT = 2  # first simulation: TraCI data collection loop
CELL_SAMPLE = 4  # sample of the collected data
CELL_PARSE = 6  # parse emissions_data.xml into df
CELL_NORMALIZE = 12  # normalized_df
CELL_MODEL_COMPARE = 18  # eight-model comparison (features include X, Y)
CELL_MSE_PLACEHOLDER = (24, 26)
CELL_RF = 30  # RF used for rerouting (four pollutant features)
CELL_THRESHOLD = 32
CELL_RF_REROUTE = 37
CELL_XGB_TRAIN = 45
CELL_XGB_REROUTE = 46
CELL_XGB_MAP = 48
CELL_DROP = 50
CELL_NOX_COMPARE = 55
CELL_REAL_MAP = 57

REROUTE_LINE = re.compile(r"^Vehicle (\S+) rerouted(?: to reduce pollution)?\. New route: (\(.*\))$")
DETECT_LINE = re.compile(r"^High pollution detected for (\S+) on edge (\S+)\. Rerouting\.\.\.$")
TABLE_ROW = re.compile(r"^\s*(\d+)\s+(-?[\d.]+)\s+(veh\S+)\s+(.*)$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def legacy_paths() -> dict[str, Path]:
    paths = {name: legacy_dir() / name for name in (REPORT_PDF, SLIDES_PDF, NOTEBOOK_ZIP)}
    missing = [n for n, p in paths.items() if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"legacy files missing from {legacy_dir()}: {missing}")
    return paths


def load_notebook(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        return json.loads(zf.read(NOTEBOOK_MEMBER))


def _text(value: str | list[str] | None) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else "".join(value)


def cell_source(nb: dict, idx: int) -> str:
    return _text(nb["cells"][idx]["source"])


def cell_stream(nb: dict, idx: int) -> str:
    return "".join(
        _text(o.get("text")) for o in nb["cells"][idx].get("outputs", []) if o.get("output_type") == "stream"
    )


def cell_plain_results(nb: dict, idx: int) -> list[str]:
    out = []
    for o in nb["cells"][idx].get("outputs", []):
        if o.get("output_type") in {"execute_result", "display_data"}:
            plain = o.get("data", {}).get("text/plain")
            if plain is not None:
                out.append(_text(plain))
    return out


def cell_errors(nb: dict, idx: int) -> list[str]:
    return [
        f"{o.get('ename')}: {o.get('evalue')}"
        for o in nb["cells"][idx].get("outputs", [])
        if o.get("output_type") == "error"
    ]


def pdf_pages(path: Path) -> list[str]:
    """Text of each page, extracted in layout mode with runs of blanks collapsed."""
    pages = []
    for page in PdfReader(path).pages:
        raw = page.extract_text(extraction_mode="layout") or ""
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.splitlines()]
        pages.append("\n".join(ln for ln in lines if ln))
    return pages


# --------------------------------------------------------------------------------------------- extraction


def write_extracts(nb: dict, report: list[str], slides: list[str]) -> list[str]:
    """Write the extracted code, outputs and PDF text into legacy/. Returns the files written."""
    out_dir = legacy_dir()
    (out_dir / "extracted").mkdir(exist_ok=True)
    nb_path = out_dir / "extracted" / Path(NOTEBOOK_MEMBER).name
    nb_path.write_text(json.dumps(nb), encoding="utf-8")

    code_lines = [
        "# Code cells of legacy/pynb_file.zip:" + NOTEBOOK_MEMBER + " with outputs stripped.",
        "# Extracted by `python -m nycemis legacy-audit`. Cell numbers are 0-based .ipynb indices.",
        "# This file is evidence for docs/LEGACY_AUDIT.md; it is not meant to be run.",
        "",
    ]
    for idx, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        code_lines.append(f"# %% [cell {idx}] execution_count={cell.get('execution_count')}")
        code_lines.append(_text(cell["source"]).rstrip())
        code_lines.append("")
    (out_dir / "notebook_code.py").write_text("\n".join(code_lines) + "\n", encoding="utf-8")

    out_lines = ["# Text outputs of the legacy notebook (images omitted; long streams truncated).", ""]
    for idx, cell in enumerate(nb["cells"]):
        for o in cell.get("outputs", []):
            kind = o.get("output_type")
            if kind == "stream":
                body = _text(o.get("text"))
            elif kind in {"execute_result", "display_data"}:
                body = _text(o.get("data", {}).get("text/plain")) or f"[non-text output: {list(o.get('data', {}))}]"
            elif kind == "error":
                body = f"{o.get('ename')}: {o.get('evalue')}"
            else:
                body = f"[{kind}]"
            if len(body) > STREAM_KEEP_CHARS:
                n_lines = body.count("\n")
                head, tail = body[: STREAM_KEEP_CHARS // 2], body[-STREAM_KEEP_CHARS // 2 :]
                body = f"{head}\n... [truncated: {len(body)} chars, {n_lines} lines in total] ...\n{tail}"
            out_lines.append(f"===== cell {idx} {kind} =====")
            out_lines.append(body.rstrip())
            out_lines.append("")
    (out_dir / "notebook_outputs.txt").write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    for name, pages, title in (
        ("report_text.md", report, "ML_SUMO_ProjectReport.pdf"),
        ("slides_text.md", slides, "SUMO_ML_Project.pdf"),
    ):
        parts = [f"# Text of {title} ({len(pages)} PDF pages, pypdf layout extraction)", ""]
        for i, text in enumerate(pages, start=1):
            parts.append(f"## PDF page {i}")
            parts.append("")
            parts.append(text)
            parts.append("")
        (out_dir / name).write_text("\n".join(parts), encoding="utf-8")
    return [
        rel(nb_path),
        rel(out_dir / "notebook_code.py"),
        rel(out_dir / "notebook_outputs.txt"),
        rel(out_dir / "report_text.md"),
        rel(out_dir / "slides_text.md"),
    ]


# --------------------------------------------------------------------------------------------- analysis


def _table_rows(text: str) -> dict[int, tuple[float, str, str]]:
    rows = {}
    for line in text.splitlines():
        m = TABLE_ROW.match(line)
        if m:
            rows[int(m.group(1))] = (float(m.group(2)), m.group(3), m.group(4))
    return rows


def baseline_horizon_bounds(nb: dict) -> dict:
    """Bound the baseline run's time span from the min-max normalized Time column (cell 12).

    normalized = (t - t_min) / (t_max - t_min), printed to 6 decimals; t_min = 0 (row 0). For each row with
    raw t > 0, t_max lies in [t / (n + 5e-7), t / (n - 5e-7)]; the bounds are intersected.
    """
    raw = _table_rows(cell_plain_results(nb, CELL_PARSE)[0])
    norm = _table_rows(cell_plain_results(nb, CELL_NORMALIZE)[0])
    if raw[0][0] != 0.0 or norm[0][0] != 0.0:
        raise ValueError("expected Time = 0 in row 0 of both tables")
    lo, hi = 0.0, float("inf")
    used = []
    for idx, (t_raw, _, _) in raw.items():
        if t_raw <= 0 or idx not in norm:
            continue
        n = norm[idx][0]
        lo = max(lo, t_raw / (n + 5e-7))
        hi = min(hi, t_raw / (n - 5e-7))
        used.append({"row": idx, "time_s": t_raw, "normalized": n})
    if not lo <= hi:
        raise ValueError("inconsistent normalized Time values")
    return {"t_max_lo_s": lo, "t_max_hi_s": hi, "t_max_mid_s": (lo + hi) / 2, "rows_used": used}


def _loop_info(source: str) -> dict:
    """Find the main while-loop: its step bound and whether its body increments ``step``."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            bound = None
            for sub in ast.walk(node.test):
                if isinstance(sub, ast.Compare) and isinstance(sub.left, ast.Name) and sub.left.id == "step":
                    comp = sub.comparators[0]
                    if isinstance(comp, ast.Constant):
                        bound = comp.value
                    elif isinstance(comp, ast.Name):
                        bound = comp.id
            increments = any(
                isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name) and s.target.id == "step"
                for s in ast.walk(node)
            )
            return {"step_bound": bound, "increments_step": increments}
    raise ValueError("no while loop found")


def reroute_stats(stream: str) -> dict:
    """Count reroute calls and how many repeat calls returned the unchanged remaining route.

    A repeat call is "unchanged" when the new route (internal ``:`` edges removed) is a suffix of the route the
    previous call gave the same vehicle. The first call per vehicle cannot be checked: the original route was
    never logged.
    """
    last: dict[str, tuple[str, ...]] = {}
    first_routes: dict[str, tuple[str, ...]] = {}
    calls = unchanged = changed = detections = 0
    for line in stream.splitlines():
        if DETECT_LINE.match(line):
            detections += 1
            continue
        m = REROUTE_LINE.match(line)
        if not m:
            continue
        veh = m.group(1)
        route = tuple(e for e in ast.literal_eval(m.group(2)) if not e.startswith(":"))
        calls += 1
        if veh in last:
            prev = last[veh]
            if len(route) <= len(prev) and prev[len(prev) - len(route) :] == route:
                unchanged += 1
            else:
                changed += 1
        else:
            first_routes[veh] = route
        last[veh] = route
    repeats = unchanged + changed
    return {
        "detections": detections,
        "reroute_calls": calls,
        "vehicles": len(first_routes),
        "repeat_calls": repeats,
        "repeat_unchanged": unchanged,
        "repeat_changed": changed,
        "repeat_unchanged_share": unchanged / repeats if repeats else None,
        "_first_routes": first_routes,
    }


def _mse_table(stream: str) -> dict[str, dict[str, float]]:
    rows = {}
    for line in stream.splitlines():
        m = re.match(r"^\s*\d+\s+(.+?)\s+([\d.]+)\s+([\d.]+)\s*$", line)
        if m:
            rows[m.group(1).strip()] = {"train_mse": float(m.group(2)), "test_mse": float(m.group(3))}
    return rows


def _find_pages(pages: list[str], pattern: str) -> list[int]:
    rx = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    return [i for i, text in enumerate(pages, start=1) if rx.search(re.sub(r"\s+", " ", text))]


def _code_hits(nb: dict, pattern: str) -> list[dict]:
    rx = re.compile(pattern)
    hits = []
    for idx, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        for ln, line in enumerate(_text(cell["source"]).splitlines(), start=1):
            if rx.search(line):
                hits.append({"cell": idx, "line": ln, "text": line.strip()})
    return hits


def reported_drops(slides: list[str]) -> dict[str, dict[str, float]]:
    """Parse the RF and XGBoost percentage drops from the slides' result table (PDF page 23)."""
    page = re.sub(r"\s+", " ", slides[22])
    # Layout extraction gives: "... CO2 CO NOx HC PMx Random Forest 72% 63.99 ... Regressor XGBoost 73.65% ..."
    nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%?", page.split("PMx", 1)[1])]
    if len(nums) < 10:
        raise ValueError(f"cannot parse the result table on slides page 23: {page!r}")
    pollutants = ["CO2", "CO", "NOx", "HC", "PMx"]
    return {
        "RF": dict(zip(pollutants, nums[0:5], strict=True)),
        "XGBoost": dict(zip(pollutants, nums[5:10], strict=True)),
    }


@dataclass
class LegacyInputs:
    nb: dict
    report: list[str]
    slides: list[str]
    paths: dict[str, Path]


def load_inputs() -> LegacyInputs:
    paths = legacy_paths()
    return LegacyInputs(
        nb=load_notebook(paths[NOTEBOOK_ZIP]),
        report=pdf_pages(paths[REPORT_PDF]),
        slides=pdf_pages(paths[SLIDES_PDF]),
        paths=paths,
    )


def compute_numbers(inp: LegacyInputs) -> dict:
    nb, report, slides = inp.nb, inp.report, inp.slides
    pages_ok = {name: (len(report) if name == REPORT_PDF else len(slides)) for name in EXPECTED_PAGES}
    for name, expected in EXPECTED_PAGES.items():
        if pages_ok[name] != expected:
            raise ValueError(f"{name}: {pages_ok[name]} pages extracted, expected {expected}")

    baseline_rows = int(re.search(r"The DataFrame has (\d+) rows", cell_stream(nb, CELL_PARSE)).group(1))
    report_rows_match = re.search(r"comprising ([\d,]+) rows", " ".join(report))
    report_rows = int(report_rows_match.group(1).replace(",", "")) if report_rows_match else None

    xgb_err = " ".join(cell_errors(nb, CELL_XGB_MAP))
    m = re.search(r"Length of values \((\d+)\) does not match length of index \((\d+)\)", xgb_err)
    xgb_rows, rf_rows = int(m.group(1)), int(m.group(2))

    horizon = baseline_horizon_bounds(nb)
    loops = {
        "collect_cell_2": _loop_info(cell_source(nb, CELL_COLLECT)),
        "rf_reroute_cell_37": _loop_info(cell_source(nb, CELL_RF_REROUTE)),
        "xgb_reroute_cell_46": _loop_info(cell_source(nb, CELL_XGB_REROUTE)),
    }
    ctl_steps = loops["rf_reroute_cell_37"]["step_bound"]

    rf = reroute_stats(cell_stream(nb, CELL_RF_REROUTE))
    xgb = reroute_stats(cell_stream(nb, CELL_XGB_REROUTE))
    common = set(rf["_first_routes"]) & set(xgb["_first_routes"])
    same_first = sum(rf["_first_routes"][v] == xgb["_first_routes"][v] for v in common)
    for d in (rf, xgb):
        d.pop("_first_routes")

    sample = _table_rows(cell_plain_results(nb, CELL_SAMPLE)[0])
    nox_cmp = cell_plain_results(nb, CELL_NOX_COMPARE)
    later_cells = range(CELL_NORMALIZE + 1, len(nb["cells"]))
    normalized_uses = [i for i in later_cells if "normalized_df" in _text(nb["cells"][i]["source"])]

    rf_mse = float(re.search(r"Mean Squared Error: ([\d.eE-]+)", cell_stream(nb, CELL_RF)).group(1))
    xgb_mse = float(re.search(r"Mean Squared Error: ([\d.eE-]+)", cell_stream(nb, CELL_XGB_TRAIN)).group(1))

    numbers = {
        "files": {
            name: {"path": rel(p), "sha256": sha256(p), "bytes": p.stat().st_size} for name, p in inp.paths.items()
        },
        "pages": {REPORT_PDF: len(report), SLIDES_PDF: len(slides)},
        "notebook": {"cells": len(nb["cells"]), "nbformat": nb.get("nbformat")},
        "d1_horizon": {
            "baseline_rows_notebook": baseline_rows,
            "baseline_rows_report": report_rows,
            "baseline_t_max_bounds_s": [horizon["t_max_lo_s"], horizon["t_max_hi_s"]],
            "baseline_t_max_mid_s": horizon["t_max_mid_s"],
            "controlled_step_bound": ctl_steps,
            "rf_controlled_rows": rf_rows,
            "xgb_controlled_rows": xgb_rows,
            "rf_row_ratio": rf_rows / baseline_rows,
            "xgb_row_ratio": xgb_rows / baseline_rows,
            "rf_rowcount_implied_drop_pct": 100 * (1 - rf_rows / baseline_rows),
            "xgb_rowcount_implied_drop_pct": 100 * (1 - xgb_rows / baseline_rows),
            "horizon_implied_drop_pct": 100 * (1 - ctl_steps / horizon["t_max_mid_s"]),
            "reported_drops_pct": reported_drops(slides),
        },
        "d2_reroutes": {"rf": rf, "xgb": xgb, "first_route_identical_rf_vs_xgb": [same_first, len(common)]},
        "d4_models": {
            "model_compare_cell_18": _mse_table(cell_stream(nb, CELL_MODEL_COMPARE)),
            "model_compare_features": "CO2, CO, HC, PMx, X, Y",
            "rf_reroute_model_cell_30_test_mse": rf_mse,
            "rf_reroute_model_features": "CO2, CO, HC, PMx",
            "xgb_reroute_model_cell_45_test_mse": xgb_mse,
            "xgb_reroute_model_features": "CO2, CO, HC, PMx, X, Y",
            "normalized_df_used_after_cell_12": normalized_uses,
            "split": "train_test_split(test_size=0.2, random_state=42) on rows",
        },
        "d5_runs": {
            "multiple_runs_claim_pages": _find_pages(report, r"Multiple Simulation Runs"),
            "emission_files_parsed": sorted(
                set(re.findall(r"emissions_data[\w]*\.xml", "\n".join(cell_source(nb, i) for i in range(len(nb["cells"])))))
            ),
        },
        "d6_threshold": {
            "notebook_lines": _code_hits(nb, r"1\.88"),
            "report_g_per_mile_pages": _find_pages(report, r"1\.88 (grams per mile|g/mile)"),
            "slides_g_per_mile_pages": _find_pages(slides, r"1\.88.{0,60}?(grams per mile|g/mile)"),
            "colorbar_concentration_labels": _code_hits(nb, r"Predicted NOx \(.*g/m"),
        },
        "d7_hardcoded": {
            "replace_with_actual": _code_hits(nb, r"[Rr]eplace with actual"),
            "example_values": _code_hits(nb, r"Example percentage drops|Sample NOx emissions"),
            "hardcoded_drive_paths": _code_hits(nb, r"[A-Z]:\\\\?CodeBox|r?['\"]D:\\"),
            "collect_loop": loops["collect_cell_2"],
            "sample_cell_4_steps": sorted({v[0] for v in sample.values()}),
            "sample_cell_4_rows": {str(k): [v[0], v[1], v[2]] for k, v in sample.items()},
            "slides_template_text_pages": _find_pages(slides, r"Big numbers catch your audience"),
            "errors": {str(i): cell_errors(nb, i) for i in range(len(nb["cells"])) if cell_errors(nb, i)},
            "nox_compare_head_cell_55": nox_cmp[-1] if nox_cmp else None,
        },
        "d8_references": {
            "report_reference_page": _find_pages(report, r"Work Cited"),
            "slides_citation_pages": _find_pages(slides, r"Dong & Javid"),
            "source_tags_in_text_pages": _find_pages(report, r"\((MDPI|SpringerLink)\)"),
        },
    }
    return numbers


def run_audit() -> tuple[dict, list[str]]:
    """Extract everything, compute the numbers, write the JSON. Returns (numbers, files written)."""
    inp = load_inputs()
    written = write_extracts(inp.nb, inp.report, inp.slides)
    numbers = compute_numbers(inp)
    out = results_dir() / "legacy_audit" / "audit_numbers.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(numbers, indent=2, sort_keys=False), encoding="utf-8")
    written.append(rel(out))
    return numbers, written
