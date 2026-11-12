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
    p = root / "results" / "thriving" / "summary.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    for c in s["comparisons"]:
        if c["a"] == "Flooded, Larisa":
            c["verdict"] = "not robust"
    p.write_text(json.dumps(s), encoding="utf-8")
    before = (root / "docs" / "index.html").read_text(encoding="utf-8")
    with pytest.raises(SiteError) as exc:
        build(root)
    assert any("Larisa" in x for x in exc.value.problems)
    assert (root / "docs" / "index.html").read_text(encoding="utf-8") == before


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
