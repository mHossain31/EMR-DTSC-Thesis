"""Validate a built network and write ``network_report.md`` and ``network_map.png`` (docs/SPECIFICATION.md 6.2 step 3).

Checks: bounding-box match (OSM scenarios), edge count in [1,500, 20,000] (OSM scenarios), lane-km, traffic-light
count, strong connectivity of the retained network, share of dead-end edges, speed-limit and road-class
distributions, and no zero-length edges.
"""

from __future__ import annotations

import collections
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import sumolib  # noqa: E402

from nycemis.config import ScenarioConfig  # noqa: E402
from nycemis.network.build import net_path, report_dir  # noqa: E402
from nycemis.paths import rel  # noqa: E402

EDGE_COUNT_RANGE = (1500, 20000)
MIN_EDGE_LENGTH_M = 0.1
BBOX_INNER_SHRINK = 0.05  # the net must cover the bbox shrunk by 5% on each side
# Overpass returns whole ways and netconvert keeps an edge if any part lies in the box, so a few long fringe edges
# reach outside; the match is measured as the share of lane-km whose segment midpoints lie inside the box.
MIN_INSIDE_SHARE = 0.90
MIN_LARGEST_SCC_SHARE = 0.90

ROAD_CLASSES = {
    "motorway/trunk": ("motorway", "motorway_link", "trunk", "trunk_link"),
    "primary/secondary": ("primary", "primary_link", "secondary", "secondary_link"),
    "tertiary": ("tertiary", "tertiary_link"),
    "residential/service": ("residential", "living_street", "service", "unclassified", "road", "track"),
}
CLASS_COLORS = {
    "motorway/trunk": "#b2182b",
    "primary/secondary": "#ef8a62",
    "tertiary": "#67a9cf",
    "residential/service": "#999999",
    "other": "#cccccc",
}


def road_class(edge_type: str) -> str:
    """Map a netconvert edge type (``highway.residential``, possibly ``a|b``) to one of four classes."""
    parts = [p.split(".", 1)[-1] for p in (edge_type or "").split("|") if p]
    for name, members in ROAD_CLASSES.items():
        if any(p in members for p in parts):
            return name
    return "other"


@dataclass
class Validation:
    scenario: str
    checks: dict[str, dict] = field(default_factory=dict)
    stats: dict = field(default_factory=dict)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks[name] = {"ok": bool(ok), "detail": detail}

    @property
    def ok(self) -> bool:
        return all(c["ok"] for c in self.checks.values())


def _geo_bbox(net: sumolib.net.Net) -> tuple[float, float, float, float] | None:
    if not net.hasGeoProj():
        return None
    (xmin, ymin), (xmax, ymax) = net.getBBoxXY()
    w, s = net.convertXY2LonLat(xmin, ymin)
    e, n = net.convertXY2LonLat(xmax, ymax)
    return (w, s, e, n)


def _lane_km_inside_share(net: sumolib.net.Net, edges: list, bbox: tuple[float, float, float, float]) -> float:
    w, s, e, n = bbox
    total = inside = 0.0
    for ed in edges:
        shape, lanes = ed.getShape(), ed.getLaneNumber()
        for (x0, y0), (x1, y1) in zip(shape, shape[1:], strict=False):
            seg = math.hypot(x1 - x0, y1 - y0) * lanes
            lon, lat = net.convertXY2LonLat((x0 + x1) / 2, (y0 + y1) / 2)
            total += seg
            if w <= lon <= e and s <= lat <= n:
                inside += seg
    return inside / total if total else 0.0


