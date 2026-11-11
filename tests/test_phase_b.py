import io
import json
import zipfile

import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, box

from thrive.data.phase_b import activation_products, flood_polygons, run

DETAIL = "https://example.test/cems/?code={code}"
CEMS = {"results": [{"code": "EMSR692", "name": "Flood in Greece", "aois": [
    {"number": 1, "name": "Larisa", "products": [
        {"type": "DEL", "downloadPath": "https://example.test/p1.zip", "feasible": True, "monitoringNumber": None},
        {"type": "DEL", "downloadPath": "https://example.test/p2.zip", "feasible": True, "monitoringNumber": 1},
        {"type": "REF", "downloadPath": "https://example.test/ref.zip", "feasible": True},
        {"type": "DEL", "downloadPath": None, "feasible": True},
        {"type": "GRA", "downloadPath": "https://example.test/no.zip", "feasible": False},
    ]},
]}]}


def geojson(geoms, **cols):
    return gpd.GeoDataFrame(cols, geometry=geoms, crs=3035).to_crs(4326).to_json().encode()


def product_zip(flood_geoms, maximum=None, both_formats=True, classes=None):
    buf = io.BytesIO()
    obs = geojson(flood_geoms, notation=classes or ["Flooded area"] * len(flood_geoms))
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("EMSR692_AOI01_DEL_PRODUCT_observedEventA_v1.json", obs)
        if both_formats:
            zf.writestr("EMSR692_AOI01_DEL_PRODUCT_observedEventA_v1.geojson", obs)
        if maximum:
            zf.writestr("EMSR692_AOI01_DEL_PRODUCT_maximumWaterExtentA_v1.json", geojson(maximum))
        zf.writestr("EMSR692_AOI01_DEL_PRODUCT_areaOfInterestA_v1.json", geojson([box(5240000, 1940000, 5270000, 1960000)]))
    return buf.getvalue()


def nuts():
    gdf = gpd.GeoDataFrame({
        "NUTS_ID": ["EL611", "EL612", "EL642", "EL521"],
        "NAME_LATN": ["Unit A", "Unit B", "Neighbour", "Far away"],
    }, geometry=[
        box(5250000, 1950000, 5253000, 1952000),
        box(5253000, 1950000, 5255000, 1951500),
        box(5255000, 1950000, 5257000, 1952000),
        box(5400000, 1950000, 5402000, 1952000),
    ], crs=3035)
    return gdf.to_crs(4326).to_json().encode()


def grid_frame(with_age=True):
    pts, pop, old = [], [], []
    for i in range(6):
        for j in range(2):
            pts.append(Point(5250500 + 1000 * i, 1950500 + 1000 * j))
            pop.append(100)
            old.append(float("nan") if (i, j) == (4, 1) else (50 if (i, j) == (3, 0) else 20))
    pts.append(Point(5250500, 1952500))
    pop.append(30)
    old.append(5)
    cols = {"T": pop}
    if with_age:
        cols["Y_GE65"] = old
    return gpd.GeoDataFrame(cols, geometry=pts, crs=3035)


@pytest.fixture
def grid_zip(tmp_path):
    g = tmp_path / "ESTAT_Census_2021_V2.gpkg"
    grid_frame().to_file(g, driver="GPKG", layer="census2021")
    z = tmp_path / "census.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(g, "Eurostat_Census-GRID_2021_V2.2/ESTAT_Census_2021_V2.gpkg")
        zf.writestr("Eurostat_Census-GRID_2021_V2.2/readme.txt", "x")
    return z


def make_config(tmp_path, older_required=True):
    p = tmp_path / f"phase-b-{older_required}.toml"
    p.write_text(f'''[cems]
activation = "EMSR692"
detail = "{DETAIL}"
product_types = ["DEL", "GRA"]
flood_layer_words = ["observedevent"]
check_layer_words = ["maximumwaterextent"]
class_columns = ["notation"]

[grid]
name = "test grid"
url = "https://example.test/census.zip"
population = ["T", "TOT_P_2021"]
older = ["Y_GE65"]
older_required = {"true" if older_required else "false"}
cell_size_m = 1000

[regions]
url = "https://example.test/nuts.geojson"
prefix = "EL61"

[analysis]
crs = 3035
min_exposed_for_ratio = 10

[[extent]]
key = "observed_all"
name = "All observed"
source = "observed"
exclude = []

[[extent]]
key = "observed_water"
name = "Water only"
source = "observed"
exclude = ["Flood trace"]

[[extent]]
key = "cems_maximum"
name = "Copernicus maximum"
source = "maximum"

[validation]
source = "test"

[validation.population]
EL611 = 600
EL612 = 380
''', encoding="utf-8")
    return p


