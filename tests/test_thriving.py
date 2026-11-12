import json
from datetime import date, timedelta

import numpy as np
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import box

from thrive.data.thriving import dekad_of, dekad_start, dekads_between, direction, overview_level, run

X0, Y0 = 5000000, 2000000
OLD = {0, 1, 2}
YOUNG = {3, 4, 5}
CONTROL = {6, 7, 8, 9}
LAKE = 10
FEWER_BACK = date(2024, 3, 1)
MORE_BACK = date(2024, 6, 1)


def cells_file(tmp_path):
    geoms, rows = [], []
    for i in range(6):
        geoms.append(box(X0 + 1000 * i, Y0, X0 + 1000 * (i + 1), Y0 + 1000))
        rows.append({"region_id": "EL611", "region_name": "Unit A", "population": 100.0, "older": 50.0 if i in OLD else 10.0, "older_known": True, "land_km2": 1.0, "flooded_share_all": 1.0, "flooded_share_water": 0.0 if i == 2 else 1.0})
    for i in range(4):
        geoms.append(box(X0 + 1000 * i, Y0 + 3000, X0 + 1000 * (i + 1), Y0 + 4000))
        rows.append({"region_id": "EL611", "region_name": "Unit A", "population": 20.0, "older": 5.0, "older_known": True, "land_km2": 1.0, "flooded_share_all": 0.0, "flooded_share_water": 0.0})
    geoms.append(box(X0 + 6000, Y0, X0 + 7000, Y0 + 1000))
    rows.append({"region_id": "EL611", "region_name": "Unit A", "population": 0.0, "older": 0.0, "older_known": True, "land_km2": 1.0, "flooded_share_all": 1.0, "flooded_share_water": 1.0})
    path = tmp_path / "cells.gpkg"
    gpd.GeoDataFrame(rows, geometry=geoms, crs=3035).to_file(path, layer="cells", driver="GPKG")
    return path


def config(tmp_path, persistence=1):
    p = tmp_path / "thriving.toml"
    p.write_text(f'''[stac]
url = "https://example.test/stac"
collection = "test"
max_cloud = 80
min_items_per_year = 20
max_failed_share = 0.1
workers = 2

[stac.assets]
red = "red"
nir = "nir"
scl = "scl"

[periods]
flood_date = "2023-09-07"
baseline = ["2021-01-01", "2022-12-31"]
after = ["2023-09-11", "2024-12-31"]

[pixels]
resolution_m = 100
valid_classes = [4, 5, 6]
guard_classes = [4, 5]
min_valid_share = 0.7
min_cell_in_scene = 0.9
default_scale = 0.0001
default_offset = -0.1
max_negative_share = 0.05

[cells]
path = "{cells_file(tmp_path).as_posix()}"
layer = "cells"

[groups]
flooded_share_min = 0.5
min_cells = 2
min_residents = 10
control_ring_m = [1000, 5000]
control_rings = [[1000, 5000], [1500, 6000]]

[recovery]
alphas = [0.8, 0.9]
persistence = {persistence}
max_gap = 3
min_coverage = 0.3
baseline_window = 1
min_baseline_ndvi = 0.3
min_cell_ndvi = 0.15
recovery_start = "2024-03-01"

[uncertainty]
replicates = 200
seed = 1

[seasons]
min_periods = 3
tolerance = 0.03
compare = ["Spring 2024", "Summer 2024"]

[[seasons.list]]
name = "Spring 2024"
start = "2024-03-01"
end = "2024-05-31"

[[seasons.list]]
name = "Summer 2024"
start = "2024-06-01"
end = "2024-08-31"

[[comparisons]]
a = "Flooded, more older residents"
b = "Flooded, fewer older residents"

[[comparisons]]
a = "Flooded, Larisa"
b = "Flooded, Karditsa, Trikala"

[[definitions]]
key = "all"
name = "All"

[[definitions]]
key = "water"
name = "Water"
''', encoding="utf-8")
    return p


def scene_dates(a, b):
    out, d = [], date.fromisoformat(a)
    while d <= date.fromisoformat(b):
        if d.day in (1, 11, 21):
            out.append(d)
        d += timedelta(days=1)
    return out


def item(d, kind="ok"):
    return {"id": f"S2_{d.isoformat()}_{kind}", "datetime": f"{d.isoformat()}T09:30:00Z", "cloud": 10.0, "baseline": "05.00", "kind": kind,
            "bounds_3035": (X0 - 500, Y0 - 500, X0 + 7000, Y0 + 5000),
            "assets": {r: {"href": f"mem://{r}", "scale": 0.0001, "offset": -0.1} for r in ("red", "nir", "scl")}}


