import json
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd

from thrive.data.download import Fetcher, arcgis_records, discover_openfema_endpoint, fetch, openfema_records, probe, sha256
from thrive.fairness import group_disparity

QUINTILE_LABELS = {1: "1 (least vulnerable)", 2: "2", 3: "3", 4: "4", 5: "5 (most vulnerable)"}
SUFFIXES = ("city and borough", "census area", "municipality", "municipio", "borough", "parish", "county")


def load_config(path: Path) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def pick(df: pd.DataFrame, candidates: Sequence[str], what: str, required: bool = True) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"none of {list(candidates)} found for {what}; columns are: {sorted(df.columns)}")
    return None


def normalize_state(name) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())


def normalize_county(name) -> tuple[str, bool]:
    text = str(name or "").lower().strip()
    text = re.sub(r"\(.*?\)", " ", text)
    wants_city = bool(re.search(r"\bcity\b", text)) and "city and borough" not in text
    text = re.sub(r"\bsaint\b|\bst\.", "st", text)
    for s in SUFFIXES:
        text = re.sub(rf"\b{s}\b", " ", text)
    if wants_city:
        text = re.sub(r"\bcity\b", " ", text)
    return re.sub(r"[^a-z0-9]", "", text), wants_city


def split_counties(text) -> list[str]:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return []
    parts = re.split(r";", str(text)) if ";" in str(text) else re.split(r",", str(text))
    return [p.strip() for p in parts if p.strip()]


class CountyIndex:
    def __init__(self, nri: pd.DataFrame):
        self.index: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for fips, state, county, ctype in zip(nri["fips"], nri["state"], nri["county"], nri["county_type"]):
            key = (normalize_state(state), normalize_county(county)[0])
            self.index.setdefault(key, []).append((fips, str(ctype or "").lower()))

    def resolve(self, state, token) -> str | None:
        name, wants_city = normalize_county(token)
        found = self.index.get((normalize_state(state), name), [])
        if len(found) == 1:
            return found[0][0]
        if len(found) > 1:
            pref = [f for f, t in found if (t == "city") == wants_city]
            if len(pref) == 1:
                return pref[0]
        return None


def prepare_nri(raw: pd.DataFrame, n: dict) -> tuple[pd.DataFrame, dict]:
    cols = {
        "fips": pick(raw, n["fips"], "FIPS"),
        "state": pick(raw, n["state"], "state"),
        "county": pick(raw, n["county"], "county"),
        "county_type": pick(raw, n["county_type"], "county type", required=False),
        "population": pick(raw, n["population"], "population"),
        "inland_eal": pick(raw, n["inland_eal"], "inland flood expected annual loss"),
        "coastal_eal": pick(raw, n["coastal_eal"], "coastal flood expected annual loss", required=False),
        "vulnerability": pick(raw, n["vulnerability"], "social vulnerability score"),
        "vulnerability_rating": pick(raw, n["vulnerability_rating"], "social vulnerability rating"),
        "version": pick(raw, n["version"], "NRI version", required=False),
    }
    num = lambda c: pd.to_numeric(raw[c], errors="coerce") if c else 0.0
    out = pd.DataFrame({
        "fips": raw[cols["fips"]].fillna("").astype(str).str.strip().str.zfill(5),
        "state": raw[cols["state"]].fillna("").astype(str),
        "county": raw[cols["county"]].fillna("").astype(str),
        "county_type": raw[cols["county_type"]].fillna("").astype(str) if cols["county_type"] else "",
        "population": num(cols["population"]),
        "flood_eal": num(cols["inland_eal"]).fillna(0.0) + (num(cols["coastal_eal"]).fillna(0.0) if cols["coastal_eal"] else 0.0),
        "vulnerability": num(cols["vulnerability"]),
        "vulnerability_rating": raw[cols["vulnerability_rating"]].fillna("").astype(str),
    })
    return out, cols


def check_vulnerability_direction(nri: pd.DataFrame) -> bool:
    med = nri.groupby("vulnerability_rating")["vulnerability"].median()
    high = [r for r in med.index if r.lower() == "very high"]
    low = [r for r in med.index if r.lower() == "very low"]
    return bool(high and low and med[high[0]] > med[low[0]])


