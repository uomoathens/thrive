import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thrive.data.phase_c import (
    burnt_by_region,
    burnt_check,
    coefficient_check,
    event_study,
    eurostat_url,
    exposure_table,
    greek_nuts,
    growth_panel,
    jsonstat_frame,
    load_config,
    nights_growth,
    run,
)

ROOT = Path(__file__).resolve().parents[1]


def jsonstat(dims: dict, values: dict) -> bytes:
    ids = list(dims)
    payload = {
        "id": ids,
        "size": [len(v) for v in dims.values()],
        "dimension": {d: {"category": {"index": {c: i for i, c in enumerate(cs)}, "label": {c: c for c in cs}}} for d, cs in dims.items()},
        "value": {str(k): v for k, v in values.items()},
        "updated": "2026-03-23T23:00:00+0100",
    }
    return json.dumps(payload).encode()


def flat(dims: dict, cell: dict) -> int:
    pos = 0
    for d, cs in dims.items():
        pos = pos * len(cs) + cs.index(cell[d])
    return pos


def test_config_holds_table_c2_and_c1():
    cfg = load_config(ROOT / "config" / "phase-c.toml")
    assert cfg["validation"]["real"]["G-I"] == [0.07, -0.21, -0.54, -0.05, -0.80]
    assert cfg["validation"]["nominal"]["G-I"] == [-0.22, -0.41, -0.06, -0.69]
    assert sum(cfg["validation"]["nominal"]["G-I"][:3]) == pytest.approx(-0.69)
    for sector, row in ((k, v) for k, v in cfg["validation"]["real"].items() if isinstance(v, list)):
        assert sum(row[1:4]) == pytest.approx(row[4], abs=0.011), sector
    burnt = {b["region_id"]: b for b in cfg["validation"]["burnt"]}
    assert burnt["EL421"]["share_pct"] == 6.9 and burnt["EL421"]["hectares"] == 18687
    assert cfg["study"]["first_year"] == 2018 and cfg["study"]["last_year"] == 2023
    assert cfg["eurostat"]["expected_regions"] == 52


def test_eurostat_url_repeats_filters():
    url = eurostat_url("https://x/{code}", "nama_10r_3gva", {"unit": "CP_MEUR", "nace_r2": ["A", "G-I"]}, 2014)
    assert url.startswith("https://x/nama_10r_3gva?")
    assert "nace_r2=A&nace_r2=G-I" in url and "sinceTimePeriod=2014" in url


def test_jsonstat_frame_places_every_value():
    dims = {"unit": ["CP_MEUR"], "geo": ["EL421", "EL511"], "time": ["2021", "2022", "2023"]}
    values = {flat(dims, {"unit": "CP_MEUR", "geo": g, "time": t}): float(i) for i, (g, t) in enumerate((g, t) for g in dims["geo"] for t in dims["time"])}
    frame, meta = jsonstat_frame(jsonstat(dims, values))
    assert len(frame) == 6
    assert frame[(frame.geo == "EL511") & (frame.time == "2023")]["value"].iloc[0] == 5.0
    assert meta["updated"].startswith("2026-03-23")


def test_greek_nuts_keeps_level_and_drops_extra_regio():
    frame = pd.DataFrame({"geo": ["EL", "EL4", "EL42", "EL421", "ELZZZ", "EL42Z", "CY000"], "value": range(7)})
    assert greek_nuts(frame, "EL", 3)["geo"].tolist() == ["EL421"]
    assert greek_nuts(frame, "EL", 2)["geo"].tolist() == ["EL42"]


