import json
import urllib.parse

import pandas as pd
import pytest

from thrive.data.download import arcgis_records, discover_openfema_endpoint, openfema_records
from thrive.data.phase_a import CountyIndex, normalize_county, prepare_nri, run, split_counties

HMA_URL = "https://www.fema.gov/api/open/v2/HmaSubapplications"
ARCGIS = "https://example.test/arcgis/query"
CATALOG = {"metadata": {}, "DataSets": [
    {"name": "HmaSubapplications", "version": 1},
    {"name": "HmaSubapplications", "version": 2},
    {"name": "DisasterDeclarationsSummaries", "version": 2},
]}

REAL_KY = [
    ("Kentucky", "Johnson", "County", "21115", 23356, 2095864.161740346, None, 34.45013795821837, "Relatively Low"),
    ("Kentucky", "Kenton", "County", "21117", 159720, 758367.4317597508, None, 30.508474576271187, "Relatively Low"),
    ("Kentucky", "Knott", "County", "21119", 16346, 275431.5925009247, None, 38.62830114308238, "Relatively Moderate"),
    ("Kentucky", "Knox", "County", "21121", 31883, 993489.4729928812, None, 43.6342136381553, "Relatively Moderate"),
]
EXTRA = [
    ("Virginia", "Richmond", "County", "51159", 9000, 1000.0, None, 10.0, "Very Low"),
    ("Virginia", "Richmond", "City", "51760", 226000, 1000.0, None, 90.0, "Very High"),
    ("Louisiana", "Orleans", "Parish", "22071", 383000, 1000.0, 5000.0, 95.0, "Very High"),
    ("Missouri", "St. Louis", "County", "29189", 1000000, 1000.0, None, 5.0, "Very Low"),
    ("Alaska", "Juneau", "City and Borough", "02110", 32000, 1000.0, 1000.0, 20.0, "Relatively Low"),
    ("Kentucky", "Lee", "County", "21129", 7887, 0.0, None, 29.286558927867564, "Relatively Low"),
]
SIMPLE = [("Arkansas", f"C{i}", "County", f"0500{i}", 1000, 100.0, None, float(i), "Very Low" if i < 3 else ("Very High" if i > 8 else "Relatively Moderate")) for i in range(10)]


def nri_attrs(rows, inland="IFLD_EALT"):
    keys = ["STATE", "COUNTY", "COUNTYTYPE", "STCOFIPS", "POPULATION", inland, "CFLD_EALT", "SOVI_SCORE", "SOVI_RATNG"]
    return [{**dict(zip(keys, r)), "OBJECTID": i + 1, "NRI_VER": "December 2025"} for i, r in enumerate(rows)]


def sub(state, counties, amount, hazard="Flooding", program="Hazard Mitigation Grant Program", status="Closed", fy=2018, activity="Other", share=None, ident=None):
    sub.n = getattr(sub, "n", 0) + 1
    return {"subapplicationIdentifier": ident or f"DR-{sub.n:04d}", "subapplicationTitle": "t", "fiscalYear": fy, "subapplicantState": state, "benefitingCounties": counties, "totalObligatedAmount": amount, "federalShareAmount": share, "primaryHazard": hazard, "secondaryHazard": None, "tertiaryHazard": None, "program": program, "status": status, "primaryActivity": activity}


def fetcher(records, nri, catalog=True):
    def f(url):
        if url.startswith("https://example.test/catalog"):
            if not catalog:
                raise OSError("catalog down")
            return json.dumps(CATALOG).encode()
        if url.startswith(HMA_URL) or url.startswith("https://example.test/hma"):
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            top, skip = int(q.get("$top", ["1"])[0]), int(q.get("$skip", ["0"])[0])
            return json.dumps({"metadata": {}, "HmaSubapplications": records[skip:skip + top]}).encode()
        if url.startswith(ARCGIS):
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            off, n = int(q.get("resultOffset", ["0"])[0]), int(q.get("resultRecordCount", ["2000"])[0])
            return json.dumps({"features": [{"attributes": a} for a in nri[off:off + n]]}).encode()
        raise AssertionError(url)
    return f