def validate(cfg: ScenarioConfig) -> Validation:
    path = net_path(cfg.id)
    net = sumolib.net.readNet(str(path))
    edges = [e for e in net.getEdges() if e.getFunction() != "internal"]
    v = Validation(cfg.id)

    if cfg.source == "osm" and cfg.bbox is not None:
        w, s, e, n = cfg.bbox
        gb = _geo_bbox(net)
        dx, dy = e - w, n - s
        inner = (w + BBOX_INNER_SHRINK * dx, s + BBOX_INNER_SHRINK * dy, e - BBOX_INNER_SHRINK * dx,
                 n - BBOX_INNER_SHRINK * dy)
        covers = gb is not None and gb[0] <= inner[0] and gb[1] <= inner[1] and gb[2] >= inner[2] \
            and gb[3] >= inner[3]
        inside = _lane_km_inside_share(net, edges, cfg.bbox)
        v.stats["lane_km_inside_bbox_share"] = round(inside, 4)
        v.add("bbox_match", covers and inside >= MIN_INSIDE_SHARE,
              f"net covers the box shrunk by {BBOX_INNER_SHRINK:.0%}: {covers}; {inside:.1%} of lane-km inside "
              f"the box (minimum {MIN_INSIDE_SHARE:.0%}); net lon/lat extent "
              f"{tuple(round(x, 4) for x in gb) if gb else None}; box {cfg.bbox}")
        lo, hi = EDGE_COUNT_RANGE
        v.add("edge_count", lo <= len(edges) <= hi, f"{len(edges)} non-internal edges (allowed {lo}-{hi})")
    else:
        v.add("edge_count", len(edges) > 0, f"{len(edges)} non-internal edges (smoke grid)")

    lane_km = sum(ed.getLength() * ed.getLaneNumber() for ed in edges) / 1000.0
    tls = len(net.getTrafficLights())
    v.stats.update({"edges": len(edges), "nodes": len(net.getNodes()), "lane_km": round(lane_km, 2),
                    "traffic_lights": tls})
    v.add("traffic_lights", tls > 0, f"{tls} signalised junctions")

    g = nx.DiGraph()
    g.add_nodes_from(ed.getID() for ed in edges)
    for ed in edges:
        for succ in ed.getOutgoing():
            if succ.getFunction() != "internal":
                g.add_edge(ed.getID(), succ.getID())
    sccs = sorted(nx.strongly_connected_components(g), key=len, reverse=True)
    largest = len(sccs[0]) if sccs else 0
    share = largest / max(1, len(edges))
    v.stats.update({"largest_scc_edges": largest, "largest_scc_share": round(share, 4),
                    "scc_count": len(sccs), "weak_components": nx.number_weakly_connected_components(g)})
    v.add("strong_connectivity", share >= MIN_LARGEST_SCC_SHARE,
          f"largest strongly connected component holds {share:.1%} of edges ({len(sccs)} components; "
          f"minimum {MIN_LARGEST_SCC_SHARE:.0%})")

    dead_ends = [ed.getID() for ed in edges if not any(s.getFunction() != "internal" for s in ed.getOutgoing())]
    sources = [ed.getID() for ed in edges if not any(s.getFunction() != "internal" for s in ed.getIncoming())]
    v.stats.update({"dead_end_edges": len(dead_ends), "dead_end_share": round(len(dead_ends) / max(1, len(edges)), 4),
                    "source_edges": len(sources)})
    v.add("dead_end_share", True, f"{len(dead_ends)} edges without a successor "
                                  f"({len(dead_ends) / max(1, len(edges)):.1%}); reported, not gated")

    zero = [ed.getID() for ed in edges if ed.getLength() < MIN_EDGE_LENGTH_M]
    v.add("no_zero_length_edges", not zero, f"{len(zero)} edges shorter than {MIN_EDGE_LENGTH_M} m")

    speeds = collections.Counter(round(ed.getSpeed() * 3.6) for ed in edges)
    classes_n = collections.Counter(road_class(ed.getType()) for ed in edges)
    classes_km = collections.Counter()
    for ed in edges:
        classes_km[road_class(ed.getType())] += ed.getLength() * ed.getLaneNumber() / 1000.0
    types = collections.Counter(ed.getType() for ed in edges)
    v.stats.update({
        "speed_limits_kmh": dict(sorted(speeds.items())),
        "road_class_edges": dict(classes_n),
        "road_class_lane_km": {k: round(x, 2) for k, x in classes_km.items()},
        "edge_types": dict(types.most_common()),
    })
    _write_outputs(cfg, net, edges, v)
    return v