def test_growth_uses_the_nuts2_deflator_and_population():
    gva3 = pd.DataFrame({"geo": ["EL421"] * 2, "nace_r2": ["G-I"] * 2, "time": ["2022", "2023"], "value": [100.0, 121.0]})
    pop3 = pd.DataFrame({"geo": ["EL421"] * 2, "time": ["2022", "2023"], "value": [200.0, 220.0]})
    n2 = pd.DataFrame({"geo": ["EL42"] * 2, "time": ["2022", "2023"], "value": [1000.0, 1050.0]})
    v2 = pd.DataFrame({"geo": ["EL42"] * 2, "time": ["2022", "2023"], "value": [100.0, 100.0]})
    out = growth_panel(gva3, pop3, n2, v2)
    row = out.iloc[0]
    assert row["year"] == 2023
    assert row["growth_nominal"] == pytest.approx((1.21 / 1.10 - 1) * 100)
    assert row["deflator_change"] == pytest.approx(5.0)
    assert row["growth_real"] == pytest.approx((1.21 / 1.05 / 1.10 - 1) * 100)


def test_burnt_share_sums_fires_inside_each_region():
    import geopandas as gpd
    from shapely.geometry import box

    regions = gpd.GeoDataFrame({"region_id": ["EL001", "EL002"], "region_name": ["West", "East"]}, geometry=[box(0, 0, 10000, 10000), box(10000, 0, 20000, 10000)], crs=3035)
    regions["area_ha"] = regions.geometry.area / 1e4
    fires = gpd.GeoDataFrame(
        {"fire_id": ["a", "b", "c"], "fire_date": pd.to_datetime(["2021-08-01", "2021-08-10", "2023-07-18"]), "fire_year": [2021, 2021, 2023]},
        geometry=[box(9000, 0, 11000, 1000), box(0, 0, 1000, 1000), box(15000, 5000, 16000, 6000)],
        crs=3035,
    )
    burnt = burnt_by_region(fires, regions)
    exp = exposure_table(burnt, regions, range(2020, 2025)).set_index(["region_id", "year"])
    assert exp.loc[("EL001", 2021), "burnt_ha"] == pytest.approx(200.0)
    assert exp.loc[("EL001", 2021), "share_pct"] == pytest.approx(2.0)
    assert exp.loc[("EL001", 2021), "fires"] == 2
    assert exp.loc[("EL002", 2021), "burnt_ha"] == pytest.approx(100.0)
    assert exp.loc[("EL002", 2023), "share_pct"] == pytest.approx(1.0)
    assert exp.loc[("EL002", 2022), "share_pct"] == 0.0
    assert len(exp) == 10


def synthetic_panel(beta, n_regions=40, seed=1, noise=0.05):
    rng = np.random.default_rng(seed)
    regions = [f"EL{i:03d}" for i in range(n_regions)]
    years = range(2016, 2025)
    x = pd.DataFrame([{"region_id": r, "year": y, "share_pct": float(rng.exponential(1.0) * (rng.random() < 0.3))} for r in regions for y in years])
    xs = x.set_index(["region_id", "year"])["share_pct"]
    alpha = dict(zip(regions, rng.normal(0, 2, n_regions)))
    delta = {y: rng.normal(0, 2) for y in years}
    rows = []
    for r in regions:
        for t in range(2018, 2024):
            y = alpha[r] + delta[t] + sum(b * xs[(r, t - k)] for b, k in zip(beta, (-1, 0, 1, 2))) + rng.normal(0, noise)
            rows.append({"region_id": r, "sector": "G-I", "year": t, "growth_real": y, "growth_nominal": y})
    return pd.DataFrame(rows), x


def test_event_study_recovers_known_effects():
    beta = [0.07, -0.21, -0.54, -0.05]
    growth, x = synthetic_panel(beta)
    res = event_study(growth, x, "G-I", "growth_real", 2018, 2023)
    assert res["horizons"] == ["year before", "fire year", "year after", "two years after"]
    assert res["observations"] == 40 * 6 and res["regions"] == 40
    assert res["coef"] == pytest.approx(beta, abs=0.02)
    assert res["cumulative"] == pytest.approx(sum(beta[1:]), abs=0.03)
    assert res["p"][2] < 0.01
    assert all(s > 0 for s in res["se"])


