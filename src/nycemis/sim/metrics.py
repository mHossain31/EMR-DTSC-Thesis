"""Parse SUMO outputs into trip and run metrics with explicit units (docs/SPECIFICATION.md 4.5, P10).

Tripinfo emissions are totals per trip in mg (``NOx_abs`` etc., emissions device). Durations are in s, lengths in
m. ``write-unfinished`` adds vehicles still running at the end; they are flagged ``finished = False``.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from lxml import etree

TRIP_COLUMNS = {
    "id": "string", "vtype": "string", "depart_s": "float64", "arrival_s": "float64", "duration_s": "float64",
    "route_length_m": "float64", "time_loss_s": "float64", "waiting_s": "float64", "depart_delay_s": "float64",
    "reroutes": "int32", "finished": "bool", "nox_mg": "float64", "co2_mg": "float64", "co_mg": "float64",
    "hc_mg": "float64", "pmx_mg": "float64", "fuel_mg": "float64",
}
LOADED_PERIOD_START_S = 900  # speed ratio uses trips departing in [900, depart_end] (15 min warm-up excluded)


def parse_tripinfo(path: Path) -> pd.DataFrame:
    rows = []
    for _, el in etree.iterparse(str(path), tag="tripinfo"):
        em = el.find("emissions")
        arrival = float(el.get("arrival"))
        rows.append({
            "id": el.get("id"), "vtype": el.get("vType"), "depart_s": float(el.get("depart")),
            "arrival_s": arrival, "duration_s": float(el.get("duration")),
            "route_length_m": float(el.get("routeLength")), "time_loss_s": float(el.get("timeLoss")),
            "waiting_s": float(el.get("waitingTime")), "depart_delay_s": float(el.get("departDelay")),
            "reroutes": int(el.get("rerouteNo")), "finished": arrival >= 0,
            "nox_mg": float(em.get("NOx_abs")), "co2_mg": float(em.get("CO2_abs")),
            "co_mg": float(em.get("CO_abs")), "hc_mg": float(em.get("HC_abs")),
            "pmx_mg": float(em.get("PMx_abs")), "fuel_mg": float(em.get("fuel_abs")),
        })
        el.clear()
    df = pd.DataFrame(rows, columns=list(TRIP_COLUMNS))
    return df.astype(TRIP_COLUMNS)


def parse_statistics(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")

    def attr(tag: str, name: str) -> float:
        m = re.search(rf"<{tag}\b[^>]*\b{name}=\"([^\"]+)\"", text)
        if not m:
            raise ValueError(f"{path}: <{tag} {name}> not found")
        return float(m.group(1))

    return {
        "loaded": int(attr("vehicles", "loaded")), "inserted": int(attr("vehicles", "inserted")),
        "running": int(attr("vehicles", "running")), "waiting": int(attr("vehicles", "waiting")),
        "teleports": int(attr("teleports", "total")), "teleports_jam": int(attr("teleports", "jam")),
        "collisions": int(attr("safety", "collisions")),
        "emergency_stops": int(attr("safety", "emergencyStops")),
    }


def speed_ratio(trips: pd.DataFrame, depart_end_s: float) -> float:
    """Demand-weighted ratio of ideal to actual travel time, sum(duration - timeLoss) / sum(duration).

    SUMO's timeLoss is the time lost to driving below the vehicle's ideal speed (its speed factor times the
    limit), so the ratio is the mean speed over the desired speed, weighted by travel time. Finished trips that
    departed in the loaded period only.
    """
    sel = trips[trips.finished & (trips.depart_s >= LOADED_PERIOD_START_S) & (trips.depart_s <= depart_end_s)]
    if sel.empty:
        return float("nan")
    return float((sel.duration_s - sel.time_loss_s).sum() / sel.duration_s.sum())


def run_metrics(trips: pd.DataFrame, stats: dict, n_route_vehicles: int, depart_end_s: float) -> dict:
    fin = trips[trips.finished]
    vkm = float(trips.route_length_m.sum() / 1000.0)
    arrived = int(len(fin))
    completion = arrived / n_route_vehicles if n_route_vehicles else float("nan")
    return {
        "total_nox_g": float(trips.nox_mg.sum() / 1000.0),
        "total_co2_kg": float(trips.co2_mg.sum() / 1e6),
        "nox_mg_per_vkm": float(trips.nox_mg.sum() / vkm) if vkm else float("nan"),
        "mean_tt_s": float(fin.duration_s.mean()) if arrived else float("nan"),
        "p95_tt_s": float(np.percentile(fin.duration_s, 95)) if arrived else float("nan"),
        "mean_timeloss_s": float(fin.time_loss_s.mean()) if arrived else float("nan"),
        "mean_wait_s": float(fin.waiting_s.mean()) if arrived else float("nan"),
        "vkm_total": vkm,
        "mean_depart_delay_s": float(trips.depart_delay_s.mean()) if len(trips) else float("nan"),
        "n_route_vehicles": int(n_route_vehicles),
        "arrived": arrived,
        "unfinished": int((~trips.finished).sum()),
        "completion_rate": completion,
        "teleports": stats["teleports"],
        "teleport_frac": stats["teleports"] / n_route_vehicles if n_route_vehicles else float("nan"),
        "collisions": stats["collisions"],
        "speed_ratio": speed_ratio(trips, depart_end_s),
        "last_arrival_s": float(fin.arrival_s.max()) if arrived else float("nan"),
    }
