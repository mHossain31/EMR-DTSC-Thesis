"""Demand generation (docs/SPECIFICATION.md 6.5): one route file per (scenario, level, seed).

For each fleet group (cars, vans, trucks) ``randomTrips.py`` is called with the OSM Web Wizard's options for that
vehicle class (fringe factor 5, ``departLane="best"``, fringe ``departSpeed="max"``, ``--validate``,
``--remove-loops``, the wizard's via-edge types, and its class-specific minimum distances; cars also use
``--lanes`` and ``--allow-fringe.min-length 1000``), with an insertion density equal to the level's total density
times the group's share. ``--validate`` resamples unroutable origin-destination pairs and duarouter writes explicit
routes; the summary checks that every trip written was routed.

The group files are merged, sorted by departure, and every vehicle gets an explicit vType drawn from its group's
emission-class shares with a seeded generator. Vehicle types are therefore part of the route file, so every
controller sees the same fleet (P2), and the file's SHA-256 is recorded for the pairing check.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import sumolib
from lxml import etree

from nycemis.config import base_config
from nycemis.demand.fleet import Fleet, fleet, type_id, write_vtypes
from nycemis.manifest import sha256_file
from nycemis.network.build import net_path
from nycemis.network.scenario_files import WIZARD_CAR_FRINGE_FACTOR, random_trips
from nycemis.paths import data_dir, rel, scenarios_dir

CAR_EXTRA = ["--allow-fringe.min-length", "1000", "--lanes"]


def derived_seed(*parts: object) -> int:
    """Deterministic 31-bit seed from any parts (stable across runs and platforms)."""
    digest = hashlib.sha256(":".join(str(p) for p in parts).encode()).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


def vtypes_path(scenario: str) -> Path:
    return scenarios_dir() / scenario / "vtypes.add.xml"


def routes_path(scenario: str, level: str, seed: int) -> Path:
    return data_dir() / "demand" / scenario / level / f"seed_{seed}.rou.xml.gz"


def _class_args(fl: Fleet, group: str) -> list[str]:
    g = fl.groups[group]
    args = ["--vehicle-class", g.vclass, "--vclass", g.vclass, "--prefix", g.prefix,
            "--min-distance", f"{g.min_distance_m:g}", "--min-distance.fringe", "10"]
    if g.vclass == "passenger":
        args += CAR_EXTRA
    return args


def generate(scenario: str, density_per_h_km: float, seed: int, out: Path, level: str = "custom",
             depart_end_s: int | None = None) -> dict:
    """Generate the merged, typed route file ``out`` and return its summary (also written next to it)."""
    fl = fleet()
    proto = base_config().protocol
    end = depart_end_s if depart_end_s is not None else proto.depart_end_s
    net_file = net_path(scenario)
    write_vtypes(vtypes_path(scenario))
    tmp_dir = out.parent / f".tmp_seed_{seed}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    vehicles: list[etree._Element] = []
    groups_summary = {}
    for group in sorted(fl.groups):
        g = fl.groups[group]
        part = tmp_dir / f"{group}.rou.xml"
        res = random_trips(net_file, part, seed=derived_seed(scenario, level, seed, group, "trips"),
                           begin=proto.depart_begin_s, end=end,
                           insertion_density=density_per_h_km * g.share, fringe_factor=WIZARD_CAR_FRINGE_FACTOR,
                           class_args=_class_args(fl, group))
        if res["unroutable"] != 0:
            raise RuntimeError(f"{group}: {res['unroutable']} unroutable trips")
        tree = etree.parse(str(part))
        group_vehicles = tree.getroot().findall("vehicle")
        rng = np.random.Generator(np.random.PCG64(derived_seed(scenario, level, seed, group, "fleet")))
        classes = list(g.classes)
        probs = np.array([g.classes[c] for c in classes])
        draws = rng.choice(len(classes), size=len(group_vehicles), p=probs)
        for veh, k in zip(group_vehicles, draws, strict=True):
            veh.set("type", type_id(classes[k]))
        vehicles.extend(group_vehicles)
        groups_summary[group] = {"vehicles": len(group_vehicles), "trips_written": res["trips"],
                                 "unroutable": res["unroutable"]}
        part.unlink()
    tmp_dir.rmdir()

    vehicles.sort(key=lambda v: (float(v.get("depart")), v.get("id")))
    root = etree.Element("routes")
    root.text = "\n    "
    for veh in vehicles:
        veh.tail = "\n    "
        root.append(veh)
    if len(root):
        root[-1].tail = "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(out, "wb", mtime=0) as fh:  # mtime=0: identical inputs give byte-identical files
        fh.write(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))

    summary = summarize(scenario, out, vehicles)
    summary.update({"scenario": scenario, "level": level, "seed": seed, "density_per_h_km": density_per_h_km,
                    "depart_end_s": end, "groups": groups_summary, "route_file": rel(out),
                    "sha256": sha256_file(out)})
    out.with_name(out.name.replace(".rou.xml.gz", ".summary.json")).write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def summarize(scenario: str, route_file: Path, vehicles: list | None = None) -> dict:
    net = sumolib.net.readNet(str(net_path(scenario)))
    if vehicles is None:
        with gzip.open(route_file, "rb") as fh:
            vehicles = etree.parse(fh).getroot().findall("vehicle")
    lengths, fringe_starts, types = [], 0, {}
    for veh in vehicles:
        edges = veh.find("route").get("edges").split()
        lengths.append(sum(net.getEdge(e).getLength() for e in edges))
        if net.getEdge(edges[0]).is_fringe():
            fringe_starts += 1
        types[veh.get("type")] = types.get(veh.get("type"), 0) + 1
    n = len(vehicles)
    return {"vehicles": n, "mean_route_length_m": round(float(np.mean(lengths)), 1) if n else 0.0,
            "fringe_start_share": round(fringe_starts / n, 4) if n else 0.0, "types": dict(sorted(types.items()))}
