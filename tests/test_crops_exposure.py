from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from thrive.data.crops_exposure import by_unit, longest_run, summer_heat


def test_longest_run():
    flags = np.array([[1, 1, 0, 1, 1, 1, 0], [0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 1]], dtype=bool)
    assert longest_run(flags).tolist() == [3, 0, 7]


def test_summer_heat_counts_only_the_season():
    days = [date(2024, 5, 30) + timedelta(days=i) for i in range(130)]
    t = np.full((2, len(days)), 30.0)
    for j, d in enumerate(days):
        if d == date(2024, 5, 31):
            t[:, j] = 45
        if date(2024, 7, 10) <= d <= date(2024, 7, 14):
            t[0, j] = 38
        if d == date(2024, 7, 20):
            t[0, j] = 41
    out = summer_heat(days, t, 2024, "06-01", "09-30", [35, 37, 40], 37, 0.9)
    a = out.iloc[0]
    assert (a["days_35"], a["days_37"], a["days_40"], a["longest_37"], a["tmax_max"]) == (6, 6, 1, 5, 41)
    assert out.iloc[1]["days_37"] == 0


def test_summer_heat_needs_the_whole_season():
    days = [date(2024, 6, 1) + timedelta(days=i) for i in range(60)]
    assert summer_heat(days, np.full((1, 60), 30.0), 2024, "06-01", "09-30", [37], 37, 0.9) is None


def test_summer_heat_marks_squares_with_gaps():
    days = [date(2024, 6, 1) + timedelta(days=i) for i in range(122)]
    t = np.full((1, 122), 39.0)
    t[0, :30] = np.nan
    out = summer_heat(days, t, 2024, "06-01", "09-30", [37], 37, 0.9)
    assert np.isnan(out.iloc[0]["days_37"])


def test_by_unit_adds_up_hectares():
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box

    cells = gpd.GeoDataFrame({"region_id": ["EL611", "EL611", "EL612"]}, geometry=[box(0, 0, 1, 1)] * 3, crs=3035)
    crops = pd.DataFrame({"cotton": [100.0, 50.0, 20.0], "maize": [0.0, 10.0, 5.0]}, index=[0, 1, 2])
    heat = pd.DataFrame({"cell": [0, 1, 2], "year": 2024, "days_37": [12, 4, 20], "days_40": [6, 0, 1]})
    t = by_unit(heat, crops, cells, 37, 10, 40, 5).set_index("Περιφερειακή Ενότητα")
    k = t.loc["Καρδίτσα και Τρίκαλα"]
    assert k["Βαμβάκι, εκτάρια"] == 150
    assert k["Βαμβάκι, εκτάρια με ≥10 ημέρες ≥37°C"] == 100
    assert k["Βαμβάκι, εκτάρια με ≥5 ημέρες ≥40°C"] == 100
    assert k["Βαμβάκι, μέσος αριθμός ημερών ≥37°C"] == pytest.approx((12 * 100 + 4 * 50) / 150, abs=0.05)
    assert t.loc["Λάρισα"]["Καλαμπόκι, εκτάρια με ≥10 ημέρες ≥37°C"] == 5


def test_run_end_to_end(tmp_path, monkeypatch):
    pytest.importorskip("geopandas")
    import shutil

    import thrive.data.crops_exposure as ce
    from tests.test_crops_heat import EDO, fake_fetcher, write_inputs

    _, files = write_inputs(tmp_path)
    cfg = tmp_path / "crops-exposure.toml"
    cfg.write_text(f'''years = [2019, 2021]
season = ["06-01", "09-30"]

[cells]
path = "{(tmp_path / 'phase-b' / 'cells.gpkg').as_posix()}"
layer = "cells"

[cropmap]
url = "{(tmp_path / 'map.tif').as_posix()}"

[cropmap.classes]
cotton = 230
maize = 216

[edo]
base = "{EDO}"
tmax_dir = "TMAX"
max_depth = 1
thresholds = [35, 37, 40]
min_valid_share = 0.9

[exposure]
threshold = 37
days = 10
extreme_threshold = 40
extreme_days = 5
''', encoding="utf-8")
    monkeypatch.setattr(ce, "fetch_to_file", lambda url, path: shutil.copy(files[url.rsplit("/", 1)[1]], path) and "sha")
    monkeypatch.setattr(ce, "tif_header", lambda url: {"url": url, "crs": "EPSG:3035", "res": (10, 10), "bounds4326": (-180, -90, 180, 90)})
    out = tmp_path / "out"
    s = ce.run(cfg, out, fetcher=fake_fetcher(files))
    assert s["years"] == [2019, 2020] and s["skipped"] == [2021]
    assert s["cotton_ha"] == pytest.approx(60 * 80) and s["maize_ha"] == pytest.approx(60 * 80)
    t = pd.read_excel(out / "crops-exposure.xlsx", sheet_name="Ανά Περιφερειακή Ενότητα")
    assert set(t["Περιφερειακή Ενότητα"]) == {"Καρδίτσα και Τρίκαλα", "Λάρισα"}
    assert (t["Βαμβάκι, εκτάρια με ≥10 ημέρες ≥37°C"] <= t["Βαμβάκι, εκτάρια"]).all()
    sq = pd.read_excel(out / "crops-exposure.xlsx", sheet_name="Ανά τετράγωνο")
    assert len(sq) == 120 and "Ημέρες ≥37°C, 2020" in sq.columns
    assert (out / "report.md").exists()
