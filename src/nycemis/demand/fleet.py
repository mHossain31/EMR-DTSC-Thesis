"""Fleet definition (``configs/fleet.yaml``), vType file, and the emission-class probe (docs/SPECIFICATION.md 6.4).

One vType per emission class; vehicle dimensions and dynamics are SUMO's defaults for the group's vClass. Type ids
are derived from the class name (``HBEFA4/PC_petrol_Euro-4`` -> ``PC_petrol_Euro-4``).
"""

from __future__ import annotations

import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator

from nycemis import env
from nycemis.config import Strict, load_yaml
from nycemis.paths import configs_dir

SHARE_TOLERANCE = 1e-9


class Group(Strict):
    share: float = Field(gt=0, le=1)
    vclass: str
    prefix: str
    min_distance_m: float = Field(ge=0)
    classes: dict[str, float]

    @model_validator(mode="after")
    def _sum(self) -> Group:
        total = sum(self.classes.values())
        if abs(total - 1.0) > SHARE_TOLERANCE or any(v <= 0 for v in self.classes.values()):
            raise ValueError(f"class shares must be positive and sum to 1 (got {total})")
        return self


class Fleet(Strict):
    groups: dict[str, Group]

    @model_validator(mode="after")
    def _sum(self) -> Fleet:
        total = sum(g.share for g in self.groups.values())
        if abs(total - 1.0) > SHARE_TOLERANCE:
            raise ValueError(f"group shares must sum to 1 (got {total})")
        prefixes = [g.prefix for g in self.groups.values()]
        if len(set(prefixes)) != len(prefixes):
            raise ValueError("group prefixes must be distinct")
        return self

    def all_classes(self) -> list[str]:
        return [c for g in self.groups.values() for c in g.classes]


@lru_cache(maxsize=1)
def fleet() -> Fleet:
    return Fleet.model_validate(load_yaml(configs_dir() / "fleet.yaml"))


def type_id(emission_class: str) -> str:
    return emission_class.split("/", 1)[-1]


def vtypes_xml(fl: Fleet | None = None) -> str:
    fl = fl or fleet()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             "<!-- Generated from configs/fleet.yaml by nycemis; one vType per emission class. -->",
             "<additional>"]
    for name, group in fl.groups.items():
        lines.append(f"    <!-- {name}: share {group.share:g}, vClass {group.vclass} -->")
        for cls in group.classes:
            lines.append(f'    <vType id="{type_id(cls)}" vClass="{group.vclass}" emissionClass="{cls}"/>')
    lines.append("</additional>")
    return "\n".join(lines) + "\n"


def write_vtypes(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(vtypes_xml(), encoding="utf-8")
    return path


def probe_classes(net: Path, classes: list[str] | None = None) -> dict[str, dict]:
    """Run one short simulation per emission class and report whether SUMO accepts it and emits NOx > 0."""
    import libsumo as traci  # one simulation at a time in this process

    classes = classes or fleet().all_classes()
    results: dict[str, dict] = {}
    edges = _two_connected_edges(net)
    for cls in classes:
        with tempfile.TemporaryDirectory(prefix="probe_") as tmp:
            rou = Path(tmp) / "probe.rou.xml"
            rou.write_text(
                "<routes>\n"
                f'  <vType id="probe" emissionClass="{cls}"/>\n'
                f'  <route id="r" edges="{edges[0]} {edges[1]}"/>\n'
                '  <vehicle id="v" type="probe" route="r" depart="0"/>\n'
                "</routes>\n",
                encoding="utf-8",
            )
            try:
                traci.start([str(env.sumo_binary("sumo")), "-n", str(net), "-r", str(rou), "--no-step-log",
                             "--end", "60", "--no-warnings"])
                nox_mg = 0.0
                accepted = traci.vehicletype.getEmissionClass("probe")
                for _ in range(60):
                    traci.simulationStep()
                    if "v" in traci.vehicle.getIDList():
                        nox_mg += traci.vehicle.getNOxEmission("v")  # mg/s over a 1 s step
                results[cls] = {"accepted": accepted == cls, "reported": accepted, "nox_mg": round(nox_mg, 3)}
            except traci.TraCIException as exc:
                results[cls] = {"accepted": False, "error": str(exc)}
            finally:
                if traci.isLoaded():
                    traci.close()
    return results


def _two_connected_edges(net: Path) -> tuple[str, str]:
    import sumolib

    n = sumolib.net.readNet(str(net))
    for e in n.getEdges():
        for nxt in e.getOutgoing():
            if e.getLength() > 50 and nxt.getLength() > 50 and e.allows("passenger") and nxt.allows("passenger"):
                return e.getID(), nxt.getID()
    raise RuntimeError(f"no pair of connected edges in {net}")


def check_probe(results: dict[str, dict]) -> list[str]:
    """Return a list of problems (empty when every class was accepted and emitted NOx)."""
    return [f"{c}: {r}" for c, r in results.items() if not r.get("accepted") or r.get("nox_mg", 0) <= 0]


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, env=env.subprocess_env(), check=False)
