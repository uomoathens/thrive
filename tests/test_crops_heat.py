import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from thrive.data.crops_heat import add_lag, band_dates, block_counts, crop_hectares, dekad_heat, estimate, pick_year_file, sample_cells, verdict


def test_block_counts():
    arr = np.zeros((4, 6), dtype=np.uint16)
    arr[0:2, 0:2] = 230
    arr[2, 5] = 216
    out = block_counts(arr, 2, [230, 216])
    assert out[230].tolist() == [[4, 0, 0], [0, 0, 0]]
    assert out[216].tolist() == [[0, 0, 0], [0, 0, 1]]


def test_pick_year_file():
    files = [
        {"name": "tmaxm_m_edo_20240101_20241231_d.nc", "path": "ver2-0-0/tmaxm_m_edo_20240101_20241231_d.nc"},
        {"name": "tmaxm_m_edo_20240101_20241231_d.nc", "path": "ver2-1-0/tmaxm_m_edo_20240101_20241231_d.nc"},
        {"name": "tmaxm_m_edo_20240101_20241231_d.zip", "path": "ver2-1-0/tmaxm_m_edo_20240101_20241231_d.zip"},
        {"name": "tmaxm_m_edo_20230101_20231231_d.nc", "path": "ver2-1-0/tmaxm_m_edo_20230101_20231231_d.nc"},
    ]
    assert pick_year_file(files, 2024)["path"] == "ver2-1-0/tmaxm_m_edo_20240101_20241231_d.nc"
    assert pick_year_file(files, 2022) is None


def test_band_dates():
    tags = {"NETCDF_DIM_time_VALUES": "{19723,19724,19725}", "time#units": "days since 1970-01-01"}
    assert band_dates(tags, 3) == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    with pytest.raises(ValueError):
        band_dates(tags, 4)
    with pytest.raises(ValueError):
        band_dates({}, 3)


def test_dekad_heat_counts_and_gaps():
    dates = [date(2024, 7, 1) + timedelta(days=i) for i in range(10)]
    tmax = np.array([[30, 36, 38, 41, 35, 34, 33, 37, 39, 40], [np.nan] * 5 + [40] * 5], dtype=float)
    out = dekad_heat(dates, tmax, [35, 37, 40])
    a = out[out["cell"] == 0].iloc[0]
    assert (a["hot35"], a["hot37"], a["hot40"], a["days"]) == (7, 5, 2, 10)
    assert a["tmax_mean"] == pytest.approx(np.mean([30, 36, 38, 41, 35, 34, 33, 37, 39, 40]))
    b = out[out["cell"] == 1].iloc[0]
    assert b["days"] == 5 and np.isnan(b["hot35"])


def test_add_lag():
    df = pd.DataFrame({"cell": [0, 0, 0], "year": [2024] * 3, "k": [18, 19, 21], "hot37": [2.0, 3.0, 1.0]})
    out = add_lag(df, ["hot37"]).sort_values("k")
    assert out["hot37_two"].tolist()[1] == 5.0
    assert np.isnan(out["hot37_two"].tolist()[0]) and np.isnan(out["hot37_two"].tolist()[2])


