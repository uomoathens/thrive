import io
import json
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd

from thrive.data.download import Fetcher, discover_openfema_endpoint, fetch, openfema_records, probe, sha256, zip_member
from thrive.fairness import group_disparity

REQUIRED_HMA = ("programArea", "programFy", "stateNumberCode", "countyCode", "projectType", "status", "federalShareObligated")
QUINTILE_LABELS = {1: "1 (least vulnerable)", 2: "2", 3: "3", 4: "4", 5: "5 (most vulnerable)"}

@dataclass(frozen=True)
class Config:
    dataset: str
    catalog: str
    endpoint: str
    page_size: int
    first_fiscal_year: int
    excluded_status: tuple[str, ...]
    nri_urls: tuple[str, ...]
    nri_member: str
    nri_columns: dict[str, tuple[str, ...]]
    flood_program_areas: tuple[str, ...]
    flood_words: tuple[str, ...]

def load_config(path: Path) -> Config:
    c = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    o, n, f = c["openfema"], c["nri"], c["flood"]
    keys = ("fips", "population", "riverine_eal", "coastal_eal", "vulnerability", "vulnerability_rating")
    return Config(
        dataset=o["dataset"],
        catalog=o["catalog"],
        endpoint=o["endpoint"],
        page_size=int(o["page_size"]),
        first_fiscal_year=int(o["first_fiscal_year"]),
        excluded_status=tuple(o["excluded_status"]),
        nri_urls=tuple(n["urls"]),
        nri_member=n["member"],
        nri_columns={k: tuple(n[k]) for k in keys},
        flood_program_areas=tuple(f["program_areas"]),
        flood_words=tuple(w.lower() for w in f["words"]),
    )

def is_flood_project(program_area: str | None, project_type: str | None, program_areas: Sequence[str], words: Sequence[str]) -> bool:
    if program_area in program_areas:
        return True
    text = (project_type or "").lower()
    return any(w in text for w in words)

def county_fips(state_code, county_code) -> str | None:
    try:
        s, c = int(str(state_code).strip()), int(str(county_code).strip())
    except (TypeError, ValueError):
        return None
    if c == 0:
        return None
    return f"{s:02d}{c:03d}"

def pick(df: pd.DataFrame, candidates: Sequence[str], what: str) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"none of {list(candidates)} found for {what}; columns are: {list(df.columns)}")

