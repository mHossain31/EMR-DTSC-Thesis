"""Download the OSM extract of a scenario's bounding box with SUMO's ``osmGet.py`` (docs/SPECIFICATION.md 6.2 step 1).

Each attempt asks one Overpass mirror, so the metadata can name the endpoint that answered. Mirrors rotate;
between rounds the delay grows (backoff) until ``max_wait_min`` is used up. The extract is frozen as
``data/osm/<scenario>.osm.xml.gz`` with its SHA-256 in ``data/MANIFEST.json`` and ``download_meta.json`` beside it.
Polygons (buildings, land use) are not downloaded: the networks do not need them (recorded in docs/DESIGN.md).
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from nycemis import env, manifest
from nycemis.paths import data_dir, rel

log = logging.getLogger(__name__)

OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://osm.hpi.de/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
ATTEMPT_TIMEOUT_S = 600

# The Web Wizard's "Highway" road-type category (tools/webWizard/script.js), with the "_link" types it adds for
# motorway, trunk, primary, secondary and tertiary. Only this category is requested: the network is car-only, so
# pedestrian, rail, air, water and aerial categories are not needed. osmGet then fetches these ways, their nodes,
# and the relations they belong to (turn restrictions included).
WIZARD_HIGHWAY_TYPES = [
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "unsurfaced", "service",
    "raceway", "bus_guideway",
]
ROAD_TYPES = {"Highway": WIZARD_HIGHWAY_TYPES}


def osm_path(scenario: str) -> Path:
    return data_dir() / "osm" / f"{scenario}.osm.xml.gz"


def meta_path(scenario: str) -> Path:
    return data_dir() / "osm" / f"{scenario}.download_meta.json"


def _check_osm(path: Path) -> dict:
    """Parse the downloaded file enough to confirm it is OSM XML with data; return counts and the OSM timestamp."""
    nodes = ways = relations = 0
    osm_base = None
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        head = fh.read(4096)
        if "<osm" not in head:
            raise ValueError(f"{path} is not OSM XML: {head[:200]!r}")
        m = re.search(r'osm_base="([^"]+)"', head)
        osm_base = m.group(1) if m else None
        fh.seek(0)
        for line in fh:
            s = line.lstrip()
            if s.startswith("<node"):
                nodes += 1
            elif s.startswith("<way"):
                ways += 1
            elif s.startswith("<relation"):
                relations += 1
    if nodes == 0 or ways == 0:
        raise ValueError(f"{path} holds no nodes or ways")
    return {"nodes": nodes, "ways": ways, "relations": relations, "osm_base": osm_base}


def _attempt(scenario: str, bbox: tuple[float, float, float, float], url: str, workdir: Path) -> Path:
    cmd = [
        sys.executable,
        str(env.sumo_tool("osmGet.py")),
        # "--bbox=" form: the value starts with "-" (western longitude), which argparse would read as an option.
        "--bbox=" + ",".join(f"{v:.6f}" for v in bbox),
        "--prefix",
        scenario,
        "--output-dir",
        str(workdir),
        "--gzip",
        "--road-types",
        json.dumps(ROAD_TYPES),
        "--url",
        url,
        "--retries",
        "0",
        "--verbose",
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=ATTEMPT_TIMEOUT_S, env=env.subprocess_env(), check=False
    )
    produced = sorted(workdir.glob(f"{scenario}*.osm.xml.gz"))
    if proc.returncode != 0 or not produced:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
        raise RuntimeError(f"osmGet via {url} failed (exit {proc.returncode}): {' | '.join(tail)}")
    return produced[0]


def fetch(
    scenario: str,
    bbox: tuple[float, float, float, float],
    max_wait_min: float = 180.0,
    base_delay_s: float = 60.0,
    force: bool = False,
) -> dict:
    """Download (or reuse) the frozen extract. Returns the download metadata. A frozen extract is reused only when its
    hash matches the manifest and it was downloaded for the same box as the scenario config now gives."""
    target = osm_path(scenario)
    if target.is_file() and manifest.verify(target) and not force:
        frozen = json.loads(meta_path(scenario).read_text(encoding="utf-8"))
        if frozen.get("bbox_wsen") == list(bbox):
            log.info("%s already frozen (hash matches the manifest); not downloading again", rel(target))
            return frozen
        log.warning("%s was downloaded for box %s, but the scenario config now gives %s: downloading again",
                    rel(target), frozen.get("bbox_wsen"), list(bbox))

    target.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 60 * max_wait_min
    delay = base_delay_s
    errors: list[str] = []
    round_no = 0
    while True:
        round_no += 1
        for url in OVERPASS_MIRRORS:
            with tempfile.TemporaryDirectory(prefix="osmget_") as tmp:
                started = dt.datetime.now(dt.UTC)
                try:
                    produced = _attempt(scenario, bbox, url, Path(tmp))
                    counts = _check_osm(produced)
                except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
                    errors.append(f"round {round_no} {url}: {exc}")
                    log.warning("OSM download attempt failed: %s", exc)
                    continue
                shutil.move(str(produced), target)
            meta = {
                "scenario": scenario,
                "bbox_wsen": list(bbox),
                "endpoint": url,
                "downloaded_utc": started.isoformat(timespec="seconds"),
                "osm_base": counts["osm_base"],
                "counts": {k: counts[k] for k in ("nodes", "ways", "relations")},
                "shapes": False,
                "road_types": ROAD_TYPES,
                "tool": "osmGet.py (SUMO tools)",
                "sumo_version": env.sumo_version(),
                "failed_attempts_before_success": len(errors),
            }
            meta_path(scenario).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
            manifest.record(target, kind="osm_extract", scenario=scenario, endpoint=url,
                            osm_base=counts["osm_base"])
            log.info("froze %s (%d nodes, %d ways) from %s", rel(target), counts["nodes"], counts["ways"], url)
            return meta
        if time.monotonic() + delay > deadline:
            raise RuntimeError(
                f"OSM download for {scenario} failed after {round_no} round(s):\n" + "\n".join(errors[-8:])
            )
        log.warning("all Overpass mirrors failed in round %d; waiting %.0f s", round_no, delay)
        time.sleep(delay)
        delay = min(delay * 2, 900.0)
