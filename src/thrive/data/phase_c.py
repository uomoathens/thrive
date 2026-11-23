import io
import json
import tempfile
import tomllib
import urllib.parse
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from thrive.data.download import Fetcher, fetch, fetch_to_file, sha256

HORIZONS = ("year before", "fire year", "year after", "two years after")


def load_config(path: Path) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def eurostat_url(template: str, code: str, filters: dict, since: int) -> str:
    params = [("format", "JSON"), ("lang", "EN"), ("sinceTimePeriod", str(since))]
    for key, value in filters.items():
        for v in value if isinstance(value, (list, tuple)) else [value]:
            params.append((key, str(v)))
    return template.format(code=code) + "?" + urllib.parse.urlencode(params)


def jsonstat_frame(raw: bytes) -> tuple[pd.DataFrame, dict]:
    payload = json.loads(raw)
    ids, sizes = payload["id"], payload["size"]
    if len(ids) != len(sizes):
        raise ValueError("JSON-stat response has mismatched id and size")
    codes = []
    for dim in ids:
        index = payload["dimension"][dim]["category"]["index"]
        ordered = sorted(index, key=index.get) if isinstance(index, dict) else list(index)
        codes.append(ordered)
    labels = {dim: payload["dimension"][dim]["category"].get("label", {}) for dim in ids}
    values = payload.get("value", {})
    items = values.items() if isinstance(values, dict) else ((i, v) for i, v in enumerate(values) if v is not None)
    rows = []
    strides = np.cumprod([1] + sizes[::-1][:-1])[::-1]
    for key, value in items:
        if value is None:
            continue
        pos = int(key)
        row = {}
        for dim, stride, size, cats in zip(ids, strides, sizes, codes):
            row[dim] = cats[(pos // int(stride)) % size]
        row["value"] = float(value)
        rows.append(row)
    frame = pd.DataFrame(rows, columns=list(ids) + ["value"])
    meta = {"updated": payload.get("updated"), "label": payload.get("label"), "geo_labels": labels.get("geo", {})}
    return frame, meta


def _single(frame: pd.DataFrame, keep) -> pd.DataFrame:
    for col in frame.columns:
        if col in keep or col == "value":
            continue
        if frame[col].nunique() > 1:
            raise ValueError(f"Eurostat dimension {col} has more than one category: {sorted(frame[col].unique())}")
    return frame


def greek_nuts(frame: pd.DataFrame, country: str, level: int) -> pd.DataFrame:
    geo = frame["geo"].astype(str)
    mask = geo.str.startswith(country) & (geo.str.len() == len(country) + level) & ~geo.str.endswith("Z")
    return frame[mask].copy()


def eurostat_tables(cfg: dict, fetcher: Fetcher = fetch) -> dict:
    e = cfg["eurostat"]
    sectors = [s["key"] for s in cfg["sector"]]
    since = int(e["since"])
    out = {"urls": {}, "sha256": {}, "updated": {}}

    def get(name, code, filters):
        url = eurostat_url(e["api"], code, filters, since)
        raw = fetcher(url)
        out["urls"][name] = url
        out["sha256"][name] = sha256(raw)
        frame, meta = jsonstat_frame(raw)
        out["updated"][name] = meta["updated"]
        return frame, meta

    gva, gmeta = get("gva", e["gva"]["code"], {"unit": e["gva"]["unit"], "nace_r2": sectors + [e["gva"]["total"]]})
    gva = _single(gva, {"geo", "time", "nace_r2"})
    pop, _ = get("population", e["population"]["code"], {"unit": e["population"]["unit"]})
    pop = _single(pop, {"geo", "time"})
    vol, _ = get("volume", e["volume"]["code"], {"unit": e["volume"]["unit"], "na_item": e["volume"]["na_item"]})
    vol = _single(vol, {"geo", "time"})
    country = e["country"]
    out["gva3"] = greek_nuts(gva[gva["nace_r2"].isin(sectors)], country, 3)
    out["gva2_total"] = greek_nuts(gva[gva["nace_r2"] == e["gva"]["total"]], country, 2)
    out["pop3"] = greek_nuts(pop, country, 3)
    out["vol2"] = greek_nuts(vol, country, 2)
    out["geo_labels"] = gmeta["geo_labels"]
    return out


def tourism_table(cfg: dict, fetcher: Fetcher = fetch) -> dict:
    e, t = cfg["eurostat"], cfg["tourism"]
    url = eurostat_url(e["api"], t["code"], {"unit": t["unit"], "nace_r2": t["nace_r2"], "c_resid": t["residence"]}, int(e["since"]))
    raw = fetcher(url)
    frame, meta = jsonstat_frame(raw)
    frame = _single(frame, {"geo", "time", "c_resid"})
    return {"url": url, "sha256": sha256(raw), "updated": meta["updated"], "nights": greek_nuts(frame, e["country"], 3)}


def nights_growth(nights: pd.DataFrame) -> pd.DataFrame:
    n = nights.assign(year=nights["time"].astype(int)).pivot_table(index=["geo", "c_resid"], columns="year", values="value")
    rows = []
    for (geo, resid), series in n.iterrows():
        for year in series.index:
            prev = year - 1
            if prev not in series.index or not np.isfinite(series[year]) or not np.isfinite(series[prev]) or series[prev] <= 0:
                continue
            rows.append({"region_id": geo, "sector": resid, "year": int(year), "nights": float(series[year]), "growth_nights": (series[year] / series[prev] - 1.0) * 100.0})
    return pd.DataFrame(rows, columns=["region_id", "sector", "year", "nights", "growth_nights"])


def growth_panel(gva3: pd.DataFrame, pop3: pd.DataFrame, gva2_total: pd.DataFrame, vol2: pd.DataFrame) -> pd.DataFrame:
    g = gva3.assign(year=gva3["time"].astype(int)).pivot_table(index=["geo", "nace_r2"], columns="year", values="value")
    p = pop3.assign(year=pop3["time"].astype(int)).pivot_table(index="geo", columns="year", values="value")
    n2 = gva2_total.assign(year=gva2_total["time"].astype(int)).pivot_table(index="geo", columns="year", values="value")
    v2 = vol2.assign(year=vol2["time"].astype(int)).pivot_table(index="geo", columns="year", values="value")
    rows = []
    for (geo, sector), series in g.iterrows():
        nuts2 = geo[:4]
        for year in series.index:
            prev = year - 1
            if prev not in series.index:
                continue
            try:
                nom = series[year] / series[prev]
                pop_ratio = p.loc[geo, year] / p.loc[geo, prev]
                defl = (n2.loc[nuts2, year] / n2.loc[nuts2, prev]) / (v2.loc[nuts2, year] / v2.loc[nuts2, prev])
            except KeyError:
                continue
            if not np.all(np.isfinite([nom, pop_ratio, defl])) or series[prev] <= 0:
                continue
            rows.append({
                "region_id": geo,
                "sector": sector,
                "year": int(year),
                "growth_real": (nom / defl / pop_ratio - 1.0) * 100.0,
                "growth_nominal": (nom / pop_ratio - 1.0) * 100.0,
                "deflator_change": (defl - 1.0) * 100.0,
            })
    return pd.DataFrame(rows, columns=["region_id", "sector", "year", "growth_real", "growth_nominal", "deflator_change"])


def _find(columns, names):
    lower = {c.lower(): c for c in columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def region_polygons(geojson: bytes, country: str, crs: int):
    import geopandas as gpd

    gdf = gpd.read_file(io.BytesIO(geojson))
    col = "NUTS_ID" if "NUTS_ID" in gdf.columns else "id"
    name = next((c for c in ("NAME_LATN", "NUTS_NAME", "NAME") if c in gdf.columns), col)
    gdf = gdf.rename(columns={col: "region_id", name: "region_name"})[["region_id", "region_name", "geometry"]]
    gdf["region_id"] = gdf["region_id"].astype(str)
    gdf = gdf[gdf["region_id"].str.startswith(country)].to_crs(crs).reset_index(drop=True)
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf["area_ha"] = gdf.geometry.area / 1e4
    return gdf


def fire_polygons(path: Path, cfg_effis: dict, regions, crs: int):
    import geopandas as gpd
    import pyogrio

    layer_crs = pyogrio.read_info(path).get("crs")
    if not layer_crs:
        raise ValueError("the EFFIS layer has no coordinate reference system")
    box_in_layer = tuple(regions.to_crs(layer_crs).total_bounds)
    gdf = gpd.read_file(path, bbox=box_in_layer)
    if gdf.crs is None:
        gdf = gdf.set_crs(layer_crs)
    columns = [c for c in gdf.columns if c != "geometry"]
    date_col = _find(columns, cfg_effis["date_fields"])
    if date_col is None:
        raise ValueError(f"no fire date field among {cfg_effis['date_fields']}; the layer has {columns}")
    id_col = _find(columns, cfg_effis["id_fields"])
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(crs)
    minx, miny, maxx, maxy = regions.total_bounds
    gdf = gdf.cx[minx:maxx, miny:maxy].copy()
    dates = pd.to_datetime(gdf[date_col].astype(str), errors="coerce", format="mixed")
    info = {"fields": columns, "date_field": date_col, "id_field": id_col, "features_in_box": int(len(gdf)), "unparsed_dates": int(dates.isna().sum())}
    gdf["fire_id"] = gdf[id_col].astype(str) if id_col else pd.Series(range(len(gdf)), index=gdf.index).astype(str)
    gdf["fire_date"] = dates
    gdf["fire_year"] = dates.dt.year
    gdf["geometry"] = gdf.geometry.make_valid()
    return gdf[["fire_id", "fire_date", "fire_year", "geometry"]], info


def burnt_by_region(fires, regions) -> pd.DataFrame:
    import geopandas as gpd

    fires = fires[fires["fire_year"].notna()]
    pairs = gpd.sjoin(fires, regions[["region_id", "geometry"]], how="inner", predicate="intersects")
    rows = []
    for idx, row in pairs.iterrows():
        geom = fires.geometry.loc[idx]
        region_geom = regions.loc[row["index_right"], "geometry"]
        ha = geom.intersection(region_geom).area / 1e4
        if ha > 0:
            rows.append({"fire_id": row["fire_id"], "fire_date": row["fire_date"], "year": int(row["fire_year"]), "region_id": row["region_id"], "burnt_ha": ha})
    return pd.DataFrame(rows, columns=["fire_id", "fire_date", "year", "region_id", "burnt_ha"])


def exposure_table(burnt: pd.DataFrame, regions, years) -> pd.DataFrame:
    grid = pd.MultiIndex.from_product([regions["region_id"], list(years)], names=["region_id", "year"]).to_frame(index=False)
    agg = burnt.groupby(["region_id", "year"]).agg(burnt_ha=("burnt_ha", "sum"), fires=("fire_id", "nunique")).reset_index()
    out = grid.merge(agg, on=["region_id", "year"], how="left").fillna({"burnt_ha": 0.0, "fires": 0})
    out = out.merge(regions[["region_id", "region_name", "area_ha"]], on="region_id", how="left")
    out["share_pct"] = out["burnt_ha"] / out["area_ha"] * 100.0
    out["fires"] = out["fires"].astype(int)
    return out[["region_id", "region_name", "year", "burnt_ha", "area_ha", "share_pct", "fires"]]


def _t_pvalue(t: float, df: int) -> float:
    from scipy import stats

    return float(2.0 * stats.t.sf(abs(t), df))


def event_study(growth: pd.DataFrame, exposure: pd.DataFrame, sector: str, measure: str, first: int, last: int, leads: int = 1, lags: int = 2) -> dict:
    x = exposure.pivot_table(index="region_id", columns="year", values="share_pct")
    data = growth[(growth["sector"] == sector) & growth["year"].between(first, last)].dropna(subset=[measure])
    ks = list(range(-leads, lags + 1))
    rows, y, reg, yr = [], [], [], []
    for _, r in data.iterrows():
        try:
            vals = [x.loc[r["region_id"], r["year"] - k] for k in ks]
        except KeyError:
            continue
        if not np.all(np.isfinite(vals)):
            continue
        rows.append(vals)
        y.append(r[measure])
        reg.append(r["region_id"])
        yr.append(int(r["year"]))
    if not rows:
        raise ValueError(f"no observations for sector {sector}")
    reg_codes = sorted(set(reg))
    years = sorted(set(yr))
    slopes = np.asarray(rows, dtype=float)
    rd = np.zeros((len(rows), len(reg_codes)))
    rd[np.arange(len(rows)), [reg_codes.index(r) for r in reg]] = 1.0
    yd = np.zeros((len(rows), len(years) - 1))
    for i, t in enumerate(yr):
        j = years.index(t)
        if j > 0:
            yd[i, j - 1] = 1.0
    X = np.hstack([slopes, rd, yd])
    Y = np.asarray(y, dtype=float)
    n, p = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ Y
    resid = Y - X @ beta
    meat = np.zeros((p, p))
    reg_arr = np.asarray(reg)
    for g in reg_codes:
        idx = reg_arr == g
        s = X[idx].T @ resid[idx]
        meat += np.outer(s, s)
    groups = len(reg_codes)
    k_eff = slopes.shape[1] + yd.shape[1]
    scale = groups / (groups - 1) * (n - 1) / (n - k_eff)
    vcov = xtx_inv @ meat @ xtx_inv * scale
    m = slopes.shape[1]
    b = beta[:m]
    se = np.sqrt(np.clip(np.diag(vcov)[:m], 0, None))
    cum_idx = [ks.index(k) for k in ks if k >= 0]
    a = np.zeros(m)
    a[cum_idx] = 1.0
    cum = float(a @ b)
    cum_se = float(np.sqrt(max(a @ vcov[:m, :m] @ a, 0.0)))
    df = groups - 1
    names = [HORIZONS[ks.index(k)] if ks.index(k) < len(HORIZONS) else f"t{k:+d}" for k in ks]
    return {
        "sector": sector,
        "measure": measure,
        "horizons": names,
        "coef": [float(v) for v in b],
        "se": [float(v) for v in se],
        "p": [_t_pvalue(bv / sv, df) if sv > 0 else None for bv, sv in zip(b, se)],
        "cumulative": cum,
        "cumulative_se": cum_se,
        "cumulative_p": _t_pvalue(cum / cum_se, df) if cum_se > 0 else None,
        "observations": int(n),
        "regions": groups,
        "years": years,
    }


def burnt_check(exposure: pd.DataFrame, cfg_val: dict) -> pd.DataFrame:
    tol = cfg_val["tolerance"]
    rows = []
    for item in cfg_val.get("burnt", []):
        hit = exposure[(exposure["region_id"] == item["region_id"]) & (exposure["year"] == item["year"])]
        name = hit["region_name"].iloc[0] if not hit.empty else None
        ha = float(hit["burnt_ha"].iloc[0]) if not hit.empty else None
        share = float(hit["share_pct"].iloc[0]) if not hit.empty else None
        name_ok = bool(name) and item["name_contains"].lower() in str(name).lower()
        share_ok = share is not None and abs(share - item["share_pct"]) <= tol["share_pct"]
        ha_ok = ha is not None and abs(ha - item["hectares"]) <= tol["hectares_rel"] * item["hectares"]
        rows.append({
            "region_id": item["region_id"],
            "region_name": name,
            "year": item["year"],
            "burnt_ha_thrive": ha,
            "burnt_ha_pbo": item["hectares"],
            "share_pct_thrive": share,
            "share_pct_pbo": item["share_pct"],
            "name_matches": name_ok,
            "within_tolerance": bool(name_ok and share_ok and ha_ok),
        })
    return pd.DataFrame(rows)


def coefficient_check(results: list[dict], cfg_val: dict) -> pd.DataFrame:
    tol = float(cfg_val["tolerance"]["coefficient"])
    rows = []
    for res in results:
        table = cfg_val.get("real" if res["measure"] == "growth_real" else "nominal", {})
        expected = table.get(res["sector"])
        if expected is None:
            continue
        ours = res["coef"] + [res["cumulative"]]
        pvals = res["p"] + [res["cumulative_p"]]
        labels = res["horizons"] + ["cumulative"]
        if res["measure"] == "growth_nominal" and len(expected) == len(ours) - 1:
            ours, pvals, labels = ours[1:], pvals[1:], labels[1:]
        for label, mine, theirs, pv in zip(labels, ours, expected, pvals):
            rows.append({
                "sector": res["sector"],
                "measure": "real" if res["measure"] == "growth_real" else "nominal",
                "horizon": label,
                "thrive": round(mine, 4),
                "pbo": theirs,
                "difference": round(mine - theirs, 4),
                "p_value_thrive": None if pv is None else round(pv, 4),
                "within_tolerance": abs(mine - theirs) <= tol,
            })
    return pd.DataFrame(rows)


def tourism_verdict(variants: list[dict], residences, alpha: float) -> dict:
    out = {}
    for resid in residences:
        rows = [v for v in variants if v["residence"] == resid]
        if not rows:
            out[resid] = "no data"
            continue
        sig = [v["cumulative_p"] is not None and v["cumulative_p"] < alpha for v in rows]
        if all(sig) and all(v["cumulative"] < 0 for v in rows):
            out[resid] = "lower after a fire"
        elif all(sig) and all(v["cumulative"] > 0 for v in rows):
            out[resid] = "higher after a fire"
        else:
            out[resid] = "not robust"
    return out


def tourism_summary(results: list[dict], nights: pd.DataFrame, exposure: pd.DataFrame, tc: dict, first: int, last: int) -> dict:
    share = exposure.set_index(["region_id", "year"])["share_pct"]
    focus = []
    for rid in tc.get("focus", []):
        rows = nights[(nights["region_id"] == rid) & (nights["sector"] == "TOTAL")].sort_values("year")
        fire_years = exposure[(exposure["region_id"] == rid) & (exposure["share_pct"] >= 1.0)]["year"].tolist()
        focus.append({
            "region_id": rid,
            "region_name": exposure.loc[exposure["region_id"] == rid, "region_name"].iloc[0] if (exposure["region_id"] == rid).any() else None,
            "fire_years_1pct": [int(y) for y in fire_years],
            "burnt_share_pct": {int(y): float(share.get((rid, y), 0.0)) for y in fire_years},
            "nights": {int(r["year"]): r["nights"] for _, r in rows.iterrows()},
            "growth_pct": {int(r["year"]): r["growth_nights"] for _, r in rows.iterrows()},
        })
    window = exposure[exposure["year"].between(first - 2, last)]
    return {
        "first_year": first,
        "last_year": last,
        "results": results,
        "focus": focus,
        "unit_years_1pct": int((window["share_pct"] >= 1.0).sum()),
    }


def _fmt(x, digits=2):
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:+.{digits}f}"


def report(summary: dict, burnt: pd.DataFrame, coefs: pd.DataFrame, sources: dict) -> str:
    ok = summary["replicated"]
    lines = [
        "# Phase C: wildfires, regional growth and Tourism, after the Hellenic Parliamentary Budget Office",
        "",
        "Generated automatically by `thrive phase-c`. `sources.json` records what was downloaded and when.",
        "",
        f"Source being replicated: {summary['source']}",
        "",
        "## Verdict on the replication",
        "",
        ("The result was replicated: the burnt areas and every coefficient of the gate sector are within tolerance." if ok else "The result was NOT replicated. Nothing is built on it until the differences below are explained."),
        "",
        "## Burnt area of the largest fires (Table C1)",
        "",
        "| Region | Year | Burnt ha, THRIVE | Burnt ha, PBO | Share %, THRIVE | Share %, PBO | Within tolerance |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, r in burnt.iterrows():
        ha = "n/a" if r["burnt_ha_thrive"] is None or pd.isna(r["burnt_ha_thrive"]) else f"{r['burnt_ha_thrive']:,.0f}"
        sh = "n/a" if r["share_pct_thrive"] is None or pd.isna(r["share_pct_thrive"]) else f"{r['share_pct_thrive']:.1f}"
        lines.append(f"| {r['region_name']} ({r['region_id']}) | {r['year']} | {ha} | {r['burnt_ha_pbo']:,} | {sh} | {r['share_pct_pbo']} | {'yes' if r['within_tolerance'] else 'no'} |")
    lines += [
        "",
        f"## Growth response to area burnt, {summary['first_year']} to {summary['last_year']} (Table C2)",
        "",
        "Percentage points of growth in GVA per inhabitant per 1 % of the region's area burnt. Region and year fixed effects, standard errors clustered by region.",
        "",
        "| Sector | Measure | Horizon | THRIVE | PBO | Difference | p-value, THRIVE | Within tolerance |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, r in coefs.iterrows():
        pv = "n/a" if r["p_value_thrive"] is None or pd.isna(r["p_value_thrive"]) else f"{r['p_value_thrive']:.2f}"
        lines.append(f"| {r['sector']} | {r['measure']} | {r['horizon']} | {_fmt(r['thrive'])} | {_fmt(r['pbo'])} | {_fmt(r['difference'])} | {pv} | {'yes' if r['within_tolerance'] else 'no'} |")
    lines += [
        "",
        "## Tourism nights after a fire (beyond the Note)",
        "",
        f"The Note ends in 2023, when regional accounts end. Eurostat counts nights spent at tourist accommodation by NUTS 3 region up to {summary['tourism']['last_year']}, so the same event study is run on the annual growth of nights, {summary['tourism']['first_year']} to {summary['tourism']['last_year']}. Percentage points of growth in nights per 1 % of the region's area burnt; region and year fixed effects; standard errors clustered by region. This is an extension of the Note, not part of the replication.",
        "",
        "| Nights by | Year before | Fire year | Year after | Two years after | Cumulative | Observations |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in summary["tourism"]["results"]:
        cells = [f"{_fmt(c)} (p {p:.2f})" if p is not None else _fmt(c) for c, p in zip(r["coef"], r["p"])]
        cum = f"{_fmt(r['cumulative'])} (p {r['cumulative_p']:.2f})" if r["cumulative_p"] is not None else _fmt(r["cumulative"])
        label = {"TOTAL": "all guests", "FOR": "guests from abroad", "DOM": "guests from Greece"}.get(r["sector"], r["sector"])
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {cum} | {r['observations']} |")
    labels = {"TOTAL": "all guests", "FOR": "guests from abroad", "DOM": "guests from Greece"}
    variants = summary["tourism"].get("variants", [])
    if variants:
        lines += [
            "",
            "The same cumulative effect, fire year to two years after, under each check fixed in advance:",
            "",
            "| Check | Nights by | Cumulative | Observations |",
            "| --- | --- | --- | --- |",
        ]
        for v in variants:
            cum = f"{_fmt(v['cumulative'])} (p {v['cumulative_p']:.2f})" if v["cumulative_p"] is not None else _fmt(v["cumulative"])
            lines.append(f"| {v['name']} | {labels.get(v['residence'], v['residence'])} | {cum} | {v['observations']} |")
        lines += ["", "Following THRIVE's own rule, a direction is reported as a finding only when every check agrees and is significant at the 5 % level:", ""]
        for resid, verdict in summary["tourism"]["verdict"].items():
            lines.append(f"- {labels.get(resid, resid)}: **{verdict}**")
    lines += [
        "",
        "Nights in the regions with the largest recent fires (all guests):",
        "",
    ]
    yrs = sorted({y for f in summary["tourism"]["focus"] for y in f["nights"]})
    lines += ["| Region | Fires burning 1 % or more | " + " | ".join(str(y) for y in yrs) + " |", "| --- | --- | " + " | ".join("---" for _ in yrs) + " |"]
    for f in summary["tourism"]["focus"]:
        fires = ", ".join(f"{y} ({s:.1f} %)" for y, s in f["burnt_share_pct"].items()) or "none"
        vals = []
        for y in yrs:
            n = f["nights"].get(y)
            g = f["growth_pct"].get(y)
            vals.append("n/a" if n is None else (f"{n:,.0f} ({g:+.1f} %)" if g is not None else f"{n:,.0f}"))
        lines.append(f"| {f['region_name']} ({f['region_id']}) | {fires} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "## The data",
        "",
        f"- Regions: {summary['regions']} NUTS 3 regions of Greece; observations in the gate regression: {summary['gate_observations']}.",
        f"- Unit-years with at least 1 % of the area burnt, {summary['first_year']} to {summary['last_year']}: {summary['unit_years_1pct']}.",
        f"- EFFIS fires matched to Greek regions: {summary['fires_matched']}, years {summary['fire_years'][0]} to {summary['fire_years'][1]}.",
        f"- Eurostat tables last updated: " + ", ".join(f"{k} {v}" for k, v in sources["eurostat_updated"].items()) + ".",
        "",
        "Tolerances: " + f"{summary['tolerance']['coefficient']} percentage points for each coefficient; {summary['tolerance']['share_pct']} percentage points for each burnt share; {summary['tolerance']['hectares_rel']:.0%} for each burnt area.",
        "",
    ]
    return "\n".join(lines)


def run(config_path: Path, out_dir: Path, fetcher: Fetcher = fetch, effis_path: Path | None = None) -> dict:
    cfg = load_config(config_path)
    e, ef, rg, st, val = cfg["eurostat"], cfg["effis"], cfg["regions"], cfg["study"], cfg["validation"]
    crs = int(rg["crs"])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, url, fn):
        try:
            value = fn()
            checks.append({"check": name, "url": url, "ok": True, "error": None})
            return value
        except Exception as exc:
            checks.append({"check": name, "url": url, "ok": False, "error": str(exc)})
            return None

    tables = check("Eurostat regional accounts", e["api"].format(code=e["gva"]["code"]), lambda: eurostat_tables(cfg, fetcher))
    tourism = check("Eurostat tourism nights", e["api"].format(code=cfg["tourism"]["code"]), lambda: tourism_table(cfg, fetcher))
    nuts_bytes = check("GISCO NUTS 3 regions", rg["url"], lambda: fetcher(rg["url"]))
    work = Path(tempfile.mkdtemp(prefix="thrive-c-"))
    if effis_path is None:
        zp = work / "effis_layer.zip"
        effis_digest = check("EFFIS burnt areas", ef["url"], lambda: fetch_to_file(ef["url"], zp))
    else:
        zp = Path(effis_path)
        effis_digest = sha256(zp.read_bytes())
        checks.append({"check": "EFFIS burnt areas", "url": str(effis_path), "ok": True, "error": None})
    (out_dir / "preflight.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    if not all(x["ok"] for x in checks):
        raise RuntimeError("preflight failed: " + " | ".join(f"{x['check']} {x['url']}: {x['error']}" for x in checks if not x["ok"]))
    regions = region_polygons(nuts_bytes, e["country"], crs)
    expected = int(e["expected_regions"])
    if len(regions) != expected:
        raise ValueError(f"GISCO returned {len(regions)} Greek NUTS 3 regions, expected {expected}")
    eurostat_regions = sorted(tables["gva3"]["geo"].unique())
    if sorted(regions["region_id"]) != eurostat_regions:
        raise ValueError(f"Eurostat and GISCO list different Greek NUTS 3 regions: {sorted(set(eurostat_regions) ^ set(regions['region_id']))}")
    if zipfile.is_zipfile(zp):
        unpacked = work / "effis"
        with zipfile.ZipFile(zp) as zf:
            zf.extractall(unpacked)
        layers = sorted(p for p in unpacked.rglob("*") if p.suffix.lower() in (".shp", ".gpkg", ".db", ".sqlite"))
        if not layers:
            raise ValueError("the EFFIS archive holds no vector layer")
        layer_path = layers[0]
    else:
        layer_path = zp
    fires, fire_info = fire_polygons(layer_path, ef, regions, crs)
    unparsed = fire_info["unparsed_dates"] / max(fire_info["features_in_box"], 1)
    if unparsed > float(ef["max_unparsed_share"]):
        raise ValueError(f"{fire_info['unparsed_dates']} of {fire_info['features_in_box']} fire dates could not be read")
    burnt = burnt_by_region(fires, regions)
    if burnt.empty:
        raise ValueError("no EFFIS fire intersects a Greek region")
    first, last = int(st["first_year"]), int(st["last_year"])
    leads, lags = int(st["leads"]), int(st["lags"])
    needed = range(first - lags, last + leads + 1)
    earliest = int(burnt["year"].min())
    if earliest > first - lags or earliest > int(ef["first_year"]):
        raise ValueError(f"EFFIS fires start in {earliest}; the study needs {first - lags}")
    tc = cfg["tourism"]
    t_first, t_last = int(tc["first_year"]), int(tc["last_year"])
    years = range(min(min(needed), t_first - lags), max(int(burnt["year"].max()), max(needed), t_last + leads) + 1)
    exposure = exposure_table(burnt, regions, years)
    growth = growth_panel(tables["gva3"], tables["pop3"], tables["gva2_total"], tables["vol2"])
    results = []
    for s in cfg["sector"]:
        for measure in ("growth_real", "growth_nominal"):
            results.append(event_study(growth, exposure, s["key"], measure, first, last, leads, lags))
    nights = nights_growth(tourism["nights"])
    tourism_results = []
    for resid in tc["residence"]:
        if (nights["sector"] == resid).any():
            tourism_results.append(event_study(nights, exposure, resid, "growth_nights", t_first, t_last, leads, lags))
    tourism_variants = []
    for v in tc.get("variant", []):
        subset = nights[~nights["region_id"].isin(v.get("exclude", []))]
        for resid in tc["residence"]:
            if (subset["sector"] == resid).any():
                res = event_study(subset, exposure, resid, "growth_nights", int(v["first_year"]), t_last, leads, lags)
                tourism_variants.append({"key": v["key"], "name": v["name"], "residence": resid, **res})
    burnt_df = burnt_check(exposure, val)
    coef_df = coefficient_check(results, val)
    gate = st["gate_sector"]
    gate_ok = bool(coef_df[coef_df["sector"] == gate]["within_tolerance"].all()) and not coef_df[coef_df["sector"] == gate].empty
    replicated = bool(gate_ok and burnt_df["within_tolerance"].all())
    gate_res = next(r for r in results if r["sector"] == gate and r["measure"] == "growth_real")
    in_window = exposure[exposure["year"].between(first, last)]
    summary = {
        "source": cfg["source"]["name"],
        "replicated": replicated,
        "gate_sector": gate,
        "first_year": first,
        "last_year": last,
        "regions": int(len(regions)),
        "gate_observations": gate_res["observations"],
        "unit_years_1pct": int((in_window["share_pct"] >= 1.0).sum()),
        "fires_matched": int(burnt["fire_id"].nunique()),
        "fire_years": [int(burnt["year"].min()), int(burnt["year"].max())],
        "tolerance": val["tolerance"],
        "results": results,
        "burnt_check": json.loads(burnt_df.to_json(orient="records")),
        "coefficient_check": json.loads(coef_df.to_json(orient="records")),
        "tourism": {**tourism_summary(tourism_results, nights, exposure, tc, t_first, t_last), "variants": tourism_variants, "verdict": tourism_verdict(tourism_variants, tc["residence"], float(tc.get("alpha", 0.05)))},
    }
    sources = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "replicates": cfg["source"]["name"],
        "replicates_url": cfg["source"]["url"],
        "eurostat_urls": tables["urls"],
        "eurostat_sha256": tables["sha256"],
        "eurostat_updated": tables["updated"],
        "tourism_url": tourism["url"],
        "tourism_sha256": tourism["sha256"],
        "tourism_updated": tourism["updated"],
        "regions_url": rg["url"],
        "regions_sha256": sha256(nuts_bytes),
        "effis_url": ef["url"] if effis_path is None else str(effis_path),
        "effis_licence": ef["licence"],
        "effis_sha256": effis_digest,
        "effis_layer": layer_path.name,
        "effis_fields": fire_info["fields"],
        "effis_date_field": fire_info["date_field"],
        "effis_id_field": fire_info["id_field"],
        "effis_features_in_box": fire_info["features_in_box"],
        "effis_unparsed_dates": fire_info["unparsed_dates"],
        "crs": f"EPSG:{crs}",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(report(summary, burnt_df, coef_df, sources), encoding="utf-8")
    fires_out = burnt.merge(regions[["region_id", "region_name"]], on="region_id", how="left")
    fires_out["fire_date"] = fires_out["fire_date"].astype(str)
    with pd.ExcelWriter(out_dir / "phase-c.xlsx", engine="openpyxl") as xl:
        coef_df.to_excel(xl, sheet_name="Replication", index=False)
        burnt_df.to_excel(xl, sheet_name="Burnt area check", index=False)
        pd.DataFrame([
            {"sector": r["sector"], "measure": r["measure"], "horizon": h, "coefficient": c, "std_error": s, "p_value": p, "observations": r["observations"], "regions": r["regions"]}
            for r in results for h, c, s, p in zip(r["horizons"] + ["cumulative"], r["coef"] + [r["cumulative"]], r["se"] + [r["cumulative_se"]], r["p"] + [r["cumulative_p"]])
        ]).to_excel(xl, sheet_name="Event studies", index=False)
        pd.DataFrame([
            {"residence": r["sector"], "horizon": h, "coefficient": c, "std_error": se, "p_value": p, "observations": r["observations"], "regions": r["regions"]}
            for r in tourism_results for h, c, se, p in zip(r["horizons"] + ["cumulative"], r["coef"] + [r["cumulative"]], r["se"] + [r["cumulative_se"]], r["p"] + [r["cumulative_p"]])
        ]).to_excel(xl, sheet_name="Nights after a fire", index=False)
        pd.DataFrame([
            {"check": v["name"], "residence": v["residence"], "horizon": h, "coefficient": c, "std_error": se, "p_value": p, "observations": v["observations"], "regions": v["regions"]}
            for v in tourism_variants for h, c, se, p in zip(v["horizons"] + ["cumulative"], v["coef"] + [v["cumulative"]], v["se"] + [v["cumulative_se"]], v["p"] + [v["cumulative_p"]])
        ]).to_excel(xl, sheet_name="Nights checks", index=False)
        nights.merge(regions[["region_id", "region_name"]], on="region_id", how="left").to_excel(xl, sheet_name="Tourism nights", index=False)
        exposure.to_excel(xl, sheet_name="Burnt share by region", index=False)
        growth.merge(regions[["region_id", "region_name"]], on="region_id", how="left").to_excel(xl, sheet_name="Growth panel", index=False)
        fires_out.to_excel(xl, sheet_name="Fires by region", index=False)
        pd.DataFrame([{"field": k, "value": json.dumps(v) if isinstance(v, (list, dict)) else v} for k, v in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    return summary