def fetcher(p1, p2):
    def f(url):
        if url == DETAIL.format(code="EMSR692"):
            return json.dumps(CEMS).encode()
        if url == "https://example.test/p1.zip":
            return p1
        if url == "https://example.test/p2.zip":
            return p2
        if url == "https://example.test/nuts.geojson":
            return nuts()
        raise AssertionError(url)
    return f


P1 = [box(5250000, 1950000, 5251000, 1951000)]
P2 = [box(5253000, 1950000, 5253500, 1951000), box(5254000, 1951000, 5255000, 1952000), box(5255000, 1950000, 5256000, 1951000)]
MAX1 = [box(5250000, 1950000, 5252000, 1951000)]
C2 = ["Flooded area", "Flood trace", "Flooded area"]


def test_products_keep_only_downloadable_flood_types():
    act, products = activation_products(DETAIL, "EMSR692", ["DEL", "GRA"], fetcher(b"", b""))
    assert act["code"] == "EMSR692"
    assert [p["url"] for p in products] == ["https://example.test/p1.zip", "https://example.test/p2.zip"]


def test_unknown_activation():
    with pytest.raises(ValueError):
        activation_products(DETAIL, "EMSR000", ["DEL"], lambda url: json.dumps({"results": []}).encode())


def test_each_layer_is_read_once_and_classes_recorded():
    found, layers, details, check = flood_polygons(product_zip(P1, MAX1), ["observedevent"], 3035, ["maximumwaterextent"])
    assert len(found) == 1
    assert len(layers) == 3
    assert details[0]["classes"]["notation"] == {"Flooded area": 1}
    assert len(check) == 1


def test_exposure_numbers(tmp_path, grid_zip):
    out = tmp_path / "out"
    s = run(make_config(tmp_path), out, fetcher(product_zip(P1, MAX1), product_zip(P2, classes=C2)), grid_path=grid_zip)
    reg = {r["region_id"]: r for r in s["regions"]}
    assert set(reg) == {"EL611", "EL612"}
    a, b = reg["EL611"], reg["EL612"]
    assert a["population"] == pytest.approx(600)
    assert b["population"] == pytest.approx(400)
    assert a["population_exposed"] == pytest.approx(100)
    assert b["population_exposed"] == pytest.approx(150)
    assert a["flooded_km2"] == pytest.approx(1.0)
    assert b["flooded_km2"] == pytest.approx(1.0)
    assert b["land_km2"] == pytest.approx(3.0)
    assert a["older"] == pytest.approx(120)
    assert b["older"] == pytest.approx(90)
    assert b["population_with_age"] == pytest.approx(300)
    assert b["older_exposed"] == pytest.approx(25)
    assert b["population_exposed_with_age"] == pytest.approx(50)
    assert s["population"] == pytest.approx(1000)
    assert s["population_exposed"] == pytest.approx(250)
    assert s["share_exposed"] == pytest.approx(0.25)
    assert s["flooded_km2"] == pytest.approx(2.0)
    assert s["age_coverage"] == pytest.approx(0.9)
    assert s["older_share_of_population"] == pytest.approx(210 / 900)
    assert s["older_share_of_exposed"] == pytest.approx(45 / 150)
    assert s["older_exposure_ratio"] == pytest.approx((45 / 150) / (210 / 900))
    assert s["checks"]["unplaced_population"] == pytest.approx(30)
    assert s["checks"]["unplaced_cells"] == 1
    assert s["checks"]["class_km2"]["Flooded area"] == pytest.approx(1.5)
    assert s["checks"]["class_km2"]["Flood trace"] == pytest.approx(0.5)
    e = {x["key"]: x for x in s["extents"]}
    assert set(e) == {"observed_all", "observed_water", "cems_maximum"}
    assert e["observed_water"]["population_exposed"] == pytest.approx(150)
    assert e["observed_water"]["flooded_km2"] == pytest.approx(1.5)
    assert e["observed_water"]["older_exposure_ratio"] == pytest.approx((45 / 150) / (210 / 900))
    assert e["cems_maximum"]["population_exposed"] == pytest.approx(200)
    assert e["cems_maximum"]["flooded_km2"] == pytest.approx(2.0)
    assert e["cems_maximum"]["older_exposure_ratio"] == pytest.approx(0.2 / (210 / 900))
    assert e["observed_all"]["region_ratios"]["EL611"] == pytest.approx(1.0)
    assert e["observed_all"]["region_ratios"]["EL612"] == pytest.approx(0.5 / 0.3)
    assert e["cems_maximum"]["region_ratios"]["EL612"] is None
    assert s["direction_thessaly"] == "not robust"
    assert s["direction_within_units"] == "not robust"
    assert s["direction_by_unit"] == {"EL611": "not robust", "EL612": "older people more exposed"}
    v = {r["region_id"]: r for r in s["validation"]}
    assert v["EL611"]["difference"] == pytest.approx(0, abs=1e-3)
    assert v["EL612"]["difference"] == pytest.approx(20, abs=1e-3)
    sources = json.loads((out / "sources.json").read_text())
    assert sources["products_used"] == 2 and sources["flood_layers_used"] == 2
    assert sources["population_column"] == "T" and sources["older_column"] == "Y_GE65"
    assert sources["grid_member"].endswith("ESTAT_Census_2021_V2.gpkg") and sources["grid_layer"] == "census2021"
    cells = gpd.read_file(out / "cells.gpkg")
    assert len(cells) == 10
    c = cells.set_index(cells.geometry.centroid.x.round().astype(int).astype(str) + "_" + cells.geometry.centroid.y.round().astype(int).astype(str))
    assert c.loc["5250500_1950500", "flooded_share_observed_all"] == pytest.approx(1.0)
    assert c.loc["5253500_1950500", "flooded_share_observed_all"] == pytest.approx(0.5)
    assert c.loc["5254500_1951500", "flooded_share_observed_all"] == pytest.approx(1.0)
    assert c.loc["5254500_1951500", "flooded_share_observed_water"] == pytest.approx(0.0)
    assert c.loc["5251500_1950500", "flooded_share_cems_maximum"] == pytest.approx(1.0)
    assert set(c["region_id"]) == {"EL611", "EL612"}
    for name in ("report.md", "phase-b.xlsx", "inventory.json", "preflight.json", "grid.json", "flood-extent.gpkg", "cells.gpkg"):
        assert (out / name).is_file(), name
    text = (out / "report.md").read_text()
    assert "Unit A" in text and "Volos" in text and "**not robust**" in text and "| 1.29 |" in text


