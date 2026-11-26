import json
import math
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from thrive.data.crops_probe import GDAL_ENV as CROP_ENV
from thrive.data.crops_probe import contains, crawl, dates_in, load_config, tif_header
from thrive.data.download import Fetcher, fetch, fetch_to_file
from thrive.data.thriving import cell_blocks, collect, dekad_of, dekad_table, make_grid, read_item, stac_items

SUMMER_K = list(range(15, 27))


def block_counts(arr: np.ndarray, per_km: int, classes: list[int]) -> dict[int, np.ndarray]:
    rows, cols = arr.shape[0] // per_km, arr.shape[1] // per_km
    a = arr[: rows * per_km, : cols * per_km].reshape(rows, per_km, cols, per_km)
    return {c: (a == c).sum(axis=(1, 3)) for c in classes}


def cell_lookup(cells, x0: float, y1: float, cols: int, rows: int) -> np.ndarray:
    lookup = np.full((rows, cols), -1, dtype=np.int64)
    cx, cy = cells.geometry.centroid.x.to_numpy(), cells.geometry.centroid.y.to_numpy()
    col = np.floor((cx - x0) / 1000).astype(int)
    row = np.floor((y1 - cy) / 1000).astype(int)
    ok = (col >= 0) & (col < cols) & (row >= 0) & (row < rows)
    lookup[row[ok], col[ok]] = np.arange(len(cells))[ok]
    return lookup


