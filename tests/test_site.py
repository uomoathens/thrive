import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("geopandas")

from thrive.site import SPAN, SiteError, build

ROOT = Path(__file__).resolve().parents[1]


def copy_repo(tmp_path):
    for part in ("docs", "results", "config"):
        shutil.copytree(ROOT / part, tmp_path / part)
    shutil.copy(ROOT / "README.md", tmp_path / "README.md")
    return tmp_path


def test_page_and_readme_match_the_results():
    out = build(ROOT, write=False)
    assert out["changed"] == []


def test_every_marked_number_is_filled(tmp_path):
    root = copy_repo(tmp_path)
    out = build(root)
    for name in ("docs/index.html", "README.md"):
        text = (root / name).read_text(encoding="utf-8")
        for m in SPAN.finditer(text):
            assert m.group(3) == out["values"][m.group(2)]


def test_second_run_changes_nothing(tmp_path):
    root = copy_repo(tmp_path)
    build(root)
    assert build(root)["changed"] == []


def test_changed_finding_stops_the_update(tmp_path):
    root = copy_repo(tmp_path)
    p = root / "results" / "phase-b" / "summary.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["validation"][0]["difference_share"] = 0.01
    p.write_text(json.dumps(s), encoding="utf-8")
    before = (root / "docs" / "index.html").read_text(encoding="utf-8")
    with pytest.raises(SiteError) as exc:
        build(root)
    assert any("ELSTAT" in x for x in exc.value.problems)
    assert (root / "docs" / "index.html").read_text(encoding="utf-8") == before


def test_changed_verdict_rewrites_the_finding(tmp_path):
    root = copy_repo(tmp_path)
    p = root / "results" / "thriving" / "summary.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    for c in s["comparisons"]:
        if c["a"] == "Flooded, Larisa":
            c["verdict"] = "not robust"
    p.write_text(json.dumps(s), encoding="utf-8")
    build(root)
    text = (root / "README.md").read_text(encoding="utf-8")
    assert "Larisa's shortfall against Karditsa and Trikala" in text
    assert "not firm under every map and control area" in text
    assert "Larisa fared worse" not in text


def test_block_resampling_changes_the_phase_b_text(tmp_path):
    root = copy_repo(tmp_path)
    p = root / "results" / "phase-b" / "summary.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["block_km"] = 10.0
    for e in s["extents"]:
        e["intervals"]["EL612"] = [0.7, 1.14]
    s["direction_by_unit"]["EL612"] = "not robust"
    p.write_text(json.dumps(s), encoding="utf-8")
    build(root)
    text = (root / "README.md").read_text(encoding="utf-8")
    assert "blocks of 10 by 10 km, because neighbouring squares" in text
    assert "In Larisa the ratio is below 1" in text and "not firm enough to report" in text
    assert "treat every square as if it were independent" not in text


def test_new_numbers_reach_the_page(tmp_path):
    root = copy_repo(tmp_path)
    p = root / "results" / "phase-a" / "sources.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["openfema_records"] = 70001
    p.write_text(json.dumps(s), encoding="utf-8")
    out = build(root)
    assert "README.md" in out["changed"]
    assert '<span data-v="a_records">70,001</span>' in (root / "README.md").read_text(encoding="utf-8")


def test_unknown_marker_is_reported(tmp_path):
    root = copy_repo(tmp_path)
    p = root / "README.md"
    p.write_text(p.read_text(encoding="utf-8") + '\n<span data-v="nothing_like_this">1</span>\n', encoding="utf-8")
    with pytest.raises(SiteError) as exc:
        build(root)
    assert any("nothing_like_this" in x for x in exc.value.problems)


def test_phase_c_stops_the_update_if_the_replication_fails(tmp_path):
    root = copy_repo(tmp_path)
    p = root / "results" / "phase-c" / "summary.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["replicated"] = False
    s["coefficient_check"][0]["difference"] = 0.02
    p.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(SiteError) as exc:
        build(root)
    assert any("no longer replicated" in x for x in exc.value.problems)
    assert any("second decimal" in x for x in exc.value.problems)


def test_phase_c_stops_if_nights_become_a_finding(tmp_path):
    root = copy_repo(tmp_path)
    p = root / "results" / "phase-c" / "summary.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["tourism"]["verdict"]["FOR"] = "lower after a fire"
    p.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(SiteError) as exc:
        build(root)
    assert any("not robust" in x for x in exc.value.problems)
