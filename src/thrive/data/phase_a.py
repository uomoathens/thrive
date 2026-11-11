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
        "fallback_amount": pick(hma, o.get("fallback_amount", []), "fallback amount", required=False),
        "identifier": pick(hma, o.get("identifier", []), "identifier", required=False),
        "title": pick(hma, o.get("title", []), "title", required=False),
        "program": pick(hma, o["program"], "program", required=False),
        "status": pick(hma, o["status"], "status"),
        "activity": pick(hma, o["activity"], "activity", required=False),
    }
    hazards = [c for c in o["hazards"] if c in hma.columns]
    if not hazards and not cols["program"] and not cols["activity"]:
        raise KeyError(f"no hazard, programme or activity column to tell flood projects apart; columns are: {sorted(hma.columns)}")
    cols["hazards"] = hazards
    text = lambda c: hma[c].fillna("").astype(str) if c else pd.Series([""] * len(hma), index=hma.index)
    primary = pd.to_numeric(hma[cols["amount"]], errors="coerce")
    fallback = pd.to_numeric(hma[cols["fallback_amount"]], errors="coerce") if cols["fallback_amount"] else pd.Series([float("nan")] * len(hma), index=hma.index)
    use_fallback = ~(primary > 0) & (fallback > 0)
    df = pd.DataFrame({
        "identifier": text(cols["identifier"]),
        "title": text(cols["title"]),
        "fiscal_year": pd.to_numeric(hma[cols["fiscal_year"]], errors="coerce"),
        "state": hma[cols["state"]],
        "counties": hma[cols["counties"]],
        "amount": primary.where(primary > 0, fallback).fillna(0.0),
        "amount_from_fallback": use_fallback,
        "program": text(cols["program"]),
        "status": text(cols["status"]),
        "activity": text(cols["activity"]),
        "hazards": hma[hazards].fillna("").astype(str).agg(" | ".join, axis=1) if hazards else "",
    })
    word = flood["hazard_word"].lower()
    by_hazard = df["hazards"].str.lower().str.contains(word, regex=False) if hazards else False
    by_program = df["program"].isin(flood["program_names"])
    activity = df["activity"].str.lower()
    by_activity = pd.Series(False, index=df.index)
    for w in flood.get("activity_words", []):
        by_activity |= activity.str.contains(w.lower(), regex=False)
    df["flood"] = by_hazard | by_program | by_activity
    df["flood_reason"] = [
        "hazard" if h else ("programme" if p else ("activity" if a else ""))
        for h, p, a in zip(by_hazard if hazards else [False] * len(df), by_program, by_activity)
    ]
    status_key = df["status"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    funded = {x.lower().replace(" ", "") for x in o["funded_status"]}
    df["funded_status"] = status_key.isin(funded)
    df["in_scope"] = df["flood"] & (df["fiscal_year"] >= int(o["first_fiscal_year"])) & df["funded_status"] & (df["amount"] > 0)
    return df, cols


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    keyed = df["identifier"] != ""
    dup = df[keyed].duplicated("identifier", keep=False)
    n = int(dup.sum())
    if not n:
        return df, 0
    best = df[keyed].sort_values("amount", ascending=False).drop_duplicates("identifier", keep="first")
    return pd.concat([best, df[~keyed]]).sort_index(), n


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


def robustness(counties: pd.DataFrame, leave_out: int) -> dict:
    total = counties["funding"].sum()
    largest = counties.nlargest(leave_out, "funding")
    rest = counties.drop(largest.index)
    g = rest.groupby("quintile")
    q_rest = (g["funding"].sum() / g["flood_eal"].sum()).reindex([1, 2, 3, 4, 5]).tolist()
    med = counties.groupby("quintile")["funding_per_eal_dollar"].median().reindex([1, 2, 3, 4, 5]).tolist()
    funded = counties[counties["funding"] > 0]
    med_funded = funded.groupby("quintile")["funding_per_eal_dollar"].median().reindex([1, 2, 3, 4, 5]).tolist()
    ratio = lambda q: float(q[4] / q[0]) if q[0] and q[0] > 0 else None
    return {
        "share_of_money_in_largest_counties": float(largest["funding"].sum() / total) if total > 0 else 0.0,
        "largest_counties_left_out": int(leave_out),
        "largest_counties": [f"{r.county}, {r.state}" for r in largest.itertuples()],
        "funding_per_eal_dollar_by_quintile_without_largest": [float(x) for x in q_rest],
        "r_cov_without_largest": ratio(q_rest),
        "median_county_ratio_by_quintile": [float(x) for x in med],
        "r_cov_median_county": ratio(med),
        "median_ratio_of_funded_counties_by_quintile": [float(x) for x in med_funded],
        "r_cov_median_funded_county": ratio(med_funded),
    }


def summarise(counties: pd.DataFrame, quintiles: pd.DataFrame, leave_out: int = 20) -> dict:
    q = quintiles["funding_per_eal_dollar"].tolist()
    funded = (counties["funding"] > 0).astype(float).tolist()
    out = {
        "counties": int(len(counties)),
        "total_funding": float(counties["funding"].sum()),
        "total_flood_eal": float(counties["flood_eal"].sum()),
        "funding_per_eal_dollar_by_quintile": [float(x) for x in q],
        "r_cov_most_vs_least_vulnerable": float(q[4] / q[0]) if q[0] > 0 else None,
        "share_without_funding_by_quintile": [float(x) for x in quintiles["share_without_funding"]],
        "disparity_in_any_funding": group_disparity(funded, counties["quintile"].tolist()),
    }
    out["robustness"] = robustness(counties, leave_out)
    measures = [out["r_cov_most_vs_least_vulnerable"], out["robustness"]["r_cov_without_largest"], out["robustness"]["r_cov_median_county"], out["robustness"]["r_cov_median_funded_county"]]
    known = [m for m in measures if m is not None]
    out["robust_direction"] = "more for the most vulnerable" if known and all(m > 1 for m in known) else ("less for the most vulnerable" if known and all(m < 1 for m in known) else "not robust")
    return out


def _ratio(x) -> str:
    return "not defined" if x is None else f"{x:.2f}"


def report(summary: dict, sources: dict) -> str:
    q = summary["funding_per_eal_dollar_by_quintile"]
    rb = summary["robustness"]
    lines = [
        "# Phase A: who gets flood protection in the United States?",
        "",
        "Generated automatically by `thrive phase-a`. `sources.json` records what was downloaded and when.",
        "",
        f"Counties with flood risk and a vulnerability score: {summary['counties']:,}.",
        f"Money counted: flood-related FEMA Hazard Mitigation Assistance grants with a funded status, fiscal year {sources['first_fiscal_year']} onwards, ${summary['total_funding'] / 1e9:,.2f} billion placed in counties. Where a grant has no obligated amount, its federal share is used (${sources['money_from_fallback'] / 1e9:,.2f} billion).",
        f"Flood risk: expected annual loss from inland and coastal flooding, National Risk Index {sources.get('nri_version') or ''}.".replace("  ", " "),
        "",
        "| Vulnerability quintile | Money per dollar of expected annual flood loss | Same, without the largest counties | Median county | Counties with no flood money |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label, v, w, m, z in zip(QUINTILE_LABELS.values(), q, rb["funding_per_eal_dollar_by_quintile_without_largest"], rb["median_county_ratio_by_quintile"], summary["share_without_funding_by_quintile"]):
        lines.append(f"| {label} | ${v:,.3f} | ${w:,.3f} | ${m:,.3f} | {z:.0%} |")
    lines += [
        "",
        "Coverage ratio, most vulnerable fifth against least vulnerable fifth:",
        "",
        f"- all money: {_ratio(summary['r_cov_most_vs_least_vulnerable'])}",
        f"- without the {rb['largest_counties_left_out']} counties that received the most ({rb['share_of_money_in_largest_counties']:.0%} of all the money): {_ratio(rb['r_cov_without_largest'])}",
        f"- median county: {_ratio(rb['r_cov_median_county'])}",
        f"- median county among those that received any flood money: {_ratio(rb['r_cov_median_funded_county'])}",
        "",
        f"Direction across all four measures: **{summary['robust_direction']}**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.",
        "",
        f"Money that could not be placed in a county: statewide ${sources['statewide_funding'] / 1e6:,.1f} million, county name not matched ${sources['unmatched_funding'] / 1e6:,.1f} million ({sources['unmatched_share']:.1%} of the money meant for named counties).",
        "",
        "Limits: a grant that names several counties is split equally between them, statewide grants are left out, money obligated is not always money spent, and expected annual loss is a model estimate. A grant counts as flood-related when one of its hazards mentions flooding, it comes from the Flood Mitigation Assistance programme, or its main activity is a flood measure (acquisition, elevation, flood control, floodproofing, drainage). The Excel file lists the largest grants so that any of them can be checked by hand.",
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
    projects, duplicates = drop_duplicates(projects)
    funding, unmatched, statewide = allocate_to_counties(projects, CountyIndex(nri))
    counties = county_table(funding, nri)
    quintiles = quintile_table(counties)
    summary = summarise(counties, quintiles, int(o.get("largest_counties_left_out", 20)))
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
        "funded_status": list(o["funded_status"]),
        "duplicate_identifier_rows": duplicates,
        "money_from_fallback": float(projects.loc[projects["in_scope"] & projects["amount_from_fallback"], "amount"].sum()),
        "flood_reason_money": {str(k): float(v) for k, v in projects[projects["in_scope"]].groupby("flood_reason")["amount"].sum().items()},
    }
    activities = projects.groupby(["activity", "flood", "flood_reason"], dropna=False).agg(subgrants=("amount", "size"), amount=("amount", "sum")).reset_index().sort_values("amount", ascending=False)
    largest = projects[projects["in_scope"]].nlargest(200, "amount")[["identifier", "fiscal_year", "state", "counties", "amount", "amount_from_fallback", "status", "program", "hazards", "activity", "flood_reason", "title"]]
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(report(summary, sources), encoding="utf-8")
    with pd.ExcelWriter(out_dir / "phase-a.xlsx", engine="openpyxl") as xl:
        quintiles.to_excel(xl, sheet_name="Quintiles")
        counties.to_excel(xl, sheet_name="Counties", index=False)
        activities.to_excel(xl, sheet_name="Activities", index=False)
        largest.to_excel(xl, sheet_name="Largest grants", index=False)
        (unmatched if len(unmatched) else pd.DataFrame(columns=["state", "county as written", "funding"])).to_excel(xl, sheet_name="Unmatched counties", index=False)
        pd.DataFrame([{"field": k, "value": json.dumps(v) if isinstance(v, (list, dict)) else v} for k, v in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    if unmatched_share > float(o["max_unmatched_share"]):
        raise ValueError(f"{unmatched_share:.0%} of the county money could not be matched to a county; see the 'Unmatched counties' sheet")
    return summary