def test_missing_age_column_stops_when_required(tmp_path):
    g = tmp_path / "grid.gpkg"
    grid_frame(with_age=False).to_file(g, driver="GPKG")
    with pytest.raises(KeyError, match="no age column"):
        run(make_config(tmp_path), tmp_path / "out", fetcher(product_zip(P1), product_zip(P2)), grid_path=g)


def test_grid_without_age_when_not_required(tmp_path):
    g = tmp_path / "grid.gpkg"
    grid_frame(with_age=False).to_file(g, driver="GPKG")
    out = tmp_path / "out"
    s = run(make_config(tmp_path, older_required=False), out, fetcher(product_zip(P1), product_zip(P2)), grid_path=g)
    assert s["population_exposed"] == pytest.approx(250)
    assert s["older_share_of_exposed"] is None
    assert "no age column" in (out / "report.md").read_text()


def test_no_flood_layer_stops_with_inventory(tmp_path, grid_zip):
    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w") as zf:
        zf.writestr("readme.txt", "nothing")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="no flood polygons"):
        run(make_config(tmp_path), out, fetcher(empty.getvalue(), empty.getvalue()), grid_path=grid_zip)
    assert json.loads((out / "inventory.json").read_text())[0]["ok"] is True


def test_preflight_names_failures(tmp_path, grid_zip):
    def f(url):
        raise OSError("down")

    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="preflight failed"):
        run(make_config(tmp_path), out, f, grid_path=grid_zip)
    checks = json.loads((out / "preflight.json").read_text())
    assert [c["check"] for c in checks] == ["Copernicus EMS activation", "GISCO regions", "test grid"]
    assert [c["ok"] for c in checks] == [False, False, True]


def test_direction_rule():
    from thrive.data.phase_b import direction

    assert direction([1.1, 1.3]) == "older people more exposed"
    assert direction([0.8, None, 0.9]) == "older people less exposed"
    assert direction([0.9, 1.2]) == "not robust"
    assert direction([None]) == "no data"
    assert direction([1.0000000001, 1.4]) == "not robust"