def searcher(a, b):
    items = [item(d) for d in scene_dates(a, b)]
    if a.startswith("2023"):
        items.append(item(date(2024, 2, 2), "cloud"))
        items.append(item(date(2024, 2, 3), "nooffset"))
    return items


def normal(d):
    return 0.2 if d.month in (10, 11, 12, 1) else 0.6


def ndvi_for(cell, d):
    if cell == LAKE:
        return -0.2
    if d.year < 2023 or cell in CONTROL:
        return normal(d)
    if cell in YOUNG:
        return normal(d) if d >= FEWER_BACK else 0.18
    return normal(d) if d >= MORE_BACK else 0.18


def reader(it, grid, window):
    r0, r1, c0, c1 = window
    idx = grid.pixel_cell[r0:r1, c0:c1]
    d = date.fromisoformat(it["datetime"][:10])
    red_refl = np.full(idx.shape, 0.05)
    v = np.vectorize(lambda c: ndvi_for(int(c), d) if c >= 0 else 0.0)(idx)
    nir_refl = red_refl * (1 + v) / (1 - v)
    off = 0.0 if it["kind"] == "nooffset" else 0.1
    red = np.round((red_refl + off) / 0.0001).astype(np.uint16)
    nir = np.round((nir_refl + off) / 0.0001).astype(np.uint16)
    scl = np.full(idx.shape, 9 if it["kind"] == "cloud" else 4, dtype=np.uint16)
    return {"red": red, "nir": nir, "scl": scl}


def test_dekads():
    assert dekad_of(date(2024, 3, 1)) == (2024, 6)
    assert dekad_of(date(2024, 3, 31)) == (2024, 8)
    assert dekad_start(2024, 7) == date(2024, 3, 11)
    assert len(dekads_between(date(2023, 9, 11), date(2023, 12, 31))) == 11


def test_direction():
    assert direction([92, 30]) == "slower where more older people live"
    assert direction([-5, -1]) == "faster where more older people live"
    assert direction([5, 0]) == "not robust"
    assert direction([None]) == "no data"


def test_recovery_dates_are_exact(tmp_path):
    out = tmp_path / "out"
    s = run(config(tmp_path), out, searcher=searcher, reader=reader)
    assert s["control_cells"] == 4
    assert s["items_excluded"] == 1
    d = {x["key"]: x for x in s["definitions"]}
    a = d["all"]["groups"]
    assert a["Flooded, fewer older residents"]["recovered"]["0.8"] == "2024-03-01"
    assert a["Flooded, more older residents"]["recovered"]["0.9"] == "2024-06-01"
    assert a["Flooded, fewer older residents"]["days"]["0.8"] == (FEWER_BACK - date(2023, 9, 7)).days
    assert a["Flooded, more older residents"]["lowest_ratio"] == pytest.approx(0.3, abs=1e-3)
    assert a["All flooded cells"]["recovered"]["0.9"] == "2024-06-01"
    assert a["Flooded, more older residents"]["cells"] == 3
    assert d["all"]["older_gap_days"] == {"0.8": 92, "0.9": 92}
    assert d["all"]["stable"] is True
    assert a["All flooded cells"]["cells"] == 6
    assert a["All flooded cells"]["cells_left_out_not_green"] == 1
    w = d["water"]["groups"]
    assert w["All flooded cells"]["cells"] == 5
    assert s["direction"] == "slower where more older people live"
    assert a["Flooded, fewer older residents"]["seasons"]["Spring 2024"] == pytest.approx(1.0, abs=2e-3)
    assert a["Flooded, more older residents"]["seasons"]["Spring 2024"] == pytest.approx(0.3, abs=2e-3)
    assert a["Flooded, more older residents"]["seasons"]["Summer 2024"] == pytest.approx(1.0, abs=2e-3)
    cmp_ = {(c["a"], c["season"]): c for c in s["comparisons"]}
    assert cmp_[("Flooded, more older residents", "Spring 2024")]["verdict"] == "lower"
    assert cmp_[("Flooded, more older residents", "Spring 2024")]["differences"] == [pytest.approx(-0.7, abs=2e-3), pytest.approx(-0.7, abs=2e-3)]
    assert cmp_[("Flooded, more older residents", "Summer 2024")]["verdict"] == "no difference shown"
    assert cmp_[("Flooded, more older residents", "Summer 2024")]["verdict_point"] == "no clear difference"
    assert len(cmp_[("Flooded, more older residents", "Spring 2024")]["detail"]) == 4
    assert s["control_rings"][0]["ring"] == "1 to 5 km" and len(s["control_rings"]) == 2
    assert cmp_[("Flooded, Larisa", "Summer 2024")]["verdict"] == "no data"
    inv = json.loads((out / "items.json").read_text())
    assert any(i["excluded_offset_check"] for i in inv)
    for name in ("report.md", "thriving.xlsx", "summary.json", "sources.json", "preflight.json", "items.json"):
        assert (out / name).is_file(), name
    assert "slower where more older people live" in (out / "report.md").read_text()