@pytest.fixture
def config(tmp_path):
    p = tmp_path / "phase-a.toml"
    p.write_text(f'''[openfema]
dataset = "HmaSubapplications"
catalog = "https://example.test/catalog"
endpoint = "https://example.test/hma"
page_size = 2
first_fiscal_year = 2000
funded_status = ["closed", "approved", "obligated", "awarded", "completed", "closeoutinitiated", "subawardaccepted"]
fiscal_year = ["fiscalYear", "programFy"]
state = ["subapplicantState", "state"]
counties = ["benefitingCounties", "projectCounties"]
amount = ["totalObligatedAmount", "federalShareObligated"]
fallback_amount = ["federalShareAmount"]
identifier = ["subapplicationIdentifier", "projectIdentifier"]
title = ["subapplicationTitle"]
hazards = ["primaryHazard", "secondaryHazard", "tertiaryHazard"]
program = ["program", "programArea"]
status = ["status"]
activity = ["primaryActivity", "projectType", "subapplicationType"]
largest_counties_left_out = 1
max_unmatched_share = 0.25

[nri]
arcgis_query = "{ARCGIS}"
page_size = 3
fips = ["STCOFIPS"]
state = ["STATE"]
county = ["COUNTY"]
county_type = ["COUNTYTYPE"]
population = ["POPULATION"]
inland_eal = ["IFLD_EALT", "RFLD_EALT"]
coastal_eal = ["CFLD_EALT"]
vulnerability = ["SOVI_SCORE", "SVI_SCORE"]
vulnerability_rating = ["SOVI_RATNG", "SVI_RATNG"]
version = ["NRI_VER"]

[flood]
program_names = ["FMA", "Flood Mitigation Assistance"]
hazard_word = "flood"
activity_words = ["acquisition", "elevation", "flood control", "floodproofing", "drainage", "stormwater"]
''', encoding="utf-8")
    return p


def index(rows=REAL_KY + EXTRA):
    cfg_cols = {"fips": ["STCOFIPS"], "state": ["STATE"], "county": ["COUNTY"], "county_type": ["COUNTYTYPE"], "population": ["POPULATION"], "inland_eal": ["IFLD_EALT"], "coastal_eal": ["CFLD_EALT"], "vulnerability": ["SOVI_SCORE"], "vulnerability_rating": ["SOVI_RATNG"], "version": ["NRI_VER"]}
    nri, _ = prepare_nri(pd.DataFrame(nri_attrs(rows)), cfg_cols)
    return CountyIndex(nri), nri


def test_normalize_county():
    assert normalize_county("Orleans Parish") == ("orleans", False)
    assert normalize_county("Saint Louis County")[0] == normalize_county("St. Louis")[0]
    assert normalize_county("Richmond city") == ("richmond", True)
    assert normalize_county("Juneau City and Borough") == ("juneau", False)
    assert normalize_county("JOHNSON (County)")[0] == "johnson"


def test_split_counties():
    assert split_counties("Kenton; Knox") == ["Kenton", "Knox"]
    assert split_counties("Kenton, Knox") == ["Kenton", "Knox"]
    assert split_counties(None) == []
    assert split_counties(float("nan")) == []


def test_resolve_real_names_and_ambiguities():
    idx, _ = index()
    assert idx.resolve("Kentucky", "JOHNSON") == "21115"
    assert idx.resolve("Kentucky", "Kenton County") == "21117"
    assert idx.resolve("Virginia", "Richmond city") == "51760"
    assert idx.resolve("Virginia", "Richmond County") == "51159"
    assert idx.resolve("Louisiana", "Orleans Parish") == "22071"
    assert idx.resolve("Missouri", "Saint Louis County") == "29189"
    assert idx.resolve("Alaska", "Juneau City and Borough") == "02110"
    assert idx.resolve("Kentucky", "Atlantis") is None
    assert idx.resolve("Ohio", "Johnson") is None