def classify(hma: pd.DataFrame, o: dict, flood: dict) -> tuple[pd.DataFrame, dict]:
    cols = {
        "fiscal_year": pick(hma, o["fiscal_year"], "fiscal year"),
        "state": pick(hma, o["state"], "state"),
        "counties": pick(hma, o["counties"], "counties"),
        "amount": pick(hma, o["amount"], "amount"),
        "program": pick(hma, o["program"], "program", required=False),
        "status": pick(hma, o["status"], "status", required=False),
        "activity": pick(hma, o["activity"], "activity", required=False),
    }
    hazards = [c for c in o["hazards"] if c in hma.columns]
    if not hazards and not cols["program"]:
        raise KeyError(f"no hazard or program column to tell flood projects apart; columns are: {sorted(hma.columns)}")
    cols["hazards"] = hazards
    df = pd.DataFrame({
        "fiscal_year": pd.to_numeric(hma[cols["fiscal_year"]], errors="coerce"),
        "state": hma[cols["state"]],
        "counties": hma[cols["counties"]],
        "amount": pd.to_numeric(hma[cols["amount"]], errors="coerce").fillna(0.0),
        "program": hma[cols["program"]].fillna("").astype(str) if cols["program"] else "",
        "status": hma[cols["status"]].fillna("").astype(str) if cols["status"] else "",
        "activity": hma[cols["activity"]].fillna("").astype(str) if cols["activity"] else "",
    })
    word = flood["hazard_word"].lower()
    hazard_text = hma[hazards].fillna("").astype(str).agg(" ".join, axis=1).str.lower() if hazards else pd.Series([""] * len(hma), index=hma.index)
    df["flood"] = hazard_text.str.contains(word, regex=False) | df["program"].isin(flood["program_names"])
    status_key = df["status"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    excluded = {s.lower().replace(" ", "") for s in o["excluded_status"]}
    df["in_scope"] = df["flood"] & (df["fiscal_year"] >= int(o["first_fiscal_year"])) & ~status_key.isin(excluded) & (df["amount"] > 0)
    return df, cols


def allocate_to_counties(projects: pd.DataFrame, index: CountyIndex) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    rows, unmatched = [], []
    statewide = 0.0
    for state, counties, amount in projects.loc[projects["in_scope"], ["state", "counties", "amount"]].itertuples(index=False):
        tokens = split_counties(counties)
        if not tokens or any(t.lower() == "statewide" for t in tokens):
            statewide += amount
            continue
        share = amount / len(tokens)
        for t in tokens:
            fips = index.resolve(state, t)
            if fips:
                rows.append((fips, share))
            else:
                unmatched.append((str(state), t, share))
    funding = pd.DataFrame(rows, columns=["fips", "funding"]).groupby("fips", as_index=False).agg(funding=("funding", "sum"), projects=("funding", "size"))
    miss = pd.DataFrame(unmatched, columns=["state", "county as written", "funding"])
    if len(miss):
        miss = miss.groupby(["state", "county as written"], as_index=False)["funding"].sum().sort_values("funding", ascending=False)
    return funding, miss, statewide


def county_table(funding: pd.DataFrame, nri: pd.DataFrame) -> pd.DataFrame:
    df = nri.merge(funding, on="fips", how="left")
    df["funding"] = df["funding"].fillna(0.0)
    df["projects"] = df["projects"].fillna(0).astype(int)
    df = df[df["vulnerability"].notna() & (df["flood_eal"] > 0)].copy()
    df["quintile"] = pd.qcut(df["vulnerability"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["funding_per_eal_dollar"] = df["funding"] / df["flood_eal"]
    return df.sort_values("fips").reset_index(drop=True)


def quintile_table(counties: pd.DataFrame) -> pd.DataFrame:
    g = counties.groupby("quintile")
    t = pd.DataFrame({
        "counties": g.size(),
        "population": g["population"].sum(),
        "flood_eal": g["flood_eal"].sum(),
        "funding": g["funding"].sum(),
        "counties_without_funding": g["funding"].apply(lambda s: int((s <= 0).sum())),
    })
    t["funding_per_eal_dollar"] = t["funding"] / t["flood_eal"]
    t["funding_per_person"] = t["funding"] / t["population"]
    t["share_without_funding"] = t["counties_without_funding"] / t["counties"]
    t.index = [QUINTILE_LABELS[i] for i in t.index]
    t.index.name = "vulnerability quintile"
    return t


def summarise(counties: pd.DataFrame, quintiles: pd.DataFrame) -> dict:
    q = quintiles["funding_per_eal_dollar"].tolist()
    funded = (counties["funding"] > 0).astype(float).tolist()
    return {
        "counties": int(len(counties)),
        "total_funding": float(counties["funding"].sum()),
        "total_flood_eal": float(counties["flood_eal"].sum()),
        "funding_per_eal_dollar_by_quintile": [float(x) for x in q],
        "r_cov_most_vs_least_vulnerable": float(q[4] / q[0]) if q[0] > 0 else None,
        "share_without_funding_by_quintile": [float(x) for x in quintiles["share_without_funding"]],
        "disparity_in_any_funding": group_disparity(funded, counties["quintile"].tolist()),
    }


def report(summary: dict, sources: dict) -> str:
    q = summary["funding_per_eal_dollar_by_quintile"]
    lines = [
        "# Phase A: who gets flood protection in the United States?",
        "",
        "Generated automatically by `thrive phase-a`. `sources.json` records what was downloaded and when.",
        "",
        f"Counties with flood risk and a vulnerability score: {summary['counties']:,}.",
        f"Money counted: {sources['amount_field']} of flood-related FEMA Hazard Mitigation Assistance subgrants, fiscal year {sources['first_fiscal_year']} onwards, ${summary['total_funding'] / 1e9:,.2f} billion placed in counties.",
        f"Flood risk: expected annual loss from inland and coastal flooding, National Risk Index {sources.get('nri_version') or ''}.".replace("  ", " "),
        "",
        "| Vulnerability quintile | Money per dollar of expected annual flood loss | Counties with no flood money |",
        "| --- | --- | --- |",
    ]
    for label, v, z in zip(QUINTILE_LABELS.values(), q, summary["share_without_funding_by_quintile"]):
        lines.append(f"| {label} | ${v:,.2f} | {z:.0%} |")
    r = summary["r_cov_most_vs_least_vulnerable"]
    lines += ["", f"Coverage ratio, most vulnerable fifth against least vulnerable fifth: {r:.2f}." if r is not None else "Coverage ratio: not defined.", ""]
    lines += [
        f"Money that could not be placed in a county: statewide ${sources['statewide_funding'] / 1e6:,.1f} million, county name not matched ${sources['unmatched_funding'] / 1e6:,.1f} million ({sources['unmatched_share']:.1%} of the money in scope).",
        "",
        "Limits: a subgrant that names several counties is split equally between them, statewide subgrants are left out, money obligated is not always money spent, and expected annual loss is a model estimate. A subgrant counts as flood-related when one of its hazards mentions flooding or it comes from the Flood Mitigation Assistance programme.",
    ]
    return "\n".join(lines) + "\n"


def preflight(cfg: dict, out_dir: Path, fetcher: Fetcher) -> str:
    o, n = cfg["openfema"], cfg["nri"]
    checks = []
    try:
        endpoint = discover_openfema_endpoint(o["dataset"], o["catalog"], fetcher)
        checks.append({"check": "OpenFEMA catalog", "url": o["catalog"], "ok": True, "error": None, "found": endpoint})
    except Exception as exc:
        endpoint = o["endpoint"]
        checks.append({"check": "OpenFEMA catalog", "url": o["catalog"], "ok": False, "error": str(exc), "found": None})
    first = probe(f"{endpoint}?$top=1", fetcher)
    checks.append({"check": "OpenFEMA first record", **first})
    if not first["ok"] and endpoint != o["endpoint"]:
        alt = probe(f"{o['endpoint']}?$top=1", fetcher)
        checks.append({"check": "OpenFEMA configured endpoint", **alt})
        if alt["ok"]:
            endpoint, first = o["endpoint"], alt
    nri_url = f"{n['arcgis_query']}?where=1%3D1&outFields=*&resultRecordCount=1&returnGeometry=false&f=json"
    try:
        body = json.loads(fetcher(nri_url))
        ok = "error" not in body and bool(body.get("features"))
        nri = {"url": nri_url, "ok": ok, "error": None if ok else f"no features: {str(body)[:300]}"}
    except Exception as exc:
        nri = {"url": nri_url, "ok": False, "error": str(exc)}
    checks.append({"check": "National Risk Index", **nri})
    (out_dir / "preflight.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    problems = [c for c in checks if not c["ok"]]
    if not first["ok"] or not nri["ok"]:
        raise RuntimeError("preflight failed: " + " | ".join(f"{c['check']} {c['url']}: {c['error']}" for c in problems))
    return endpoint


def run(config_path: Path, out_dir: Path, fetcher: Fetcher = fetch) -> dict:
    cfg = load_config(config_path)
    o, n = cfg["openfema"], cfg["nri"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    endpoint = preflight(cfg, out_dir, fetcher)
    records, hma_digests = openfema_records(endpoint, int(o["page_size"]), fetcher)
    nri_rows, nri_digests = arcgis_records(n["arcgis_query"], int(n["page_size"]), fetcher)
    (out_dir / "sample.json").write_text(json.dumps({"openfema": records[:25], "nri": nri_rows[:3]}, indent=2, default=str) + "\n", encoding="utf-8")
    hma = pd.DataFrame.from_records(records)
    nri_raw = pd.DataFrame.from_records(nri_rows)
    nri, nri_cols = prepare_nri(nri_raw, n)
    if not check_vulnerability_direction(nri):
        raise ValueError("vulnerability score does not rise with its rating; refusing to rank counties")
    projects, hma_cols = classify(hma, o, cfg["flood"])
    funding, unmatched, statewide = allocate_to_counties(projects, CountyIndex(nri))
    counties = county_table(funding, nri)
    quintiles = quintile_table(counties)
    summary = summarise(counties, quintiles)
    in_scope_money = float(projects.loc[projects["in_scope"], "amount"].sum())
    unmatched_money = float(unmatched["funding"].sum()) if len(unmatched) else 0.0
    county_money = in_scope_money - statewide
    unmatched_share = unmatched_money / county_money if county_money > 0 else 0.0
    sources = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "openfema_endpoint": endpoint,
        "openfema_records": int(len(hma)),
        "openfema_pages_sha256": hma_digests,
        "openfema_columns": sorted(hma.columns.tolist()),
        "openfema_columns_used": hma_cols,
        "amount_field": hma_cols["amount"],
        "nri_source": n["arcgis_query"],
        "nri_records": int(len(nri_raw)),
        "nri_pages_sha256": nri_digests,
        "nri_columns_used": nri_cols,
        "nri_version": str(nri_raw[nri_cols["version"]].mode().iloc[0]) if nri_cols["version"] and len(nri_raw) else None,
        "first_fiscal_year": int(o["first_fiscal_year"]),
        "subgrants_in_scope": int(projects["in_scope"].sum()),
        "money_in_scope": in_scope_money,
        "statewide_funding": float(statewide),
        "unmatched_funding": unmatched_money,
        "unmatched_share": unmatched_share,
        "status_counts": {str(k): int(v) for k, v in projects["status"].value_counts().items()},
    }
    activities = projects.groupby(["activity", "flood"], dropna=False).agg(subgrants=("amount", "size"), amount=("amount", "sum")).reset_index().sort_values("amount", ascending=False)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(report(summary, sources), encoding="utf-8")
    with pd.ExcelWriter(out_dir / "phase-a.xlsx", engine="openpyxl") as xl:
        quintiles.to_excel(xl, sheet_name="Quintiles")
        counties.to_excel(xl, sheet_name="Counties", index=False)
        activities.to_excel(xl, sheet_name="Activities", index=False)
        (unmatched if len(unmatched) else pd.DataFrame(columns=["state", "county as written", "funding"])).to_excel(xl, sheet_name="Unmatched counties", index=False)
        pd.DataFrame([{"field": k, "value": json.dumps(v) if isinstance(v, (list, dict)) else v} for k, v in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    if unmatched_share > float(o["max_unmatched_share"]):
        raise ValueError(f"{unmatched_share:.0%} of the county money could not be matched to a county; see the 'Unmatched counties' sheet")
    return summary