def _write_outputs(cfg: ScenarioConfig, net: sumolib.net.Net, edges: list, v: Validation) -> None:
    rdir = report_dir(cfg.id)
    rdir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 9))
    for ed in edges:
        xs, ys = zip(*ed.getShape(), strict=True)
        cls = road_class(ed.getType())
        ax.plot(xs, ys, color=CLASS_COLORS[cls], linewidth=0.5 + 0.4 * ed.getLaneNumber(), solid_capstyle="round")
    for cls, color in CLASS_COLORS.items():
        ax.plot([], [], color=color, linewidth=2, label=cls)
    tl_nodes = [net.getNode(tl.getID()) for tl in net.getTrafficLights() if net.hasNode(tl.getID())]
    if tl_nodes:
        ax.scatter([nd.getCoord()[0] for nd in tl_nodes], [nd.getCoord()[1] for nd in tl_nodes], s=6,
                   color="#1a9850", label="traffic light", zorder=3)
    ax.set_aspect("equal")
    ax.set_title(f"{cfg.name}: {v.stats['edges']} edges, {v.stats['lane_km']} lane-km")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(rdir / "network_map.png", dpi=150)
    plt.close(fig)

    build = json.loads((rdir / "network_build.json").read_text(encoding="utf-8"))
    lines = [
        f"# Network report: {cfg.name}",
        "",
        "Generated by `python -m nycemis net build`; do not edit by hand.",
        "",
        f"- Net file: `{build['net_file']}` (SHA-256 `{build['net_sha256'][:16]}...`), SUMO {build['sumo_version']}",
        f"- Built in {build['seconds']} s with {build['warnings_count']} netconvert warnings",
        f"- Result: **{'PASS' if v.ok else 'FAIL'}**",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    lines += [f"| {k} | {'pass' if c['ok'] else 'FAIL'} | {c['detail']} |" for k, c in v.checks.items()]
    lines += ["", "## Statistics", "", "| Quantity | Value |", "|---|---|"]
    for key in ("edges", "nodes", "lane_km", "traffic_lights", "largest_scc_edges", "largest_scc_share",
                "scc_count", "weak_components", "dead_end_edges", "dead_end_share", "source_edges"):
        lines.append(f"| {key} | {v.stats[key]} |")
    lines += ["", "## Road classes", "", "| Class | Edges | Lane-km |", "|---|---|---|"]
    for cls in CLASS_COLORS:
        if cls in v.stats["road_class_edges"]:
            lines.append(f"| {cls} | {v.stats['road_class_edges'][cls]} | {v.stats['road_class_lane_km'][cls]} |")
    lines += ["", "## Speed limits", "", "| km/h | Edges |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in v.stats["speed_limits_kmh"].items()]
    lines += ["", "## Edge types", "", "| Type | Edges |", "|---|---|"]
    lines += [f"| {k or '(none)'} | {n} |" for k, n in v.stats["edge_types"].items()]
    if build.get("warnings_sample"):
        lines += ["", "## netconvert warnings (first 20)", ""]
        lines += [f"- {w}" for w in build["warnings_sample"]]
    extra = rdir / "opendrive_check.json"
    if extra.is_file():
        od = json.loads(extra.read_text(encoding="utf-8"))
        lines += ["", "## OpenDRIVE export check (docs/SPECIFICATION.md 6.2 step 5)", ""]
        for variant in od["variants"]:
            lines.append(f"- `{' '.join(variant['options'])}`: {'ok' if variant['ok'] else 'FAILED'}, "
                         f"{variant['warnings_count']} warnings, {variant['bytes']:,} bytes")
    smoke = rdir / "smoke_run.json"
    if smoke.is_file():
        sm = json.loads(smoke.read_text(encoding="utf-8"))
        lines += ["", "## Headless smoke run (docs/SPECIFICATION.md 6.2 step 4)", "",
                  f"- {sm['seconds_simulated']} s simulated, {sm['vehicles_inserted']} vehicles inserted, "
                  f"errors: {sm['errors']}, warnings: {sm['warnings_count']}, wall-clock {sm['wall_s']} s",
                  f"- GUI: `{sm['gui_command']}`"]
    (rdir / "network_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (rdir / "network_validation.json").write_text(
        json.dumps({"ok": v.ok, "checks": v.checks, "stats": v.stats}, indent=2) + "\n", encoding="utf-8")


def report_path(scenario: str) -> Path:
    return report_dir(scenario) / "network_report.md"


def summary(v: Validation) -> str:
    rows = [f"{v.scenario}: {'PASS' if v.ok else 'FAIL'} ({rel(report_path(v.scenario))})"]
    rows += [f"  [{'ok' if c['ok'] else 'FAIL'}] {k}: {c['detail']}" for k, c in v.checks.items()]
    return "\n".join(rows)