def test_nri_accepts_old_riverine_column():
    cols = {"fips": ["STCOFIPS"], "state": ["STATE"], "county": ["COUNTY"], "county_type": ["COUNTYTYPE"], "population": ["POPULATION"], "inland_eal": ["IFLD_EALT", "RFLD_EALT"], "coastal_eal": ["CFLD_EALT"], "vulnerability": ["SOVI_SCORE"], "vulnerability_rating": ["SOVI_RATNG"], "version": ["NRI_VER"]}
    nri, used = prepare_nri(pd.DataFrame(nri_attrs(REAL_KY, inland="RFLD_EALT")), cols)
    assert used["inland_eal"] == "RFLD_EALT"
    assert nri.loc[nri["fips"] == "21115", "flood_eal"].iloc[0] == pytest.approx(2095864.161740346)


def test_coastal_and_inland_are_added():
    _, nri = index()
    assert nri.loc[nri["fips"] == "22071", "flood_eal"].iloc[0] == pytest.approx(6000.0)


def test_paging_helpers():
    records = [sub("Kentucky", "Knox", i) for i in range(5)]
    rows, digests = openfema_records(HMA_URL, 2, fetcher(records, []))
    assert len(rows) == 5 and len(digests) == 3
    attrs = nri_attrs(REAL_KY + EXTRA)
    rows, digests = arcgis_records(ARCGIS, 3, fetcher([], attrs))
    assert len(rows) == len(attrs)
    assert discover_openfema_endpoint("HmaSubapplications", "https://example.test/catalog", fetcher([], [])) == HMA_URL


def test_arcgis_error_is_reported():
    with pytest.raises(RuntimeError, match="ArcGIS service error"):
        arcgis_records(ARCGIS, 3, lambda url: json.dumps({"error": {"code": 400, "message": "Invalid field"}}).encode())


def test_run_simple_numbers(config, tmp_path):
    records = [
        sub("Arkansas", "C0", 300.0),
        sub("Arkansas", "C1", 300.0, program="FMA", hazard="Other"),
        sub("Arkansas", "C9", 50.0),
        sub("Arkansas", "C9", 999.0, hazard="Wildfire"),
        sub("Arkansas", "C9", 999.0, status="Withdrawn"),
        sub("Arkansas", "C9", 999.0, status="notSelected"),
        sub("Arkansas", "C9", 999.0, fy=1995),
        sub("Arkansas", "C9", 999.0, status="Pending"),
        sub("Arkansas", "Statewide", 777.0),
    ]
    out = tmp_path / "out"
    summary = run(config, out, fetcher(records, nri_attrs(SIMPLE)))
    assert summary["counties"] == 10
    assert summary["total_funding"] == pytest.approx(650.0)
    assert summary["funding_per_eal_dollar_by_quintile"] == pytest.approx([3.0, 0.0, 0.0, 0.0, 0.25])
    assert summary["r_cov_most_vs_least_vulnerable"] == pytest.approx(0.25 / 3.0)
    rb = summary["robustness"]
    assert rb["r_cov_without_largest"] == pytest.approx(0.25 / 3.0)
    assert rb["r_cov_median_county"] == pytest.approx(0.25 / 3.0)
    assert rb["r_cov_median_funded_county"] == pytest.approx(0.5 / 3.0)
    assert summary["robust_direction"] == "less for the most vulnerable"
    sources = json.loads((out / "sources.json").read_text())
    assert sources["openfema_endpoint"] == HMA_URL
    assert sources["subgrants_in_scope"] == 4
    assert sources["statewide_funding"] == pytest.approx(777.0)
    assert sources["nri_version"] == "December 2025"
    assert sources["amount_field"] == "totalObligatedAmount"
    assert [c["ok"] for c in json.loads((out / "preflight.json").read_text())] == [True, True, True]
    assert len(json.loads((out / "sample.json").read_text())["openfema"]) == len(records)
    assert pd.ExcelFile(out / "phase-a.xlsx").sheet_names == ["Quintiles", "Counties", "Activities", "Largest grants", "Unmatched counties", "Sources"]
    assert "most vulnerable" in (out / "report.md").read_text()