def test_event_study_matches_textbook_clustered_errors():
    beta = [0.0, -0.3, -0.5, 0.0]
    growth, x = synthetic_panel(beta, n_regions=12, seed=7, noise=0.5)
    res = event_study(growth, x, "G-I", "growth_real", 2018, 2023)
    xs = x.set_index(["region_id", "year"])["share_pct"]
    d = growth.copy()
    for name, k in zip(("lead", "x0", "x1", "x2"), (-1, 0, 1, 2)):
        d[name] = [xs[(r, t - k)] for r, t in zip(d.region_id, d.year)]
    X = pd.concat([d[["lead", "x0", "x1", "x2"]], pd.get_dummies(d.region_id, dtype=float), pd.get_dummies(d.year, drop_first=True, dtype=float)], axis=1).to_numpy()
    y = d.growth_real.to_numpy()
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    assert res["coef"] == pytest.approx(list(b[:4]), abs=1e-8)
    inv = np.linalg.pinv(X.T @ X)
    u = y - X @ b
    meat = sum(np.outer(X[d.region_id.to_numpy() == g].T @ u[d.region_id.to_numpy() == g], X[d.region_id.to_numpy() == g].T @ u[d.region_id.to_numpy() == g]) for g in d.region_id.unique())
    n, G, k = len(y), 12, 4 + 5
    V = inv @ meat @ inv * G / (G - 1) * (n - 1) / (n - k)
    assert res["se"] == pytest.approx(list(np.sqrt(np.diag(V)[:4])), rel=1e-8)


def test_coefficient_check_flags_differences():
    cfg = {"tolerance": {"coefficient": 0.05}, "real": {"G-I": [0.07, -0.21, -0.54, -0.05, -0.80]}, "nominal": {"G-I": [-0.22, -0.41, -0.06, -0.69]}}
    good = {"sector": "G-I", "measure": "growth_real", "horizons": ["year before", "fire year", "year after", "two years after"], "coef": [0.06, -0.20, -0.55, -0.04], "p": [0.5, 0.08, 0.0, 0.8], "cumulative": -0.79, "cumulative_p": 0.0}
    nominal = {**good, "measure": "growth_nominal", "coef": [0.0, -0.22, -0.30, -0.06], "cumulative": -0.58}
    df = coefficient_check([good, nominal], cfg)
    real = df[df.measure == "real"]
    assert len(real) == 5 and real["within_tolerance"].all()
    nom = df[df.measure == "nominal"]
    assert nom["horizon"].tolist() == ["fire year", "year after", "two years after", "cumulative"]
    assert nom.set_index("horizon")["within_tolerance"].to_dict() == {"fire year": True, "year after": False, "two years after": True, "cumulative": False}


def test_nights_growth_by_residence():
    nights = pd.DataFrame({"geo": ["EL421"] * 4, "c_resid": ["TOTAL", "TOTAL", "FOR", "FOR"], "time": ["2023", "2024", "2023", "2024"], "value": [25158840.0, 28745136.0, 24153130.0, 27637097.0]})
    out = nights_growth(nights).set_index("sector")
    assert out.loc["TOTAL", "growth_nights"] == pytest.approx(14.25, abs=0.01)
    assert out.loc["FOR", "growth_nights"] == pytest.approx(14.42, abs=0.01)
    assert (out["year"] == 2024).all()


