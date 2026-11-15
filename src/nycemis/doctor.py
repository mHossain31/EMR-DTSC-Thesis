"""``python -m nycemis doctor``: check that this machine can run every stage (docs/SPECIFICATION.md 5.2).

Each check is marked required or informational. Required failures make ``doctor`` exit non-zero. Informational
items (TeX engine, CARLA readiness) are reported but do not fail the gate: TeX is needed only at M9 and CARLA only
for the optional M10.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

from nycemis import env
from nycemis.paths import repo_root

OVERPASS_STATUS_URLS = (
    "https://overpass-api.de/api/status",
    "https://overpass.private.coffee/api/status",
    "https://maps.mail.ru/osm/tools/overpass/api/status",
    "https://overpass.kumi.systems/api/status",
)
MIN_FREE_GB = 50.0
TOOLS_NEEDED = (
    "osmGet.py",
    "osmBuild.py",
    "osmWebWizard.py",
    "randomTrips.py",
    "net/netcheck.py",
)
BINARIES_NEEDED = ("sumo", "sumo-gui", "netconvert", "netgenerate", "duarouter", "polyconvert")


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _python() -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) in {(3, 11), (3, 12)}
    return Check("python", ok, f"{sys.version.split()[0]} at {sys.executable}")


def _os_cpu_disk() -> list[Check]:
    info = env.platform_info()
    cores = os.cpu_count() or 0
    free_gb = shutil.disk_usage(repo_root()).free / 1e9
    return [
        Check("os", True, f"{info['os']} {info['os_release']} ({info['machine']})"),
        Check("cpu_cores", cores >= 2, f"{cores} logical cores; default workers = {max(1, cores - 1)}"),
        Check("free_disk", free_gb >= MIN_FREE_GB, f"{free_gb:.0f} GB free (need >= {MIN_FREE_GB:.0f} GB)"),
    ]


def _sumo() -> list[Check]:
    checks: list[Check] = []
    try:
        home = env.sumo_home()
        checks.append(Check("sumo_home", True, str(home)))
    except RuntimeError as exc:
        return [Check("sumo_home", False, str(exc))]
    try:
        checks.append(Check("sumo_version", True, env.sumo_version()))
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        checks.append(Check("sumo_version", False, str(exc)))
    for name in BINARIES_NEEDED:
        try:
            checks.append(Check(f"bin:{name}", True, str(env.sumo_binary(name).name)))
        except FileNotFoundError as exc:
            checks.append(Check(f"bin:{name}", False, str(exc)))
    for tool in TOOLS_NEEDED:
        try:
            env.sumo_tool(tool)
            checks.append(Check(f"tool:{tool}", True, "present"))
        except FileNotFoundError as exc:
            checks.append(Check(f"tool:{tool}", False, str(exc)))
    backend = env.load_backend("libsumo")
    checks.append(
        Check("libsumo_import", backend.name == "libsumo", f"backend loaded: {backend.name}")
    )
    return checks


def _tex() -> Check:
    local = repo_root() / "tools" / ("tectonic.exe" if os.name == "nt" else "tectonic")
    found = [p for p in ("tectonic", "latexmk", "pdflatex") if shutil.which(p)]
    if local.is_file():
        found.insert(0, f"tools/{local.name}")
    detail = ", ".join(found) if found else "none found (needed at M9 only; see docs/SPECIFICATION.md M9)"
    return Check("tex_engine", bool(found), detail, required=False)


def _overpass() -> Check:
    errors = []
    for url in OVERPASS_STATUS_URLS:
        req = urllib.request.Request(url, headers={"User-Agent": "nycemis-doctor/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                first = resp.read(200).decode("utf-8", "replace").splitlines()[:2]
                return Check("overpass", True, f"{url} reachable: {' | '.join(first)}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(f"{url}: {exc}")
    return Check("overpass", False, "; ".join(errors))


def _git() -> Check:
    root = repo_root()
    if not (root / ".git").exists():
        return Check("git", False, "not a git repository")
    out = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--branch"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return Check("git", False, out.stderr.strip())
    lines = out.stdout.splitlines()
    dirty = len(lines) - 1
    return Check("git", True, f"{lines[0] if lines else ''}; {dirty} changed paths")


def _carla() -> Check:
    gpu = "none"
    smi = shutil.which("nvidia-smi")
    if smi:
        out = subprocess.run(
            [smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            gpu = out.stdout.strip().splitlines()[0]
    capable_os = sys.platform.startswith(("win", "linux"))
    root = os.environ.get("CARLA_ROOT", "unset")
    capable = capable_os and gpu != "none"
    return Check(
        "carla_ready",
        capable,
        f"os_ok={capable_os}; nvidia_gpu={gpu}; CARLA_ROOT={root} (informational, M10 only)",
        required=False,
    )


def run_checks(include_network: bool = True) -> list[Check]:
    checks = [_python(), *_os_cpu_disk(), *_sumo(), _tex(), _git(), _carla()]
    if include_network:
        checks.append(_overpass())
    return checks


def format_report(checks: list[Check]) -> str:
    rows = []
    for c in checks:
        status = "OK  " if c.ok else ("FAIL" if c.required else "WARN")
        rows.append(f"[{status}] {c.name:<22} {c.detail}")
    failed = [c for c in checks if c.required and not c.ok]
    rows.append("")
    rows.append("doctor: GREEN" if not failed else f"doctor: RED ({len(failed)} required check(s) failed)")
    return "\n".join(rows)