def classify_projects(hma: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    missing = [c for c in REQUIRED_HMA if c not in hma.columns]
    if missing:
        raise KeyError(f"OpenFEMA columns missing: {missing}; columns are: {list(hma.columns)}")
    df = hma.copy()
    df["federalShareObligated"] = pd.to_numeric(df["federalShareObligated"], errors="coerce").fillna(0.0)
    df["programFy"] = pd.to_numeric(df["programFy"], errors="coerce")
    df["fips"] = [county_fips(s, c) for s, c in zip(df["stateNumberCode"], df["countyCode"])]
    df["flood"] = [is_flood_project(a, t, cfg.flood_program_areas, cfg.flood_words) for a, t in zip(df["programArea"], df["projectType"])]
    df["in_scope"] = df["flood"] & (df["programFy"] >= cfg.first_fiscal_year) & ~df["status"].isin(cfg.excluded_status) & (df["federalShareObligated"] > 0)
    return df

def county_funding(projects: pd.DataFrame) -> pd.DataFrame:
    scoped = projects[projects["in_scope"] & projects["fips"].notna()]
    return scoped.groupby("fips").agg(funding=("federalShareObligated", "sum"), projects=("federalShareObligated", "size")).reset_index()

def prepare_nri(nri: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, dict[str, str]]:
    cols = {k: pick(nri, v, k) for k, v in cfg.nri_columns.items() if k != "coastal_eal"}
    coastal = next((c for c in cfg.nri_columns["coastal_eal"] if c in nri.columns), None)
    if coastal:
        cols["coastal_eal"] = coastal
    out = pd.DataFrame({
        "fips": nri[cols["fips"]].astype(str).str.strip().str.zfill(5),
        "population": pd.to_numeric(nri[cols["population"]], errors="coerce"),
        "flood_eal": pd.to_numeric(nri[cols["riverine_eal"]], errors="coerce").fillna(0.0)
        + (pd.to_numeric(nri[coastal], errors="coerce").fillna(0.0) if coastal else 0.0),
        "vulnerability": pd.to_numeric(nri[cols["vulnerability"]], errors="coerce"),
        "vulnerability_rating": nri[cols["vulnerability_rating"]].astype(str),
    })
    return out, cols

def check_vulnerability_direction(nri: pd.DataFrame) -> bool:
    med = nri.groupby("vulnerability_rating")["vulnerability"].median()
    high = [r for r in med.index if r.lower() == "very high"]
    low = [r for r in med.index if r.lower() == "very low"]
    if not high or not low:
        return False
    return bool(med[high[0]] > med[low[0]])

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

def _report(summary: dict, sources: dict) -> str:
    q = summary["funding_per_eal_dollar_by_quintile"]
    lines = [
        "# Phase A: who gets flood protection in the United States?",
        "",
        "Generated automatically by `thrive phase-a`. Check `sources.json` for what was downloaded and when.",
        "",
        f"Counties with flood risk and a vulnerability score: {summary['counties']:,}.",
        f"FEMA flood-mitigation funding counted (federal share obligated, fiscal year {sources['first_fiscal_year']} onwards): ${summary['total_funding'] / 1e9:,.2f} billion.",
        "",
        "| Vulnerability quintile | Funding per dollar of expected annual flood loss | Counties with no flood funding |",
        "| --- | --- | --- |",
    ]
    for label, v, z in zip(QUINTILE_LABELS.values(), q, summary["share_without_funding_by_quintile"]):
        lines.append(f"| {label} | ${v:,.2f} | {z:.0%} |")
    r = summary["r_cov_most_vs_least_vulnerable"]
    lines += ["", f"Coverage ratio, most vulnerable fifth against least vulnerable fifth: {r:.2f}." if r is not None else "Coverage ratio: not defined.", ""]
    lines += [
        "Limits: funding is counted in the primary county of each project, statewide projects are left out, obligated money is not necessarily spent, and expected annual loss is a model estimate from the National Risk Index. A project counts as flood-related by the rule in `config/phase-a.toml`; `phase-a.xlsx` lists every project type and how it was classified.",
    ]
    return "\n".join(lines) + "\n"

def preflight(cfg: Config, out_dir: Path, fetcher: Fetcher) -> tuple[str, str, bytes]:
    checks = []
    try:
        endpoint = discover_openfema_endpoint(cfg.dataset, cfg.catalog, fetcher)
        checks.append({"check": "OpenFEMA catalog", "url": cfg.catalog, "ok": True, "error": None, "found": endpoint})
    except Exception as exc:
        endpoint = cfg.endpoint
        checks.append({"check": "OpenFEMA catalog", "url": cfg.catalog, "ok": False, "error": str(exc), "found": None})
    first = probe(f"{endpoint}?$top=1", fetcher)
    checks.append({"check": "OpenFEMA first record", **first})
    if not first["ok"] and endpoint != cfg.endpoint:
        alt = probe(f"{cfg.endpoint}?$top=1", fetcher)
        checks.append({"check": "OpenFEMA configured endpoint", **alt})
        if alt["ok"]:
            endpoint = cfg.endpoint
            first = alt
    nri_url, nri_zip = None, None
    for url in cfg.nri_urls:
        try:
            data = fetcher(url)
            zip_member(data, cfg.nri_member)
            checks.append({"check": "National Risk Index", "url": url, "ok": True, "bytes": len(data), "error": None})
            nri_url, nri_zip = url, data
            break
        except Exception as exc:
            checks.append({"check": "National Risk Index", "url": url, "ok": False, "bytes": 0, "error": str(exc)})
    (out_dir / "preflight.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    problems = [c for c in checks if not c["ok"]]
    if not first["ok"] or nri_zip is None:
        raise RuntimeError("preflight failed: " + " | ".join(f"{c['check']} {c['url']}: {c['error']}" for c in problems))
    return endpoint, nri_url, nri_zip


def run(config_path: Path, out_dir: Path, fetcher: Fetcher = fetch) -> dict:
    cfg = load_config(config_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    endpoint, nri_url, nri_zip = preflight(cfg, out_dir, fetcher)
    records, digests = openfema_records(endpoint, cfg.page_size, fetcher)
    hma = pd.DataFrame.from_records(records)
    nri_raw = pd.read_csv(io.BytesIO(zip_member(nri_zip, cfg.nri_member)), dtype=str, low_memory=False)
    nri, nri_cols = prepare_nri(nri_raw, cfg)
    direction_ok = check_vulnerability_direction(nri)
    if not direction_ok:
        raise ValueError("vulnerability score does not rise with its rating; refusing to rank counties")
    projects = classify_projects(hma, cfg)
    funding = county_funding(projects)
    counties = county_table(funding, nri)
    quintiles = quintile_table(counties)
    summary = summarise(counties, quintiles)
    unmatched = sorted(set(funding["fips"]) - set(nri["fips"]))
    sources = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "openfema_endpoint": endpoint,
        "openfema_records": int(len(hma)),
        "openfema_pages_sha256": digests,
        "openfema_columns": sorted(hma.columns.tolist()),
        "nri_url": nri_url,
        "nri_sha256": sha256(nri_zip),
        "nri_rows": int(len(nri_raw)),
        "nri_columns_used": nri_cols,
        "vulnerability_direction_checked": direction_ok,
        "first_fiscal_year": cfg.first_fiscal_year,
        "flood_rule": {"program_areas": list(cfg.flood_program_areas), "words": list(cfg.flood_words)},
        "projects_in_scope": int(projects["in_scope"].sum()),
        "statewide_or_unknown_county_funding": float(projects.loc[projects["in_scope"] & projects["fips"].isna(), "federalShareObligated"].sum()),
        "funded_counties_not_in_nri": unmatched,
        "status_counts": {str(k): int(v) for k, v in projects["status"].value_counts().items()},
    }
    types = projects.groupby(["projectType", "flood"]).agg(projects=("federalShareObligated", "size"), funding=("federalShareObligated", "sum")).reset_index().sort_values("funding", ascending=False)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(_report(summary, sources), encoding="utf-8")
    with pd.ExcelWriter(out_dir / "phase-a.xlsx", engine="openpyxl") as xl:
        quintiles.to_excel(xl, sheet_name="Quintiles")
        counties.to_excel(xl, sheet_name="Counties", index=False)
        types.to_excel(xl, sheet_name="Project types", index=False)
        pd.DataFrame([{"field": k, "value": json.dumps(v) if isinstance(v, (list, dict)) else v} for k, v in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    return summary