def synthetic_panel(beta, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(120):
        level = rng.normal(0, 0.3)
        for y in range(2019, 2026):
            shock = rng.normal(0, 0.05)
            for k in range(15, 27):
                hot = float(rng.poisson(2 + (k - 15) % 4))
                sma = rng.normal()
                rows.append({"cell": c, "year": y, "k": k, "block": c // 6, "hot": hot, "sma": sma, "y": level + 0.02 * k + shock + beta * hot + 0.01 * sma + rng.normal(0, 0.02)})
    return pd.DataFrame(rows)


def test_estimate_recovers_effect():
    r = estimate(synthetic_panel(-0.01), "hot", "year", "sma")
    assert r["b"] == pytest.approx(-0.01, abs=0.002)
    assert r["hi"] < 0
    r0 = estimate(synthetic_panel(0.0, seed=3), "hot", "yeark", "sma")
    assert r0["lo"] <= 0 <= r0["hi"]


def test_verdict():
    neg = {"b": -0.01, "lo": -0.02, "hi": -0.001}
    zero = {"b": 0.0, "lo": -0.01, "hi": 0.01}
    pos = {"b": 0.01, "lo": 0.001, "hi": 0.02}
    assert verdict([neg, neg]) == "lower greenness after hot days"
    assert verdict([pos, pos]) == "higher greenness after hot days"
    assert verdict([zero, zero]) == "no effect shown"
    assert verdict([neg, zero]) == "not robust"
    assert verdict([neg, {"b": None}]) == "no data"


def test_crop_hectares_and_sample(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    gpd = pytest.importorskip("geopandas")
    from rasterio.transform import from_origin
    from shapely.geometry import box

    x0, y1 = 5_300_000.0, 2_000_000.0
    arr = np.zeros((200, 300), dtype=np.uint16)
    arr[0:100, 0:100] = 230
    arr[100:150, 100:200] = 216
    tif = tmp_path / "map.tif"
    with rasterio.open(tif, "w", driver="GTiff", width=300, height=200, count=1, dtype="uint16", crs="EPSG:3035", transform=from_origin(x0, y1, 10, 10)) as ds:
        ds.write(arr, 1)
    cells = gpd.GeoDataFrame({"cell_id": [1, 2, 3]}, geometry=[box(x0, y1 - 1000, x0 + 1000, y1), box(x0 + 1000, y1 - 2000, x0 + 2000, y1 - 1000), box(x0 + 2000, y1 - 1000, x0 + 3000, y1)], crs=3035)
    ha = crop_hectares(cells, str(tif), {"cotton": 230, "maize": 216}, strip_km=1)
    assert ha["cotton"].tolist() == [100.0, 0.0, 0.0]
    assert ha["maize"].tolist() == [0.0, 50.0, 0.0]

    nc = tmp_path / "tmax.tif"
    data = np.stack([np.full((3, 3), 30.0 + b, dtype="float32") for b in range(3)])
    data[:, 0, 0] = -9999
    with rasterio.open(nc, "w", driver="GTiff", width=3, height=3, count=3, dtype="float32", crs="EPSG:3035", transform=from_origin(x0, y1, 1000, 1000), nodata=-9999) as ds:
        ds.write(data)
        ds.update_tags(NETCDF_DIM_time_VALUES="{19905,19906,19907}", **{"time#units": "days since 1970-01-01"})
    cx, cy = cells.geometry.centroid.x.to_numpy(), cells.geometry.centroid.y.to_numpy()
    dates, vals = sample_cells(nc, cx, cy, "EPSG:3035")
    assert dates[0] == date(2024, 7, 1)
    assert np.isnan(vals[0]).all()
    assert vals[1].tolist() == [30.0, 31.0, 32.0]


X0, Y1 = 5_300_000.0, 2_000_000.0
NX, NY = 12, 10
EDO = "https://edo.example/data/"


def tmax_value(cell, d):
    v = math.sin(cell * 12.9898 + d.toordinal() * 78.233) * 43758.5453
    return 33.0 + 9.0 * (v - math.floor(v))


def hot37(cell, d):
    from thrive.data.thriving import dekad_of

    y, k = dekad_of(d)
    start = date(y, k // 3 + 1, 1 + 10 * (k % 3))
    end = date(y + (k == 35), (k + 1) // 3 % 12 + 1, 1 + 10 * ((k + 1) % 3)) if k < 35 else date(y + 1, 1, 1)
    n, day = 0, start
    while day < end:
        n += tmax_value(cell, day) >= 37
        day += timedelta(days=1)
    return n


def write_inputs(tmp_path):
    import geopandas as gpd
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import box

    geoms, rows = [], []
    for r in range(NY):
        for c in range(NX):
            geoms.append(box(X0 + c * 1000, Y1 - (r + 1) * 1000, X0 + (c + 1) * 1000, Y1 - r * 1000))
            i = r * NX + c
            rows.append({"cell_id": i, "region_id": "EL611" if c < 6 else "EL612", "region_name": "Karditsa" if c < 6 else "Larisa", "flooded_share_observed_all": 0.5 if i < 10 else 0.0})
    cells = gpd.GeoDataFrame(rows, geometry=geoms, crs=3035)
    (tmp_path / "phase-b").mkdir()
    cells.to_file(tmp_path / "phase-b" / "cells.gpkg", layer="cells", driver="GPKG")
    crop = np.zeros((NY * 100, NX * 100), dtype=np.uint16)
    for r in range(NY):
        for c in range(NX):
            crop[r * 100 : r * 100 + 80, c * 100 : (c + 1) * 100] = 230 if (r + c) % 2 else 216
    with rasterio.open(tmp_path / "map.tif", "w", driver="GTiff", width=NX * 100, height=NY * 100, count=1, dtype="uint16", crs="EPSG:3035", transform=from_origin(X0, Y1, 10, 10)) as ds:
        ds.write(crop, 1)
    files = {}
    for y in (2019, 2020):
        days = [date(y, 1, 1) + timedelta(days=i) for i in range((date(y + 1, 1, 1) - date(y, 1, 1)).days)]
        cube = np.zeros((len(days), NY, NX), dtype="float32")
        for b, d in enumerate(days):
            for r in range(NY):
                for c in range(NX):
                    cube[b, r, c] = tmax_value(r * NX + c, d)
        name = f"tmaxm_m_edo_{y}0101_{y}1231_d.nc"
        with rasterio.open(tmp_path / name, "w", driver="GTiff", width=NX, height=NY, count=len(days), dtype="float32", crs="EPSG:3035", transform=from_origin(X0, Y1, 1000, 1000)) as ds:
            ds.write(cube)
            ds.update_tags(NETCDF_DIM_time_VALUES="{" + ",".join(str((d - date(1970, 1, 1)).days) for d in days) + "}", **{"time#units": "days since 1970-01-01"})
        files[name] = tmp_path / name
        dek = [date(y, m, dd) for m in range(1, 13) for dd in (1, 11, 21)]
        rng = np.random.default_rng(y)
        sm = rng.normal(0, 1, (36, NY, NX)).astype("float32")
        name = f"smian_m_eul_{y}0101_{y}1221_t.nc"
        with rasterio.open(tmp_path / name, "w", driver="GTiff", width=NX, height=NY, count=36, dtype="float32", crs="EPSG:3035", transform=from_origin(X0, Y1, 1000, 1000)) as ds:
            ds.write(sm)
            ds.update_tags(NETCDF_DIM_time_VALUES="{" + ",".join(str((d - date(1970, 1, 1)).days) for d in dek) + "}", **{"time#units": "days since 1970-01-01"})
        files[name] = tmp_path / name
    cfg = tmp_path / "crops-heat.toml"
    cfg.write_text(f'''years = [2019, 2020]
season = ["06-01", "09-30"]
block_m = 2000

[cells]
path = "{(tmp_path / 'phase-b' / 'cells.gpkg').as_posix()}"
layer = "cells"

[cropmap]
url = "{(tmp_path / 'map.tif').as_posix()}"
min_crop_ha = 50
min_cells = 50

[cropmap.classes]
cotton = 230
maize = 216

[edo]
base = "{EDO}"
tmax_dir = "TMAX"
sma_dir = "SMA"
max_depth = 1
thresholds = [35, 37, 40]

[flood]
column = "flooded_share_observed_all"
share = 0.1
until_year = 2024

[exposure]
threshold = 37
days = 10

[stac]
url = "mem://stac"
collection = "sentinel-2-c1-l2a"
max_cloud = 80
min_items_per_summer = 10
max_failed_share = 0.1
workers = 2

[stac.assets]
red = "red"
nir = "nir"
scl = "scl"

[pixels]
resolution_m = 100
valid_classes = [4, 5, 6]
guard_classes = [4, 5]
min_valid_share = 0.7
min_cell_in_scene = 0.9
default_scale = 0.0001
default_offset = -0.1
max_negative_share = 0.05
min_ndvi = 0.1
''', encoding="utf-8")
    return cfg, files


def fake_fetcher(files):
    def fetch(url):
        if url == EDO + "TMAX/":
            return b'<a href="v1/">v1/</a>'
        if url == EDO + "SMA/":
            return b'<a href="v1/">v1/</a>'
        if url in (EDO + "TMAX/v1/", EDO + "SMA/v1/"):
            kind = "tmaxm" if "TMAX" in url else "smian"
            return "".join(f'<a href="{n}">{n}</a>\n' for n in files if n.startswith(kind)).encode()
        raise AssertionError(url)

    return fetch


def scene_items(a, b):
    out, d = [], date.fromisoformat(a)
    while d <= date.fromisoformat(b):
        if d.day in (3, 8, 13, 18, 23, 28):
            out.append({"id": f"S2_{d.isoformat()}", "datetime": f"{d.isoformat()}T09:30:00Z", "cloud": 10.0, "baseline": "05.00",
                        "bounds_3035": (X0 - 500, Y1 - NY * 1000 - 500, X0 + NX * 1000 + 500, Y1 + 500),
                        "assets": {r: {"href": f"mem://{r}", "scale": 0.0001, "offset": -0.1} for r in ("red", "nir", "scl")}})
        d += timedelta(days=1)
    return out


def scene_reader(it, grid, window):
    r0, r1, c0, c1 = window
    idx = grid.pixel_cell[r0:r1, c0:c1]
    d = date.fromisoformat(it["datetime"][:10])
    cache = {}

    def ndvi(c):
        if c < 0:
            return 0.0
        if c not in cache:
            cache[c] = 0.6 * math.exp(-0.03 * hot37(int(c), d))
        return cache[c]

    v = np.vectorize(ndvi)(idx)
    red_refl = np.full(idx.shape, 0.05)
    nir_refl = red_refl * (1 + v) / (1 - v)
    red = np.round((red_refl + 0.1) / 0.0001).astype(np.uint16)
    nir = np.round((nir_refl + 0.1) / 0.0001).astype(np.uint16)
    return {"red": red, "nir": nir, "scl": np.full(idx.shape, 4, dtype=np.uint16)}


def test_run_end_to_end(tmp_path, monkeypatch):
    pytest.importorskip("geopandas")
    import shutil

    import thrive.data.crops_heat as ch

    cfg, files = write_inputs(tmp_path)

    def fake_to_file(url, path):
        shutil.copy(files[url.rsplit("/", 1)[1]], path)
        return "sha"

    monkeypatch.setattr(ch, "fetch_to_file", fake_to_file)
    monkeypatch.setattr(ch, "tif_header", lambda url: {"url": url, "crs": "EPSG:3035", "res": (10, 10), "bounds4326": (-180, -90, 180, 90)})
    out = tmp_path / "out"
    s = ch.run(cfg, out, searcher=scene_items, reader=scene_reader, fetcher=fake_fetcher(files))
    assert s["cells"] == NX * NY
    assert s["cotton_ha"] == pytest.approx(60 * 80)
    assert s["maize_ha"] == pytest.approx(60 * 80)
    assert len(s["specifications"]) == 12
    main = [r for r in s["specifications"] if r["threshold_C"] == 37 and r["hot_days_in"] == "this ten-day period"]
    for r in main:
        assert r["b"] == pytest.approx(-0.03, abs=0.004)
    assert s["verdict"] == "lower greenness after hot days"
    for name in ("report.md", "summary.json", "sources.json", "crops-heat.xlsx", "preflight.json", "items.json"):
        assert (out / name).exists()
    ex = pd.read_excel(out / "crops-heat.xlsx", sheet_name="exposure")
    assert set(ex["region_id"]) == {"EL611", "EL612"}
    assert (ex["cotton_ha_exposed"] <= ex["cotton_ha"]).all()