def crop_hectares(cells, url: str, classes: dict[str, int], strip_km: int = 5) -> pd.DataFrame:
    import rasterio
    from rasterio.windows import Window

    minx, miny, maxx, maxy = cells.total_bounds
    x0, y0 = math.floor(minx / 1000) * 1000, math.floor(miny / 1000) * 1000
    x1, y1 = math.ceil(maxx / 1000) * 1000, math.ceil(maxy / 1000) * 1000
    cols, rows = int((x1 - x0) // 1000), int((y1 - y0) // 1000)
    lookup = cell_lookup(cells, x0, y1, cols, rows)
    out = {name: np.zeros(len(cells)) for name in classes}
    src = "/vsicurl/" + url if url.startswith("http") else url
    with rasterio.Env(**CROP_ENV), rasterio.open(src) as ds:
        if ds.crs is None or ds.crs.to_epsg() != 3035:
            raise ValueError(f"crop map is not in EPSG:3035 but {ds.crs}")
        res = abs(ds.res[0])
        per_km = int(round(1000 / res))
        if abs(per_km * res - 1000) > 1e-6:
            raise ValueError(f"crop map pixel {res} m does not divide 1 km")
        col_off = (x0 - ds.bounds.left) / res
        row_off = (ds.bounds.top - y1) / res
        if abs(col_off - round(col_off)) > 1e-6 or abs(row_off - round(row_off)) > 1e-6:
            raise ValueError("crop map pixels are not aligned with the 1 km grid")
        col_off, row_off = int(round(col_off)), int(round(row_off))
        for r in range(0, rows, strip_km):
            n = min(strip_km, rows - r)
            win = Window(col_off, row_off + r * per_km, cols * per_km, n * per_km)
            arr = ds.read(1, window=win, boundless=True, fill_value=0)
            counts = block_counts(arr, per_km, list(classes.values()))
            sub = lookup[r : r + n]
            m = sub >= 0
            for name, code in classes.items():
                out[name][sub[m]] += counts[code][m] * (res * res) / 1e4
    return pd.DataFrame(out, index=cells.index)


def pick_year_file(files: list[dict], year: int, ext: str = ".nc") -> dict | None:
    best = None
    for f in files:
        if not f["name"].lower().endswith(ext):
            continue
        ds = dates_in(f["path"])
        if len(ds) >= 2 and ds[0][0] == ds[1][0] == "ymd" and ds[0][1] == date(year, 1, 1) and ds[1][1].year == year:
            if best is None or f["path"] > best["path"]:
                best = f
    return best


def band_dates(tags: dict, count: int) -> list[date]:
    vals = tags.get("NETCDF_DIM_time_VALUES")
    units = str(tags.get("time#units", ""))
    if not vals or " since " not in units:
        raise ValueError("the NetCDF file gives no time axis")
    unit, origin_text = units.split(" since ", 1)
    origin = date.fromisoformat(origin_text.strip()[:10])
    per_day = {"days": 1.0, "hours": 24.0, "minutes": 1440.0, "seconds": 86400.0}[unit.strip().lower()]
    out = [origin + timedelta(days=float(x) / per_day) for x in str(vals).strip("{}").split(",") if x.strip()]
    if len(out) != count:
        raise ValueError(f"time axis has {len(out)} values for {count} bands")
    return out


def sample_cells(path: Path, xs: np.ndarray, ys: np.ndarray, crs_points: str) -> tuple[list[date], np.ndarray]:
    import rasterio
    from pyproj import Transformer
    from rasterio.transform import rowcol
    from rasterio.windows import Window

    target = str(path)
    with rasterio.open(target) as ds:
        if ds.subdatasets:
            target = ds.subdatasets[0]
    with rasterio.open(target) as ds:
        dates = band_dates(ds.tags(), ds.count)
        crs = ds.crs or "EPSG:4326"
        tx, ty = Transformer.from_crs(crs_points, crs, always_xy=True).transform(xs, ys)
        rr, cc = rowcol(ds.transform, tx, ty)
        rr, cc = np.asarray(rr), np.asarray(cc)
        r0, r1, c0, c1 = int(rr.min()), int(rr.max()) + 1, int(cc.min()), int(cc.max()) + 1
        arr = ds.read(window=Window(c0, r0, c1 - c0, r1 - r0), boundless=True, fill_value=np.nan, out_dtype="float32")
        vals = arr[:, rr - r0, cc - c0].T.astype("float64")
        nod = ds.nodata
        if nod is not None and np.isfinite(nod):
            vals[vals == nod] = np.nan
        vals[np.abs(vals) > 1e6] = np.nan
    return dates, vals


def dekad_heat(dates: list[date], tmax: np.ndarray, thresholds: list[float], min_days: int = 8) -> pd.DataFrame:
    dk = [dekad_of(d) for d in dates]
    years = np.array([d[0] for d in dk])
    ks = np.array([d[1] for d in dk])
    rows = []
    for (y, k) in sorted(set(dk)):
        sel = (years == y) & (ks == k)
        block = tmax[:, sel]
        valid = np.isfinite(block)
        days = valid.sum(axis=1)
        enough = days >= min(min_days, int(sel.sum()))
        filled = np.where(valid, block, 0.0)
        part = {"cell": np.arange(tmax.shape[0]), "year": y, "k": k, "days": days}
        part["tmax_mean"] = np.where(enough, filled.sum(axis=1) / np.maximum(days, 1), np.nan)
        for t in thresholds:
            count = (np.where(valid, block, -np.inf) >= t).sum(axis=1).astype("float64")
            part[f"hot{int(t)}"] = np.where(enough, count, np.nan)
        rows.append(pd.DataFrame(part))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def dekad_mean(dates: list[date], values: np.ndarray, name: str) -> pd.DataFrame:
    rows = []
    for j, d in enumerate(dates):
        y, k = dekad_of(d)
        rows.append(pd.DataFrame({"cell": np.arange(values.shape[0]), "year": y, "k": k, name: values[:, j]}))
    df = pd.concat(rows, ignore_index=True)
    return df.groupby(["cell", "year", "k"], as_index=False)[name].mean()


def add_lag(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    prev = df[["cell", "year", "k"] + cols].copy()
    prev["k"] = prev["k"] + 1
    prev = prev.rename(columns={c: f"{c}_prev" for c in cols})
    out = df.merge(prev, on=["cell", "year", "k"], how="left")
    for c in cols:
        out[f"{c}_two"] = out[c] + out[f"{c}_prev"]
    return out


def demean(df: pd.DataFrame, cols: list[str], keys: list[str], tol: float = 1e-10, max_iter: int = 1000) -> pd.DataFrame:
    out = df[cols].to_numpy(dtype="float64").copy()
    codes = [pd.factorize(df[k])[0] for k in keys]
    sizes = [np.bincount(c).astype("float64") for c in codes]
    for _ in range(max_iter):
        change = 0.0
        for c, n in zip(codes, sizes):
            for j in range(out.shape[1]):
                m = np.bincount(c, weights=out[:, j], minlength=len(n)) / n
                out[:, j] -= m[c]
                change = max(change, float(np.abs(m).max()))
        if change < tol:
            break
    return pd.DataFrame(out, columns=cols, index=df.index)


def ols_cluster(y: np.ndarray, X: np.ndarray, clusters: np.ndarray, dof_absorbed: int) -> tuple[np.ndarray, np.ndarray]:
    XtX = X.T @ X
    inv = np.linalg.pinv(XtX)
    b = inv @ X.T @ y
    e = y - X @ b
    n, k = X.shape
    G = len(np.unique(clusters))
    meat = np.zeros((k, k))
    order = np.argsort(clusters, kind="mergesort")
    cs, Xs, es = clusters[order], X[order], e[order]
    bounds = np.flatnonzero(np.r_[True, cs[1:] != cs[:-1], True])
    for a, z in zip(bounds[:-1], bounds[1:]):
        s = Xs[a:z].T @ es[a:z]
        meat += np.outer(s, s)
    scale = (G / max(G - 1, 1)) * ((n - 1) / max(n - k - dof_absorbed, 1))
    V = inv @ meat @ inv * scale
    return b, np.sqrt(np.clip(np.diag(V), 0, None))


def estimate(panel: pd.DataFrame, heat: str, fe: str, control: str | None) -> dict:
    cols = ["y", heat] + ([control] if control else [])
    d = panel.dropna(subset=cols).copy()
    d["ck"] = d["cell"].astype(str) + "|" + d["k"].astype(str)
    d["yk"] = d["year"].astype(str) + "|" + d["k"].astype(str)
    keys = ["ck", "year" if fe == "year" else "yk"]
    if len(d) < 100 or d[heat].std() == 0:
        return {"n": int(len(d)), "b": None, "se": None, "lo": None, "hi": None, "pct": None, "pct_lo": None, "pct_hi": None}
    r = demean(d, cols, keys)
    X = r[[heat] + ([control] if control else [])].to_numpy()
    if np.allclose(X[:, 0], 0):
        return {"n": int(len(d)), "b": None, "se": None, "lo": None, "hi": None, "pct": None, "pct_lo": None, "pct_hi": None}
    absorbed = d[keys[1]].nunique() - 1
    b, se = ols_cluster(r["y"].to_numpy(), X, d["block"].to_numpy(), absorbed)
    lo, hi = b[0] - 1.96 * se[0], b[0] + 1.96 * se[0]
    return {
        "n": int(len(d)),
        "cells": int(d["cell"].nunique()),
        "clusters": int(d["block"].nunique()),
        "b": float(b[0]),
        "se": float(se[0]),
        "lo": float(lo),
        "hi": float(hi),
        "pct": float(100 * (math.exp(b[0]) - 1)),
        "pct_lo": float(100 * (math.exp(lo) - 1)),
        "pct_hi": float(100 * (math.exp(hi) - 1)),
    }


def verdict(rows: list[dict]) -> str:
    if not rows or any(r.get("b") is None for r in rows):
        return "no data"
    if all(r["hi"] < 0 for r in rows):
        return "lower greenness after hot days"
    if all(r["lo"] > 0 for r in rows):
        return "higher greenness after hot days"
    if all(r["lo"] <= 0 <= r["hi"] for r in rows):
        return "no effect shown"
    return "not robust"


def exposure_table(panel_heat: pd.DataFrame, crops: pd.DataFrame, cells, threshold: int, min_days: int) -> pd.DataFrame:
    h = panel_heat[panel_heat["k"].isin(SUMMER_K)].groupby(["cell", "year"], as_index=False)[f"hot{threshold}"].sum()
    h = h.merge(crops, left_on="cell", right_index=True).merge(cells[["region_id", "region_name"]], left_on="cell", right_index=True)
    h["exposed"] = h[f"hot{threshold}"] >= min_days
    rows = []
    for (y, rid, rname), g in h.groupby(["year", "region_id", "region_name"]):
        row = {"year": int(y), "region_id": rid, "region_name": rname}
        for crop in crops.columns:
            tot = g[crop].sum()
            row[f"{crop}_ha"] = round(float(tot), 0)
            row[f"{crop}_ha_exposed"] = round(float(g.loc[g["exposed"], crop].sum()), 0)
        row["mean_hot_days"] = round(float(g[f"hot{threshold}"].mean()), 1)
        rows.append(row)
    return pd.DataFrame(rows)


def report(s: dict, specs: pd.DataFrame, by_crop: pd.DataFrame, exposure: pd.DataFrame) -> str:
    def table(df):
        if df is None or df.empty:
            return "_No rows._\n"
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join("" if pd.isna(r[c]) else (f"{r[c]:,.4g}" if isinstance(r[c], float) else str(r[c])) for c in cols) + " |")
        return "\n".join(lines) + "\n"

    lines = [
        "# Heat and summer crops in Thessaly",
        "",
        "Generated automatically by `thrive crops-heat`. `sources.json` records what was read and when.",
        "",
        "Question: in the 1 km squares of Thessaly where cotton and maize grow, is the crop less green in the ten-day periods with more hot days, once soil moisture and the normal season of each square are accounted for?",
        "",
        f"Squares: {s['cells']} squares with at least {s['min_crop_ha']:.0f} ha of cotton and maize in the EU crop map 2022 ({s['cotton_ha']:,.0f} ha of cotton class and {s['maize_ha']:,.0f} ha of maize). Summers: {', '.join(str(y) for y in s['years'])}, ten-day periods June to September. Sentinel-2 scenes used: {s['scenes_used']:,} of {s['scenes_found']:,}.",
        "",
        "Heat: daily maximum temperature of the European Drought Observatory (JRC MARS, 10 km), counted as days at or above a threshold in each ten-day period. Soil moisture: soil moisture index anomaly of the European Drought Observatory (about 2 km). Greenness: median Sentinel-2 NDVI of each square in each ten-day period.",
        "",
        f"Model: log greenness on hot days and soil moisture, with a separate normal for each square and ten-day period of the year, and either a common effect of each year or a common effect of each ten-day period of each year. Standard errors are clustered on {s['block_km']:.0f} km blocks. Squares flooded by Storm Daniel are left out from September 2023 to the end of {s['flood_until']}.",
        "",
        "## Verdict",
        "",
        f"Across all {len(specs)} specifications: **{s['verdict']}**. A direction is reported as a finding only if every specification agrees and every 95% interval stays on one side of zero.",
        "",
        "## Every specification",
        "",
        table(specs),
        "## Cotton and maize separately (37 °C, this and the previous ten-day period, year effects)",
        "",
        table(by_crop),
        f"## Exposure: crop area in squares with at least {s['exposure_days']} days at or above {s['exposure_threshold']} °C in June to September",
        "",
        table(exposure),
        "## Limits",
        "",
        "- The crop map is of 2022; crops rotate, so a square counted as cotton may have grown another crop in another year. The cotton class of the map is the class of other non-permanent industrial crops, which in Thessaly is mostly cotton; its 2022 area is 19% above the Eurostat cotton area.",
        "- Temperature is a 10 km grid and soil moisture a model at about 1.5 km; neither sees the irrigation of a single field.",
        "- Greenness is not yield. A lower NDVI shows stress or earlier ageing of the canopy, not tonnes lost.",
        "- The years 2019 to 2025 are few; a result can depend on one unusual summer.",
    ]
    return "\n".join(lines) + "\n"


def run(config_path: Path, out_dir: Path, searcher: Callable | None = None, reader: Callable | None = None, fetcher: Fetcher = fetch) -> dict:
    import geopandas as gpd

    cfg = load_config(config_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sources = {"started": started}
    cells = gpd.read_file(cfg["cells"]["path"], layer=cfg["cells"].get("layer", "cells")).to_crs(3035).reset_index(drop=True)

    cm = cfg["cropmap"]
    bbox4326 = list(cells.to_crs(4326).total_bounds)
    head = tif_header(cm["url"])
    if not contains(head["bounds4326"], bbox4326):
        raise RuntimeError(f"the crop map file {cm['url']} does not cover all of Thessaly")
    classes = {name: int(code) for name, code in cm["classes"].items()}
    crops = crop_hectares(cells, cm["url"], classes)
    sources["crop_map"] = {"url": cm["url"], "crs": head["crs"], "res": head["res"]}
    min_ha = float(cm["min_crop_ha"])
    crop_cells = crops.index[crops.sum(axis=1) >= min_ha].to_numpy()
    if len(crop_cells) < int(cm["min_cells"]):
        raise RuntimeError(f"only {len(crop_cells)} squares hold at least {min_ha} ha of the summer crops")
    study = cells.loc[crop_cells].reset_index().rename(columns={"index": "row"})

    e = cfg["edo"]
    years = list(range(int(cfg["years"][0]), int(cfg["years"][1]) + 1))
    cx, cy = study.geometry.centroid.x.to_numpy(), study.geometry.centroid.y.to_numpy()
    heat_parts, sma_parts, edo_src = [], [], []
    tmax_files = crawl(e["base"] + e["tmax_dir"] + "/", fetcher, int(e["max_depth"]))
    sma_files = crawl(e["base"] + e["sma_dir"] + "/", fetcher, int(e["max_depth"]))
    with tempfile.TemporaryDirectory() as tmp:
        for y in years:
            for kind, flist in (("tmax", tmax_files), ("sma", sma_files)):
                f = pick_year_file(flist, y)
                if f is None:
                    raise RuntimeError(f"no {kind} file for {y} in the European Drought Observatory")
                local = Path(tmp) / f["name"]
                digest = fetch_to_file(f["url"], local)
                dates, vals = sample_cells(local, cx, cy, "EPSG:3035")
                local.unlink()
                edo_src.append({"kind": kind, "year": y, "url": f["url"], "sha256": digest, "bands": len(dates), "valid_share": float(np.isfinite(vals).mean())})
                if kind == "tmax":
                    heat_parts.append(dekad_heat(dates, vals, [float(t) for t in e["thresholds"]]))
                else:
                    sma_parts.append(dekad_mean(dates, vals, "sma"))
    sources["edo"] = edo_src
    heat = pd.concat(heat_parts, ignore_index=True)
    sma = pd.concat(sma_parts, ignore_index=True)

    st, px = cfg["stac"], cfg["pixels"]
    grid = make_grid(study, float(px["resolution_m"]))
    from pyproj import Transformer

    t = Transformer.from_crs(3035, 4326, always_xy=True)
    minx, miny, maxx, maxy = study.total_bounds
    lon, lat = t.transform([minx, maxx, maxx, minx], [miny, miny, maxy, maxy])
    bbox = (min(lon), min(lat), max(lon), max(lat))
    search = searcher or (lambda a, b: stac_items(st, bbox, a, b))
    items, checks = [], []
    for y in years:
        a, b = f"{y}-{cfg['season'][0]}", f"{y}-{cfg['season'][1]}"
        found = [i for i in search(a, b) if i.get("cloud") is None or float(i["cloud"]) <= st["max_cloud"]]
        ok = len(found) >= int(st["min_items_per_summer"])
        checks.append({"year": y, "scenes": len(found), "needed": int(st["min_items_per_summer"]), "ok": ok})
        items += found
    (out_dir / "preflight.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    if not all(c["ok"] for c in checks):
        raise RuntimeError("too few Sentinel-2 scenes: " + "; ".join(f"{c['year']}: {c['scenes']}" for c in checks if not c["ok"]))
    obs, inventory = collect(items, grid, px, reader or read_item, int(st.get("workers", 8)), float(px["default_scale"]), float(px["default_offset"]), float(px["max_negative_share"]))
    (out_dir / "items.json").write_text(json.dumps(inventory, indent=2, default=str) + "\n", encoding="utf-8")
    failed = sum(1 for i in inventory if "error" in i)
    if failed > float(st["max_failed_share"]) * max(len(inventory), 1):
        raise RuntimeError(f"{failed} of {len(inventory)} scenes could not be read; see items.json")
    dek = dekad_table(obs)
    dek = dek[dek["k"].isin(SUMMER_K) & (dek["ndvi"] > float(px["min_ndvi"]))]

    th = [int(x) for x in e["thresholds"]]
    hotcols = [f"hot{x}" for x in th]
    panel = heat.merge(sma, on=["cell", "year", "k"], how="left")
    panel = add_lag(panel, hotcols)
    panel = panel.merge(dek, on=["cell", "year", "k"], how="inner")
    panel["y"] = np.log(panel["ndvi"])
    blocks = cell_blocks(study, float(cfg["block_m"]))
    panel["block"] = blocks[panel["cell"].to_numpy()]
    flood = study[cfg["flood"]["column"]].to_numpy() >= float(cfg["flood"]["share"])
    after = (panel["year"] > 2023) | ((panel["year"] == 2023) & (panel["k"] >= 24))
    drop = flood[panel["cell"].to_numpy()] & after.to_numpy() & (panel["year"] <= int(cfg["flood"]["until_year"])).to_numpy()
    panel = panel[~drop]
    crops_study = crops.loc[crop_cells].reset_index(drop=True)
    panel = panel.merge(crops_study.assign(cell=np.arange(len(crops_study))), on="cell", how="left")

    specs = []
    for tval in th:
        for lag, col in (("this ten-day period", f"hot{tval}"), ("this and the previous ten-day period", f"hot{tval}_two")):
            for fe_name, fe in (("each year", "year"), ("each ten-day period of each year", "yeark")):
                r = estimate(panel, col, fe, "sma")
                specs.append({"threshold_C": tval, "hot_days_in": lag, "common_effect": fe_name, **r})
    v = verdict(specs)
    by_crop = []
    main_col = f"hot{37 if 37 in th else th[0]}_two"
    for crop in classes:
        share = panel[crop] / panel[list(classes)].sum(axis=1)
        sub = panel[share >= 0.5]
        by_crop.append({"crop": crop, **estimate(sub, main_col, "year", "sma")})
    exp_t, exp_d = int(cfg["exposure"]["threshold"]), int(cfg["exposure"]["days"])
    heat_study = heat.copy()
    heat_study["cell"] = study["row"].to_numpy()[heat_study["cell"].to_numpy()]
    exposure = exposure_table(heat_study, crops.loc[crop_cells], cells, exp_t, exp_d)

    spec_df, crop_df = pd.DataFrame(specs), pd.DataFrame(by_crop)
    summary = {
        "started": started,
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cells": int(len(crop_cells)),
        "min_crop_ha": min_ha,
        "cotton_ha": float(crops.loc[crop_cells, "cotton"].sum()) if "cotton" in crops else 0.0,
        "maize_ha": float(crops.loc[crop_cells, "maize"].sum()) if "maize" in crops else 0.0,
        "years": years,
        "scenes_found": len(items),
        "scenes_used": int(obs["item"].nunique()) if len(obs) else 0,
        "rows": int(len(panel)),
        "block_km": float(cfg["block_m"]) / 1000,
        "flood_until": int(cfg["flood"]["until_year"]),
        "verdict": v,
        "exposure_threshold": exp_t,
        "exposure_days": exp_d,
        "specifications": specs,
        "by_crop": by_crop,
    }
    with pd.ExcelWriter(out_dir / "crops-heat.xlsx") as xl:
        spec_df.to_excel(xl, sheet_name="specifications", index=False)
        crop_df.to_excel(xl, sheet_name="by_crop", index=False)
        exposure.to_excel(xl, sheet_name="exposure", index=False)
        out_cells = study[["row", "cell_id", "region_id", "region_name"]].join(crops_study)
        out_cells.to_excel(xl, sheet_name="squares", index=False)
        panel.drop(columns=["y"]).head(1_000_000).to_excel(xl, sheet_name="panel", index=False)
    (out_dir / "report.md").write_text(report(summary, spec_df, crop_df, exposure), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2, default=str) + "\n", encoding="utf-8")
    return summary