def test_burnt_check_needs_name_share_and_hectares():
    exp = pd.DataFrame({"region_id": ["EL421", "EL511"], "region_name": ["Kalymnos, Karpathos, Kasos, Kos, Rodos", "Evros"], "year": [2023, 2023], "burnt_ha": [18700.0, 80000.0], "share_pct": [6.92, 18.9]})
    cfg = {"tolerance": {"share_pct": 0.3, "hectares_rel": 0.05}, "burnt": [
        {"region_id": "EL421", "name_contains": "Rodos", "year": 2023, "hectares": 18687, "share_pct": 6.9},
        {"region_id": "EL511", "name_contains": "Evros", "year": 2023, "hectares": 94578, "share_pct": 22.3},
        {"region_id": "EL642", "name_contains": "Evvoia", "year": 2021, "hectares": 52668, "share_pct": 12.6},
    ]}
    out = burnt_check(exp, cfg).set_index("region_id")
    assert out.loc["EL421", "within_tolerance"]
    assert not out.loc["EL511", "within_tolerance"]
    assert not out.loc["EL642", "within_tolerance"]


def fake_world(tmp_path, beta):
    import geopandas as gpd
    from shapely.geometry import box

    ids = ["EL111", "EL112", "EL121", "EL122"]
    names = ["Alpha", "Beta", "Gamma", "Delta"]
    boxes = [box(22.0 + i * 0.2, 38.0, 22.2 + i * 0.2, 38.2) for i in range(4)]
    regions = gpd.GeoDataFrame({"NUTS_ID": ids, "NAME_LATN": names}, geometry=boxes, crs=4326)
    nuts = regions.to_json().encode()
    area = regions.to_crs(3035).geometry.area.to_numpy() / 1e4
    fire_specs = [("f1", "2021-08-03", 0, 0.03), ("f2", "2023-07-18", 2, 0.05), ("f3", "2019-07-01", 1, 0.02), ("f4", "2016-08-01", 3, 0.04), ("f5", "2022-08-01", 1, 0.03), ("f6", "2024-07-20", 3, 0.02)]
    fires = gpd.GeoDataFrame(
        {"id": [f[0] for f in fire_specs], "FIREDATE": [f[1] for f in fire_specs]},
        geometry=[box(22.0 + r * 0.2 + 0.01, 38.01, 22.0 + r * 0.2 + 0.01 + s, 38.01 + s) for _, _, r, s in fire_specs],
        crs=4326,
    )
    shp = tmp_path / "effis"
    shp.mkdir()
    fires.to_file(shp / "modis.ba.poly.shp")
    zp = tmp_path / "effis_layer.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        for p in shp.iterdir():
            zf.write(p, p.name)
    fires_3035 = fires.to_crs(3035)
    years = [str(y) for y in range(2014, 2025)]
    x = {(ids[r], int(d[:4])): fires_3035.geometry.iloc[i].intersection(regions.to_crs(3035).geometry.iloc[r]).area / 1e4 / area[r] * 100 for i, (_, d, r, _) in enumerate(fire_specs)}
    sectors = ["A", "B-E", "C", "G-I", "TOTAL"]
    gva_dims = {"unit": ["CP_MEUR"], "nace_r2": sectors, "geo": ["EL11", "EL12"] + ids, "time": years}
    level = {}
    gva_values = {}
    for g in gva_dims["geo"]:
        for s in sectors:
            v = 100.0
            for t in years:
                y = int(t)
                if len(g) == 5 and s == "G-I":
                    v *= 1 + (2.0 + sum(b * x.get((g, y - k), 0.0) for b, k in zip(beta, (-1, 0, 1, 2)))) / 100
                else:
                    v *= 1.02
                level[(g, s, t)] = v
                gva_values[flat(gva_dims, {"unit": "CP_MEUR", "nace_r2": s, "geo": g, "time": t})] = v
    pop_dims = {"unit": ["THS"], "geo": ids, "time": years}
    pop = jsonstat(pop_dims, {flat(pop_dims, {"unit": "THS", "geo": g, "time": t}): 100.0 for g in ids for t in years})
    vol_dims = {"freq": ["A"], "na_item": ["B1G"], "unit": ["I20"], "geo": ["EL11", "EL12"], "time": years}
    vol = jsonstat(vol_dims, {flat(vol_dims, {"freq": "A", "na_item": "B1G", "unit": "I20", "geo": g, "time": t}): level[(g, "TOTAL", t)] for g in ["EL11", "EL12"] for t in years})
    gva = jsonstat(gva_dims, gva_values)
    t_years = [str(y) for y in range(2020, 2026)]
    t_dims = {"freq": ["A"], "c_resid": ["FOR", "TOTAL"], "unit": ["NR"], "nace_r2": ["I551-I553"], "geo": ids, "time": t_years}
    t_values = {}
    for g in ids:
        for c in t_dims["c_resid"]:
            v = 1000.0
            for t in t_years:
                y = int(t)
                if y > 2020:
                    v *= 1 + (5.0 + sum(b * x.get((g, y - k), 0.0) for b, k in zip(beta, (-1, 0, 1, 2)))) / 100
                t_values[flat(t_dims, {"freq": "A", "c_resid": c, "unit": "NR", "nace_r2": "I551-I553", "geo": g, "time": t})] = v
    tour = jsonstat(t_dims, t_values)

    def fetcher(url):
        if "nama_10r_3gva" in url:
            return gva
        if "nama_10r_3popgdp" in url:
            return pop
        if "nama_10r_2gvagr" in url:
            return vol
        if "tour_occ_nin3" in url:
            return tour
        if "NUTS_RG" in url:
            return nuts
        raise AssertionError(url)

    text = (ROOT / "config" / "phase-c.toml").read_text(encoding="utf-8").replace("expected_regions = 52", "expected_regions = 4")
    cfg = tmp_path / "phase-c.toml"
    cfg.write_text(text, encoding="utf-8")
    return cfg, fetcher, zp


