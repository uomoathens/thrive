import io
import json
import zipfile

import pandas as pd
import pytest

from thrive.data.download import first_working, openfema_records, zip_member
from thrive.data.phase_a import county_fips, is_flood_project, run

WORDS = ("flood", "riverine", "coastal", "drainage", "acquisition", "elevation")

NRI_ROWS = [
    ("05001", 1000, 100.0, 0.0, 1.0, "Very Low"),
    ("05003", 1000, 100.0, 0.0, 2.0, "Very Low"),
    ("05005", 1000, 100.0, 0.0, 3.0, "Relatively Low"),
    ("05007", 1000, 100.0, 0.0, 4.0, "Relatively Low"),
    ("05009", 1000, 100.0, 0.0, 5.0, "Relatively Moderate"),
    ("05011", 1000, 100.0, 0.0, 6.0, "Relatively Moderate"),
    ("05013", 1000, 100.0, 0.0, 7.0, "Relatively High"),
    ("05015", 1000, 100.0, 0.0, 8.0, "Relatively High"),
    ("05017", 1000, 50.0, 50.0, 9.0, "Very High"),
    ("05019", 1000, 100.0, "", 10.0, "Very High"),
    ("05021", 1000, 0.0, 0.0, 11.0, "Very High"),
]


def hma(state, county, area, ptype, status, fy, money):
    return {"programArea": area, "programFy": fy, "stateNumberCode": state, "countyCode": county, "projectType": ptype, "status": status, "federalShareObligated": money, "projectIdentifier": f"{county}-{ptype}"}


RECORDS = [
    hma("5", "1", "HMGP", "200.1: Acquisition of Private Real Property - Riverine", "Closed", 2010, 400.0),
    hma("5", "3", "FMA", "Other", "Closed", 2015, 200.0),
    hma("5", "17", "HMGP", "202.1: Elevation of Private Structures - Riverine", "Closed", 2018, 100.0),
    hma("5", "19", "HMGP", "601.1: Generators", "Closed", 2018, 999.0),
    hma("5", "19", "HMGP", "200.1: Acquisition - Riverine", "Withdrawn", 2018, 999.0),
    hma("5", "19", "HMGP", "200.1: Acquisition - Riverine", "Closed", 1995, 999.0),
    hma("5", "0", "HMGP", "200.1: Acquisition - Riverine", "Closed", 2012, 777.0),
]


def nri_zip():
    df = pd.DataFrame(NRI_ROWS, columns=["STCOFIPS", "POPULATION", "RFLD_EALT", "CFLD_EALT", "SOVI_SCORE", "SOVI_RATNG"])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("NRI_Table_Counties/NRI_Table_Counties.csv", df.to_csv(index=False))
    return buf.getvalue()


def fake_fetcher(page_size):
    def f(url):
        if url.startswith("https://example.test/hma"):
            skip = int(url.split("$skip=")[1].split("&")[0])
            page = RECORDS[skip:skip + page_size]
            return json.dumps({"metadata": {"skip": skip}, "HazardMitigationAssistanceProjects": page}).encode()
        if url == "https://bad.test/nri.zip":
            raise OSError("down")
        if url == "https://example.test/nri.zip":
            return nri_zip()
        raise AssertionError(url)
    return f


@pytest.fixture
def config(tmp_path):
    p = tmp_path / "phase-a.toml"
    p.write_text('''[openfema]
endpoint = "https://example.test/hma"
page_size = 3
first_fiscal_year = 2000
excluded_status = ["Void", "Withdrawn"]

[nri]
urls = ["https://bad.test/nri.zip", "https://example.test/nri.zip"]
member = "NRI_Table_Counties.csv"
fips = ["STCOFIPS"]
population = ["POPULATION"]
riverine_eal = ["RFLD_EALT"]
coastal_eal = ["CFLD_EALT"]
vulnerability = ["SOVI_SCORE", "SVI_SCORE"]
vulnerability_rating = ["SOVI_RATNG", "SVI_RATNG"]

[flood]
program_areas = ["FMA"]
words = ["flood", "riverine", "coastal", "drainage", "acquisition", "elevation"]
''', encoding="utf-8")
    return p


def test_county_fips_pads_openfema_codes():
    assert county_fips("5", "21") == "05021"
    assert county_fips("72", "21") == "72021"
    assert county_fips("5", "0") is None
    assert county_fips(None, "21") is None


def test_flood_rule():
    assert is_flood_project("FMA", "anything", ("FMA",), WORDS)
    assert is_flood_project("HMGP", "202.1: Elevation of Private Structures - Riverine", ("FMA",), WORDS)
    assert not is_flood_project("HMGP", "601.1: Generators", ("FMA",), WORDS)
    assert not is_flood_project("HMGP", None, ("FMA",), WORDS)


def test_paging_reads_every_page():
    rows, digests = openfema_records("https://example.test/hma", 3, fake_fetcher(3))
    assert len(rows) == len(RECORDS)
    assert len(digests) == 3


def test_first_working_skips_a_dead_source():
    url, data = first_working(["https://bad.test/nri.zip", "https://example.test/nri.zip"], fake_fetcher(3))
    assert url == "https://example.test/nri.zip"
    assert b"STCOFIPS" in zip_member(data, "NRI_Table_Counties.csv")


def test_run_end_to_end(config, tmp_path):
    out = tmp_path / "out"
    summary = run(config, out, fake_fetcher(3))
    assert summary["counties"] == 10
    assert summary["total_funding"] == pytest.approx(700.0)
    assert summary["funding_per_eal_dollar_by_quintile"] == pytest.approx([3.0, 0.0, 0.0, 0.0, 0.5])
    assert summary["r_cov_most_vs_least_vulnerable"] == pytest.approx(0.5 / 3.0)
    assert summary["share_without_funding_by_quintile"] == pytest.approx([0.0, 1.0, 1.0, 1.0, 0.5])
    sources = json.loads((out / "sources.json").read_text())
    assert sources["projects_in_scope"] == 4
    assert sources["statewide_or_unknown_county_funding"] == pytest.approx(777.0)
    assert sources["nri_url"] == "https://example.test/nri.zip"
    assert sources["vulnerability_direction_checked"] is True
    xl = pd.ExcelFile(out / "phase-a.xlsx")
    assert xl.sheet_names == ["Quintiles", "Counties", "Project types", "Sources"]
    assert "most vulnerable" in (out / "report.md").read_text()


def test_run_refuses_reversed_vulnerability(config, tmp_path, monkeypatch):
    rows = [(f, p, r, c, -s, rt) for f, p, r, c, s, rt in NRI_ROWS]
    monkeypatch.setattr("tests.test_phase_a.NRI_ROWS", rows)
    with pytest.raises(ValueError):
        run(config, tmp_path / "out", fake_fetcher(3))


def test_missing_column_is_reported(config, tmp_path):
    bad = [{k: v for k, v in r.items() if k != "federalShareObligated"} for r in RECORDS]

    def f(url):
        if url.startswith("https://example.test/hma"):
            skip = int(url.split("$skip=")[1].split("&")[0])
            return json.dumps({"metadata": {}, "X": bad[skip:skip + 3]}).encode()
        return fake_fetcher(3)(url)

    with pytest.raises(KeyError, match="federalShareObligated"):
        run(config, tmp_path / "out", f)


def test_paging_stops_if_source_ignores_skip():
    page = json.dumps({"metadata": {}, "X": RECORDS[:3]}).encode()
    with pytest.raises(RuntimeError, match="twice"):
        openfema_records("https://example.test/hma", 3, lambda url: page)
