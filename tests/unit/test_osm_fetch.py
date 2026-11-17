"""A frozen OSM extract is reused only for the box it was downloaded for."""

from __future__ import annotations

import json

import pytest

from nycemis.network import osm_fetch


def test_frozen_extract_reused_only_for_the_same_box(tmp_path, monkeypatch) -> None:
    target = tmp_path / "x.osm.xml.gz"
    target.write_bytes(b"")
    meta = tmp_path / "x.download_meta.json"
    meta.write_text(json.dumps({"bbox_wsen": [1.0, 2.0, 3.0, 4.0]}), encoding="utf-8")
    monkeypatch.setattr(osm_fetch, "osm_path", lambda s: target)
    monkeypatch.setattr(osm_fetch, "meta_path", lambda s: meta)
    monkeypatch.setattr(osm_fetch.manifest, "verify", lambda p: True)
    monkeypatch.setattr(osm_fetch, "rel", lambda p: p.name)  # rel() only accepts paths inside the repository
    calls: list[tuple[float, ...]] = []

    def attempt(scenario, bbox, url, workdir):
        calls.append(bbox)
        raise RuntimeError("offline")

    monkeypatch.setattr(osm_fetch, "_attempt", attempt)
    assert osm_fetch.fetch("x", (1.0, 2.0, 3.0, 4.0))["bbox_wsen"] == [1.0, 2.0, 3.0, 4.0]
    assert not calls
    with pytest.raises(RuntimeError):
        osm_fetch.fetch("x", (1.0, 2.0, 3.0, 5.0), max_wait_min=0, base_delay_s=0)
    assert calls and calls[0] == (1.0, 2.0, 3.0, 5.0)