def test_persistence_moves_nothing_when_recovery_is_permanent(tmp_path):
    s = run(config(tmp_path, persistence=3), tmp_path / "out", searcher=searcher, reader=reader)
    g = {x["key"]: x for x in s["definitions"]}["all"]["groups"]
    assert g["Flooded, fewer older residents"]["recovered"]["0.8"] == "2024-03-01"


def test_preflight_stops_without_scenes(tmp_path):
    with pytest.raises(RuntimeError, match="preflight failed"):
        run(config(tmp_path), tmp_path / "out", searcher=lambda a, b: [], reader=reader)
    checks = json.loads((tmp_path / "out" / "preflight.json").read_text())
    assert [c["ok"] for c in checks] == [False, False]


def test_overview_level():
    assert overview_level(10, [2, 4, 8, 16], 40) == 1
    assert overview_level(20, [2, 4, 8], 40) == 0
    assert overview_level(10, [2, 4], 15) is None
    assert overview_level(60, [2, 4], 40) is None


def test_read_item_from_tiled_tiffs_with_overviews(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from pyproj import Transformer
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin

    from thrive.data.thriving import item_bounds_3035, make_grid, read_item

    cells = gpd.read_file(cells_file(tmp_path), layer="cells")
    grid = make_grid(cells, 40)
    to_utm = Transformer.from_crs(3035, 32634, always_xy=True)
    xs, ys = to_utm.transform([X0 - 3000, X0 + 9000], [Y0 - 3000, Y0 + 7000])
    hrefs = {}
    for role, value, res in (("red", 1500, 10), ("nir", 5500, 10), ("scl", 4, 20)):
        w, h = int((max(xs) - min(xs)) // res), int((max(ys) - min(ys)) // res)
        path = tmp_path / f"{role}.tif"
        with rasterio.open(path, "w", driver="GTiff", width=w, height=h, count=1, dtype="uint16", crs="EPSG:32634", transform=from_origin(min(xs), max(ys), res, res), nodata=0, tiled=True, blockxsize=256, blockysize=256) as dst:
            dst.write(np.full((1, h, w), value, dtype=np.uint16))
            dst.build_overviews([2, 4], Resampling.average)
        hrefs[role] = str(path)
    to_ll = Transformer.from_crs(32634, 4326, always_xy=True)
    lon, lat = to_ll.transform([min(xs), max(xs)], [min(ys), max(ys)])
    it = {"id": "x", "bbox": [min(lon), min(lat), max(lon), max(lat)], "assets": {r: {"href": h} for r, h in hrefs.items()}}
    win = grid.window_for(item_bounds_3035(it))
    assert win == (0, grid.height, 0, grid.width)
    bands = read_item(it, grid, win)
    inside = grid.pixel_cell >= 0
    assert (bands["red"][inside] == 1500).all()
    assert (bands["nir"][inside] == 5500).all()
    assert (bands["scl"][inside] == 4).all()


def test_bare_season_does_not_count_as_recovery(tmp_path):
    from thrive.data.thriving import group_series

    s = run(config(tmp_path), tmp_path / "out", searcher=searcher, reader=reader)
    g = {x["key"]: x for x in s["definitions"]}["all"]["groups"]
    assert g["Flooded, fewer older residents"]["recovered"]["0.8"] == "2024-03-01"
    assert g["Flooded, more older residents"]["recovered"]["0.8"] == "2024-06-01"
    import pandas as pd
    dek = pd.DataFrame({"cell": [1, 1], "year": [2023, 2023], "k": [27, 28], "ndvi": [0.18, 0.18]})
    base = pd.Series([0.2, 0.6], index=pd.MultiIndex.from_tuples([(1, 27), (1, 28)], names=["cell", "k"]))
    out = group_series(dek, base, [1], [(2023, 27), (2023, 28)], 0.3, 0.3)
    assert np.isnan(out["ratio"].iloc[0])
    assert out["ratio"].iloc[1] == pytest.approx(0.3)


def test_a_thin_year_stops_the_run(tmp_path):
    def thin(a, b):
        items = searcher(a, b)
        return [i for i in items if not i["datetime"].startswith("2022")] if a.startswith("2021") else items

    with pytest.raises(RuntimeError, match="too few scenes in 2022"):
        run(config(tmp_path), tmp_path / "out", searcher=thin, reader=reader)


def test_compare_rule():
    from thrive.data.thriving import compare

    assert compare([-0.08, -0.05, -0.04], 0.03) == "lower"
    assert compare([0.05, 0.04], 0.03) == "higher"
    assert compare([0.01, -0.02, 0.0], 0.03) == "no clear difference"
    assert compare([0.05, 0.01], 0.03) == "not robust"
    assert compare([0.05, None], 0.03) == "no data"


def test_weeds_right_after_the_flood_do_not_count_as_recovery(tmp_path):
    def weedy(cell, d):
        if cell in OLD | YOUNG and date(2023, 9, 21) <= d < date(2023, 12, 1):
            return 0.7
        return ndvi_for(cell, d)

    def rdr(it, grid, window):
        r0, r1, c0, c1 = window
        idx = grid.pixel_cell[r0:r1, c0:c1]
        d = date.fromisoformat(it["datetime"][:10])
        v = np.vectorize(lambda c: weedy(int(c), d) if c >= 0 else 0.0)(idx)
        red_refl = np.full(idx.shape, 0.05)
        nir_refl = red_refl * (1 + v) / (1 - v)
        off = 0.0 if it["kind"] == "nooffset" else 0.1
        scl = np.full(idx.shape, 9 if it["kind"] == "cloud" else 4, dtype=np.uint16)
        return {"red": np.round((red_refl + off) / 0.0001).astype(np.uint16), "nir": np.round((nir_refl + off) / 0.0001).astype(np.uint16), "scl": scl}

    s = run(config(tmp_path), tmp_path / "out", searcher=searcher, reader=rdr)
    g = {x["key"]: x for x in s["definitions"]}["all"]["groups"]
    assert g["Flooded, fewer older residents"]["recovered"]["0.8"] == "2024-03-01"
    assert g["Flooded, more older residents"]["recovered"]["0.9"] == "2024-06-01"


def test_verdict_rule():
    from thrive.data.thriving import verdict

    assert verdict([-0.08, -0.05], [[-0.1, -0.06], [-0.07, -0.02]], 0.03) == "lower"
    assert verdict([-0.08, -0.05], [[-0.1, 0.01], [-0.07, -0.02]], 0.03) == "not robust"
    assert verdict([0.01, -0.02], [[-0.03, 0.04], [-0.05, 0.02]], 0.03) == "no difference shown"
    assert verdict([0.05, 0.04], [[0.02, 0.08], [0.01, 0.07]], 0.03) == "higher"
    assert verdict([0.05, None], [[0.02, 0.08], None], 0.03) == "no data"


def test_matrix_ratio_matches_the_series_and_intervals_cover_the_point():
    import pandas as pd
    from thrive.data.thriving import group_series, interval, matrices, point_ratio, poisson_weights, replicate_ratio

    rng = np.random.default_rng(3)
    post = [(2024, k) for k in range(6, 15)]
    rows = [{"cell": c, "year": y, "k": k, "ndvi": float(rng.uniform(0.2, 0.8))} for c in range(40) for (y, k) in post if rng.random() > 0.2]
    dek = pd.DataFrame(rows)
    base = pd.Series([float(rng.uniform(0.3, 0.8)) for c in range(40) for k in range(36)], index=pd.MultiIndex.from_product([range(40), range(36)], names=["cell", "k"]))
    old = group_series(dek, base, list(range(40)), post, 0.3, 0.3)["ratio"].to_numpy()
    P, B = matrices(dek, base, list(range(40)), post)
    new, valid = point_ratio(P, B, 0.3, 0.3)
    assert np.allclose(old, new, equal_nan=True)
    rep = replicate_ratio(P, valid, B, poisson_weights(np.random.default_rng(1), 500, 40))
    for t in range(len(post)):
        lo, hi = interval(rep[:, t])
        assert lo <= new[t] <= hi
