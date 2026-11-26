from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from thrive.data import crops_probe as cp

INDEX = """<html><body><table>
<tr><th><a href="?C=N;O=D">Name</a></th></tr>
<tr><td><a href="/data/">Parent Directory</a></td><td>-</td></tr>
<tr><td><a href="ver3-0-2/">ver3-0-2/</a></td><td>2026-01-26 11:48</td><td>-</td></tr>
<tr><td><a href="smian_m_euu_20240721_t.tif">smian_m_euu_20240721_t.tif</a></td><td>2024-07-22 10:00</td><td>3.2M</td></tr>
<tr><td><a href="README.txt">README.txt</a></td><td>2026-01-26 11:48</td><td>804</td></tr>
</table></body></html>"""

BASE = "https://example.org/data/EDO_X/"


def test_parse_index_keeps_children_and_sizes():
    rows = cp.parse_index(INDEX, BASE)
    names = {r["name"]: r for r in rows}
    assert set(names) == {"ver3-0-2", "smian_m_euu_20240721_t.tif", "README.txt"}
    assert names["ver3-0-2"]["is_dir"] is True
    assert names["smian_m_euu_20240721_t.tif"]["size_bytes"] == int(3.2 * 1024 ** 2)
    assert names["README.txt"]["size_bytes"] == 804


def test_crawl_descends_into_folders():
    pages = {
        BASE: INDEX.encode(),
        BASE + "ver3-0-2/": b'<a href="smian_2023.nc">smian_2023.nc</a> 2026-01-26 10:00 1.1G',
    }
    files = cp.crawl(BASE, lambda u: pages[u], max_depth=2)
    paths = sorted(f["path"] for f in files)
    assert paths == ["README.txt", "smian_m_euu_20240721_t.tif", "ver3-0-2/smian_2023.nc"]


def test_dates_in_prefers_full_dates():
    assert cp.dates_in("smian_m_euu_20240721_t.tif")[0] == ("ymd", date(2024, 7, 21))
    assert cp.dates_in("wsdi_2023-08.tif")[0] == ("ym", date(2023, 8, 1))
    assert cp.dates_in("smian_2023.nc")[0] == ("y", date(2023, 1, 1))
    assert cp.dates_in("README.txt") == []


def test_years_covered_and_sample_choice():
    files = [
        {"name": "a_20230711.tif", "path": "a_20230711.tif", "size_bytes": 10},
        {"name": "a_20240721.tif", "path": "a_20240721.tif", "size_bytes": 10},
        {"name": "a_2024.nc", "path": "a_2024.nc", "size_bytes": 10},
        {"name": "a_20240721.zip", "path": "a_20240721.zip", "size_bytes": 10 ** 12},
    ]
    counts = cp.years_covered(files, 2023, 2025)
    assert counts == {2023: 1, 2024: 3, 2025: 0}
    pick = cp.pick_sample(files, date(2024, 7, 21), max_bytes=10 ** 6)
    assert pick["name"] == "a_20240721.tif"


def test_window_stats_ignores_nodata_and_nan():
    arr = np.array([[1.0, 2.0], [np.nan, -9999.0]])
    s = cp.window_stats(arr, -9999.0)
    assert s["pixels"] == 4 and s["valid_share"] == 0.5
    assert s["min"] == 1.0 and s["max"] == 2.0 and s["mean"] == 1.5


def test_compare_flags_cotton_within_tolerance():
    cfg = cp.load_config(Path("config/crops-probe.toml"))
    classes = pd.DataFrame({"class": [230, 216], "name": ["x", "y"], "hectares": [70000.0, 10000.0]})
    crops = pd.DataFrame({
        "crops": ["I5000", "C1500"],
        "time": ["2022", "2022"],
        "label": ["Cotton fibre", "Grain maize and corn-cob-mix"],
        "thousand_ha": [80.0, 30.0],
    })
    out = cp.compare(classes, crops, cfg).set_index("crop")
    assert bool(out.loc["Cotton", "within_tolerance"]) is True
    assert bool(out.loc["Maize", "within_tolerance"]) is False


def test_config_lists_the_needed_indicators():
    cfg = cp.load_config(Path("config/crops-probe.toml"))
    keys = {i["key"] for i in cfg["edo"]["indicator"]}
    assert set(cfg["edo"]["needed"]) <= keys