def test_multi_county_subgrant_is_split(config, tmp_path):
    rows = REAL_KY + EXTRA
    out = tmp_path / "out"
    run(config, out, fetcher([sub("Kentucky", "Kenton; Knox", 100.0)], nri_attrs(rows)))
    counties = pd.read_excel(out / "phase-a.xlsx", sheet_name="Counties", dtype={"fips": str})
    got = dict(zip(counties["fips"], counties["funding"]))
    assert got["21117"] == pytest.approx(50.0) and got["21121"] == pytest.approx(50.0)


def test_too_many_unmatched_names_stop_the_run(config, tmp_path):
    out = tmp_path / "out"
    records = [sub("Kentucky", "Atlantis", 900.0), sub("Kentucky", "Knox", 100.0)]
    with pytest.raises(ValueError, match="could not be matched"):
        run(config, out, fetcher(records, nri_attrs(REAL_KY + EXTRA)))
    miss = pd.read_excel(out / "phase-a.xlsx", sheet_name="Unmatched counties")
    assert miss.iloc[0]["county as written"] == "Atlantis"


def test_falls_back_when_catalog_is_down(config, tmp_path):
    out = tmp_path / "out"
    run(config, out, fetcher([sub("Arkansas", "C0", 10.0)], nri_attrs(SIMPLE), catalog=False))
    assert json.loads((out / "sources.json").read_text())["openfema_endpoint"] == "https://example.test/hma"


def test_preflight_reports_every_problem(config, tmp_path):
    def f(url):
        if url.startswith(ARCGIS) or url.startswith(HMA_URL) or url.startswith("https://example.test/hma"):
            raise OSError("down")
        return fetcher([], [])(url)

    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="preflight failed") as err:
        run(config, out, f)
    assert "National Risk Index" in str(err.value) and "OpenFEMA" in str(err.value)
    checks = [c["check"] for c in json.loads((out / "preflight.json").read_text())]
    assert checks == ["OpenFEMA catalog", "OpenFEMA first record", "OpenFEMA configured endpoint", "National Risk Index"]


def test_missing_column_is_named(config, tmp_path):
    bad = [{k: v for k, v in sub("Arkansas", "C0", 10.0).items() if k != "totalObligatedAmount"}]
    with pytest.raises(KeyError, match="amount"):
        run(config, tmp_path / "out", fetcher(bad, nri_attrs(SIMPLE)))


def test_reversed_vulnerability_is_refused(config, tmp_path):
    flipped = [(s, c, t, f, p, i, co, -v, r) for s, c, t, f, p, i, co, v, r in SIMPLE]
    with pytest.raises(ValueError, match="vulnerability"):
        run(config, tmp_path / "out", fetcher([sub("Arkansas", "C0", 10.0)], nri_attrs(flipped)))


def test_flood_by_activity_and_fallback_amount(config, tmp_path):
    out = tmp_path / "out"
    records = [
        sub("Arkansas", "C0", None, hazard="Hurricane", activity="Elevation", share=400.0),
        sub("Arkansas", "C9", 100.0, hazard="Severe Storm(s)", activity="Flood control"),
        sub("Arkansas", "C9", 100.0, hazard="Tornado", activity="Saferoom/shelter"),
    ]
    summary = run(config, out, fetcher(records, nri_attrs(SIMPLE)))
    assert summary["total_funding"] == pytest.approx(500.0)
    sources = json.loads((out / "sources.json").read_text())
    assert sources["money_from_fallback"] == pytest.approx(400.0)
    assert sources["flood_reason_money"] == {"activity": pytest.approx(500.0)}


def test_duplicate_identifiers_are_counted_once(config, tmp_path):
    out = tmp_path / "out"
    records = [sub("Arkansas", "C0", 100.0, ident="DR-1"), sub("Arkansas", "C0", 300.0, ident="DR-1"), sub("Arkansas", "C9", 50.0)]
    summary = run(config, out, fetcher(records, nri_attrs(SIMPLE)))
    assert summary["total_funding"] == pytest.approx(350.0)
    assert json.loads((out / "sources.json").read_text())["duplicate_identifier_rows"] == 2
