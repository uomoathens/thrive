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


def to_geojson(geoms, crs_from=3035):
    return gpd.GeoDataFrame(geometry=geoms, crs=crs_from).to_crs(4326).to_json().encode()


def product_zip(flood_geoms):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("EMSR692_AOI01_DEL_PRODUCT_observedEventA_v1.json", to_geojson(flood_geoms))
        zf.writestr("EMSR692_AOI01_DEL_PRODUCT_areaOfInterestA_v1.json", to_geojson([box(5240000, 1940000, 5260000, 1960000)]))
    return buf.getvalue()


def nuts():
    gdf = gpd.GeoDataFrame({
        "NUTS_ID": ["EL611", "EL612", "EL521"],
        "NAME_LATN": ["Unit A", "Unit B", "Elsewhere"],
    }, geometry=[box(5250000, 1950000, 5253000, 1952000), box(5253000, 1950000, 5255000, 1952000), box(5300000, 1950000, 5302000, 1952000)], crs=3035)
    return gdf.to_crs(4326).to_json().encode()


@pytest.fixture
def grid(tmp_path):
    pts, pop, old = [], [], []
    for i in range(5):
        for j in range(2):
            pts.append(Point(5250500 + 1000 * i, 1950500 + 1000 * j))
            pop.append(100)
            old.append(50 if (i, j) == (3, 0) else 20)
    path = tmp_path / "grid.gpkg"
    gpd.GeoDataFrame({"TOT_P_2021": pop, "Y_GE65_2021": old}, geometry=pts, crs=3035).to_file(path, driver="GPKG")
    return path


@pytest.fixture
def config(tmp_path):
    p = tmp_path / "phase-b.toml"
    p.write_text(f'''[cems]
activation = "EMSR692"
detail = "{DETAIL}"
product_types = ["DEL", "GRA"]
flood_layer_words = ["observedevent"]

[grid]
url = "https://example.test/grid.gpkg"
population = ["TOT_P_2021", "T", "TOT_P"]
older = ["Y_GE65_2021", "Y_GE65"]
cell_size_m = 1000

[regions]
url = "https://example.test/nuts.geojson"
prefix = "EL61"

[analysis]
crs = 3035
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


def test_products_keep_only_downloadable_flood_types():
    act, products = activation_products(DETAIL, "EMSR692", ["DEL", "GRA"], fetcher(b"", b""))
    assert act["code"] == "EMSR692"
    assert [p["url"] for p in products] == ["https://example.test/p1.zip", "https://example.test/p2.zip"]


def test_unknown_activation():
    with pytest.raises(ValueError):
        activation_products(DETAIL, "EMSR000", ["DEL"], lambda url: json.dumps({"results": []}).encode())


def test_flood_layers_are_picked_by_name():
    found, layers = flood_polygons(product_zip([box(5250000, 1950000, 5251000, 1951000)]), ["observedevent"], 3035)
    assert len(found) == 1
    assert len(layers) == 2


def test_exposure_numbers(config, grid, tmp_path):
    p1 = product_zip([box(5250000, 1950000, 5251000, 1951000)])
    p2 = product_zip([box(5253000, 1950000, 5253500, 1951000), box(5250000, 1950000, 5250500, 1951000)])
    out = tmp_path / "out"
    summary = run(config, out, fetcher(p1, p2), grid_path=grid)
    regions = {r["region_id"]: r for r in summary["regions"]}
    assert set(regions) == {"EL611", "EL612"}
    assert regions["EL611"]["population"] == pytest.approx(600, rel=1e-3)
    assert regions["EL612"]["population"] == pytest.approx(400, rel=1e-3)
    assert regions["EL611"]["population_exposed"] == pytest.approx(100, rel=1e-3)
    assert regions["EL612"]["population_exposed"] == pytest.approx(50, rel=1e-3)
    assert regions["EL611"]["flooded_km2"] == pytest.approx(1.0, rel=1e-3)
    assert regions["EL612"]["flooded_km2"] == pytest.approx(0.5, rel=1e-3)
    assert regions["EL612"]["older_exposed"] == pytest.approx(25, rel=1e-3)
    assert summary["population_exposed"] == pytest.approx(150, rel=1e-3)
    assert summary["share_exposed"] == pytest.approx(0.15, rel=1e-3)
    assert summary["older_share_of_exposed"] == pytest.approx(45 / 150, rel=1e-3)
    sources = json.loads((out / "sources.json").read_text())
    assert sources["products_used"] == 2 and sources["flood_layers_used"] == 2
    assert sources["population_column"] == "TOT_P_2021" and sources["older_column"] == "Y_GE65_2021"
    for name in ("report.md", "phase-b.xlsx", "inventory.json", "preflight.json", "flood-extent.gpkg"):
        assert (out / name).is_file(), name
    assert "Unit A" in (out / "report.md").read_text()


def test_no_flood_layer_stops_with_inventory(config, grid, tmp_path):
    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w") as zf:
        zf.writestr("readme.txt", "nothing")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="no flood polygons"):
        run(config, out, fetcher(empty.getvalue(), empty.getvalue()), grid_path=grid)
    assert json.loads((out / "inventory.json").read_text())[0]["ok"] is True


def test_preflight_names_failures(config, grid, tmp_path):
    def f(url):
        raise OSError("down")

    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="preflight failed"):
        run(config, out, f, grid_path=grid)
    checks = json.loads((out / "preflight.json").read_text())
    assert [c["check"] for c in checks] == ["Copernicus EMS activation", "GISCO regions", "GISCO 1 km grid"]
    assert [c["ok"] for c in checks] == [False, False, True]


def test_grid_without_age_column(config, tmp_path):
    pts = [Point(5250500 + 1000 * i, 1950500 + 1000 * j) for i in range(5) for j in range(2)]
    path = tmp_path / "grid-total.gpkg"
    gpd.GeoDataFrame({"TOT_P_2021": [100] * 10}, geometry=pts, crs=3035).to_file(path, driver="GPKG")
    p1 = product_zip([box(5250000, 1950000, 5251000, 1951000)])
    out = tmp_path / "out"
    summary = run(config, out, fetcher(p1, p1), grid_path=path)
    assert summary["population_exposed"] == pytest.approx(100, rel=1e-3)
    assert summary["older_exposed"] is None
    assert "no age column" in (out / "report.md").read_text()