@pytest.mark.parametrize("beta", [[0.0, -0.21, -0.54, -0.05]])
def test_run_writes_every_output_and_refuses_an_unreplicated_result(tmp_path, beta):
    cfg, fetcher, zp = fake_world(tmp_path, beta)
    out = tmp_path / "out"
    summary = run(cfg, out, fetcher=fetcher, effis_path=zp)
    for name in ("preflight.json", "sources.json", "summary.json", "report.md", "phase-c.xlsx"):
        assert (out / name).is_file(), name
    assert summary["replicated"] is False
    assert summary["regions"] == 4 and summary["fires_matched"] == 6
    tour = {r["sector"]: r for r in summary["tourism"]["results"]}
    assert set(tour) == {"TOTAL", "FOR"}
    assert tour["TOTAL"]["coef"] == pytest.approx(beta, abs=1e-6)
    assert tour["TOTAL"]["observations"] == 4 * 4
    assert "Tourism nights after a fire" in (out / "report.md").read_text(encoding="utf-8")
    gi = next(r for r in summary["results"] if r["sector"] == "G-I" and r["measure"] == "growth_nominal")
    assert gi["coef"][1:] == pytest.approx(beta[1:], abs=1e-6)
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "NOT replicated" in report
    sheets = pd.ExcelFile(out / "phase-c.xlsx").sheet_names
    assert sheets == ["Replication", "Burnt area check", "Event studies", "Nights after a fire", "Tourism nights", "Burnt share by region", "Growth panel", "Fires by region", "Sources"]
    src = json.loads((out / "sources.json").read_text(encoding="utf-8"))
    assert src["effis_date_field"] == "FIREDATE" and src["effis_id_field"] == "id"


def test_run_stops_when_regions_are_missing(tmp_path):
    cfg, fetcher, zp = fake_world(tmp_path, [0, 0, 0, 0])
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("expected_regions = 4", "expected_regions = 52"), encoding="utf-8")
    with pytest.raises(ValueError, match="expected 52"):
        run(cfg, tmp_path / "out", fetcher=fetcher, effis_path=zp)


def test_workflows_commit_without_a_message():
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        if "git commit" in text:
            assert 'git commit --allow-empty-message -m ""' in text, path.name
            assert text.count("git commit") == 1, path.name
