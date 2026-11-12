import json
import math
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from thrive.recovery import robust_recovery

GDAL_ENV = {
    "AWS_NO_SIGN_REQUEST": "YES",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF,.tiff",
    "GDAL_HTTP_MAX_RETRY": "5",
    "GDAL_HTTP_RETRY_DELAY": "3",
    "GDAL_HTTP_MULTIPLEX": "YES",
    "VSI_CACHE": "TRUE",
}


def load_config(path: Path) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def dekad_of(d: date) -> tuple[int, int]:
    return d.year, (d.month - 1) * 3 + min((d.day - 1) // 10, 2)


def dekad_start(year: int, k: int) -> date:
    return date(year, k // 3 + 1, 1 + 10 * (k % 3))


def dekads_between(start: date, end: date) -> list[tuple[int, int]]:
    out, y, k = [], *dekad_of(start)
    while dekad_start(y, k) <= end:
        out.append((y, k))
        k += 1
        if k == 36:
            y, k = y + 1, 0
    return out


@dataclass
class Grid:
    x0: float
    y1: float
    res: float
    width: int
    height: int
    per_km: int
    pixel_cell: np.ndarray

    @property
    def transform(self):
        from rasterio.transform import from_origin

        return from_origin(self.x0, self.y1, self.res, self.res)

    def window_for(self, bounds) -> tuple[int, int, int, int] | None:
        minx, miny, maxx, maxy = bounds
        c0 = max(0, int(math.floor((minx - self.x0) / self.res)))
        c1 = min(self.width, int(math.ceil((maxx - self.x0) / self.res)))
        r0 = max(0, int(math.floor((self.y1 - maxy) / self.res)))
        r1 = min(self.height, int(math.ceil((self.y1 - miny) / self.res)))
        if c0 >= c1 or r0 >= r1:
            return None
        return r0, r1, c0, c1


def make_grid(cells, res: float) -> Grid:
    per_km = int(round(1000 / res))
    if abs(per_km * res - 1000) > 1e-9:
        raise ValueError("the pixel size must divide 1000 m exactly")
    minx, miny, maxx, maxy = cells.total_bounds
    x0, y0 = math.floor(minx / 1000) * 1000, math.floor(miny / 1000) * 1000
    x1, y1 = math.ceil(maxx / 1000) * 1000, math.ceil(maxy / 1000) * 1000
    cols, rows = int((x1 - x0) // 1000), int((y1 - y0) // 1000)
    lookup = np.full((rows, cols), -1, dtype=np.int32)
    cx, cy = cells.geometry.centroid.x.to_numpy(), cells.geometry.centroid.y.to_numpy()
    col = ((cx - x0) // 1000).astype(int)
    row = ((y1 - cy) // 1000).astype(int)
    lookup[row, col] = np.arange(len(cells))
    pixel_cell = np.repeat(np.repeat(lookup, per_km, axis=0), per_km, axis=1)
    return Grid(x0, y1, res, cols * per_km, rows * per_km, per_km, pixel_cell)


def stac_items(cfg: dict, bbox, start: str, end: str) -> list[dict]:
    from pystac_client import Client

    client = Client.open(cfg["url"])
    search = client.search(collections=[cfg["collection"]], bbox=list(bbox), datetime=f"{start}T00:00:00Z/{end}T23:59:59Z", limit=200)
    names = cfg["assets"]
    out, raw = [], 0
    first_keys = None
    for it in search.items():
        raw += 1
        if first_keys is None:
            first_keys = sorted(it.assets)
        assets = {}
        for role, key in names.items():
            a = it.assets.get(key)
            if a is None:
                break
            bands = a.extra_fields.get("raster:bands") or [{}]
            assets[role] = {"href": a.href, "scale": bands[0].get("scale"), "offset": bands[0].get("offset")}
        else:
            out.append({
                "id": it.id,
                "datetime": it.datetime.isoformat() if it.datetime else it.properties.get("datetime"),
                "cloud": it.properties.get("eo:cloud_cover"),
                "baseline": it.properties.get("s2:processing_baseline"),
                "bbox": list(it.bbox),
                "assets": assets,
            })
    if raw and not out:
        raise KeyError(f"{raw} scenes found but none has the assets {names}; the first has {first_keys}")
    return out


def read_item(item: dict, grid: Grid, window) -> dict[str, np.ndarray]:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.vrt import WarpedVRT

    r0, r1, c0, c1 = window
    transform = from_origin(grid.x0 + c0 * grid.res, grid.y1 - r0 * grid.res, grid.res, grid.res)
    out = {}
    with rasterio.Env(**GDAL_ENV):
        for role in ("red", "nir", "scl"):
            href = item["assets"][role]["href"]
            with rasterio.open(href) as src:
                level = overview_level(src.res[0], src.overviews(1), grid.res)
            opts = {} if level is None else {"overview_level": level}
            with rasterio.open(href, **opts) as src:
                with WarpedVRT(src, crs="EPSG:3035", transform=transform, width=c1 - c0, height=r1 - r0, resampling=Resampling.nearest, nodata=0) as vrt:
                    out[role] = vrt.read(1)
    return out


def overview_level(native: float, factors, target: float) -> int | None:
    best = None
    for i, f in enumerate(factors):
        if native * f <= target + 1e-6:
            best = i
    return best


def item_bounds_3035(item: dict):
    from pyproj import Transformer

    t = Transformer.from_crs(4326, 3035, always_xy=True)
    w, s, e, n = item["bbox"]
    xs, ys = t.transform([w, e, e, w], [s, s, n, n])
    return min(xs), min(ys), max(xs), max(ys)


def cell_values(item: dict, grid: Grid, window, bands: dict, px: dict, default_scale: float, default_offset: float) -> tuple[pd.DataFrame, dict]:
    r0, r1, c0, c1 = window
    idx = grid.pixel_cell[r0:r1, c0:c1]
    red, nir, scl = (bands[k].astype(np.float32) for k in ("red", "nir", "scl"))
    present = (idx >= 0) & (bands["red"] > 0) & (bands["nir"] > 0) & (bands["scl"] > 0)
    def conv(role, arr):
        a = item["assets"][role]
        scale = default_scale if a.get("scale") is None else float(a["scale"])
        offset = default_offset if a.get("offset") is None else float(a["offset"])
        return arr * scale + offset
    r, n = conv("red", red), conv("nir", nir)
    land = present & np.isin(scl, px["guard_classes"])
    negative = float(((r < 0) & land).sum() / land.sum()) if land.any() else 0.0
    valid = present & np.isin(scl, px["valid_classes"]) & (r + n > 0)
    ndvi = np.where(valid, (n - r) / np.where(r + n > 0, r + n, np.float32(1.0)), np.float32(np.nan)).astype(np.float32)
    ncell = int(grid.pixel_cell.max()) + 1
    inside = np.bincount(idx[idx >= 0], minlength=ncell)
    full = grid.per_km * grid.per_km
    seen = np.bincount(idx[present], minlength=ncell)
    df = pd.DataFrame({"cell": idx[valid], "ndvi": ndvi[valid]})
    if df.empty:
        return pd.DataFrame(columns=["cell", "ndvi", "valid_share"]), {"negative_share": negative, "cells": 0}
    g = df.groupby("cell")["ndvi"]
    res = pd.DataFrame({"ndvi": g.median(), "valid": g.size()})
    res["inside"] = inside[res.index]
    res["seen"] = seen[res.index]
    res = res[(res["inside"] >= full * px["min_cell_in_scene"]) & (res["seen"] >= full * px["min_cell_in_scene"])]
    res["valid_share"] = res["valid"] / res["seen"]
    res = res[res["valid_share"] >= px["min_valid_share"]]
    out = res.reset_index()[["cell", "ndvi", "valid_share"]]
    return out, {"negative_share": negative, "cells": int(len(out))}


def collect(items, grid: Grid, px: dict, reader, workers: int, default_scale: float, default_offset: float, guard_max: float):
    rows, inventory = [], []

    def one(item):
        win = grid.window_for(item_bounds_3035(item)) if "bounds_3035" not in item else grid.window_for(item["bounds_3035"])
        if win is None:
            return item, None, {"skipped": "outside the study area"}
        last = None
        for _ in range(3):
            try:
                bands = reader(item, grid, win)
                vals, info = cell_values(item, grid, win, bands, px, default_scale, default_offset)
                return item, vals, info
            except Exception as exc:
                last = exc
        return item, None, {"error": str(last)}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(one, it) for it in items]
        for f in as_completed(futures):
            item, vals, info = f.result()
            entry = {"id": item["id"], "datetime": item["datetime"], "cloud": item.get("cloud"), "baseline": item.get("baseline"), **info}
            flagged = vals is not None and info.get("negative_share", 0) > guard_max
            entry["excluded_offset_check"] = bool(flagged)
            inventory.append(entry)
            if vals is not None and not flagged and len(vals):
                d = datetime.fromisoformat(str(item["datetime"]).replace("Z", "+00:00")).date()
                rows.append(vals.assign(date=d, item=item["id"]))
    obs = pd.concat(sorted(rows, key=lambda r: str(r["item"].iloc[0])), ignore_index=True).sort_values(["item", "cell"], kind="mergesort", ignore_index=True) if rows else pd.DataFrame(columns=["cell", "ndvi", "valid_share", "date", "item"])
    return obs, sorted(inventory, key=lambda x: (str(x["datetime"]), x["id"]))


def dekad_table(obs: pd.DataFrame) -> pd.DataFrame:
    if obs.empty:
        return pd.DataFrame(columns=["cell", "year", "k", "ndvi"])
    best = obs.sort_values(["cell", "date", "valid_share", "item"], ascending=[True, True, False, True], kind="mergesort").drop_duplicates(["cell", "date"])
    dk = best["date"].map(dekad_of)
    best = best.assign(year=[x[0] for x in dk], k=[x[1] for x in dk])
    return best.groupby(["cell", "year", "k"], as_index=False)["ndvi"].median()


def baseline_table(dek: pd.DataFrame, years, window: int) -> pd.DataFrame:
    base = dek[dek["year"].isin(years)]
    parts = []
    for shift in range(-window, window + 1):
        parts.append(base.assign(k=(base["k"] + shift) % 36))
    allk = pd.concat(parts, ignore_index=True) if parts else base
    return allk.groupby(["cell", "k"])["ndvi"].median().rename("base")


def group_series(dek: pd.DataFrame, base: pd.Series, cells_idx, post_dekads, min_coverage: float, min_base: float = 0.0) -> pd.DataFrame:
    cells_idx = list(cells_idx)
    sub = dek[dek["cell"].isin(cells_idx)].set_index(["cell", "year", "k"])["ndvi"]
    rows = []
    for (y, k) in post_dekads:
        try:
            post = sub.xs((y, k), level=("year", "k"))
        except KeyError:
            post = pd.Series(dtype=float)
        b = base.reindex(pd.MultiIndex.from_arrays([post.index, [k] * len(post)], names=["cell", "k"])).to_numpy() if len(post) else np.array([])
        ok = ~np.isnan(b) if len(b) else np.array([], dtype=bool)
        n = int(ok.sum())
        cov = n / len(cells_idx) if cells_idx else 0.0
        sb = float(b[ok].sum()) if n else 0.0
        mean_base = sb / n if n else float("nan")
        ratio = float(post.to_numpy()[ok].sum() / sb) if n and cov >= min_coverage and sb > 0 and mean_base >= min_base else float("nan")
        rows.append({"year": y, "k": k, "date": dekad_start(y, k), "cells_observed": n, "coverage": cov, "baseline_ndvi": mean_base, "ratio": ratio})
    return pd.DataFrame(rows)


def year_counts(items, start: str, end: str, per_year: int) -> list[dict]:
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    counts = {}
    for i in items:
        y = int(str(i["datetime"])[:4])
        counts[y] = counts.get(y, 0) + 1
    out = []
    for y in range(a.year, b.year + 1):
        m0 = a.month if y == a.year else 1
        m1 = b.month if y == b.year else 12
        need = math.ceil(per_year * (m1 - m0 + 1) / 12)
        out.append({"year": y, "scenes": counts.get(y, 0), "needed": need, "ok": counts.get(y, 0) >= need})
    return out


def fill(series: pd.Series, max_gap: int) -> pd.Series:
    return series.interpolate(limit=max_gap, limit_area="inside")


def direction(pairs) -> str:
    vals = [p for p in pairs if p is not None]
    if not vals:
        return "no data"
    if all(p > 0 for p in vals):
        return "slower where more older people live"
    if all(p < 0 for p in vals):
        return "faster where more older people live"
    return "not robust"


def season_value(group_ratio, control_ratio, dates, start: str, end: str, min_periods: int):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    vals = [gr / cr for gr, cr, d in zip(group_ratio, control_ratio, dates) if a <= d <= b and np.isfinite(gr) and np.isfinite(cr) and cr > 0]
    return (float(np.mean(vals)), len(vals)) if len(vals) >= min_periods else (None, len(vals))


def compare(diffs, tolerance: float) -> str:
    vals = [d for d in diffs if d is not None]
    if not vals or len(vals) < len(diffs):
        return "no data"
    if all(abs(d) < tolerance for d in vals):
        return "no clear difference"
    if all(d <= -tolerance for d in vals):
        return "lower"
    if all(d >= tolerance for d in vals):
        return "higher"
    return "not robust"


def matrices(dek: pd.DataFrame, base: pd.Series, cells_idx, post_dekads):
    idx = list(cells_idx)
    pos = {c: i for i, c in enumerate(idx)}
    tpos = {p: i for i, p in enumerate(post_dekads)}
    P = np.full((len(idx), len(post_dekads)), np.nan)
    sub = dek[dek["cell"].isin(idx)]
    for c, y, k, v in zip(sub["cell"].to_numpy(), sub["year"].to_numpy(), sub["k"].to_numpy(), sub["ndvi"].to_numpy()):
        t = tpos.get((int(y), int(k)))
        if t is not None:
            P[pos[c], t] = v
    ks = [k for (_, k) in post_dekads]
    mi = pd.MultiIndex.from_product([idx, sorted(set(ks))], names=["cell", "k"])
    b = base.reindex(mi)
    B = np.full_like(P, np.nan)
    kpos = {k: j for j, k in enumerate(sorted(set(ks)))}
    bm = b.to_numpy().reshape(len(idx), len(kpos)) if len(idx) else np.zeros((0, len(kpos)))
    for t, k in enumerate(ks):
        B[:, t] = bm[:, kpos[k]]
    return P, B


def point_ratio(P, B, min_coverage: float, min_base: float):
    valid = ~np.isnan(P) & ~np.isnan(B)
    n = P.shape[0]
    cnt = valid.sum(axis=0)
    num = np.where(valid, P, 0.0).sum(axis=0)
    den = np.where(valid, B, 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_base = np.where(cnt > 0, den / np.maximum(cnt, 1), np.nan)
        ok = (cnt > 0) & (cnt / max(n, 1) >= min_coverage) & (den > 0) & (mean_base >= min_base)
        ratio = np.where(ok, num / np.where(den > 0, den, 1.0), np.nan)
    return ratio, valid


def replicate_ratio(P, valid, B, W):
    Pz = np.where(valid, P, 0.0).astype(np.float32)
    Bz = np.where(valid, B, 0.0).astype(np.float32)
    num = W @ Pz
    den = W @ Bz
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def poisson_weights(rng, reps: int, n: int):
    return rng.poisson(1.0, size=(reps, n)).astype(np.float32)


def season_with_interval(g_point, g_rep, c_point, c_rep, dates, start: str, end: str, min_periods: int):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    t = np.array([a <= d <= b for d in dates]) & np.isfinite(g_point) & np.isfinite(c_point) & (c_point > 0)
    if t.sum() < min_periods:
        return None, None, int(t.sum())
    point = float(np.mean(g_point[t] / c_point[t]))
    import warnings

    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rep = np.nanmean(g_rep[:, t] / c_rep[:, t], axis=1)
    return point, rep, int(t.sum())


def interval(rep, level: float = 0.95):
    if rep is None:
        return None
    r = rep[np.isfinite(rep)]
    if len(r) == 0:
        return None
    lo, hi = np.percentile(r, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return [float(lo), float(hi)]


def verdict(points, intervals, tolerance: float) -> str:
    if not points or any(p is None for p in points) or any(i is None for i in intervals):
        return "no data"
    if all(p <= -tolerance and i[1] < 0 for p, i in zip(points, intervals)):
        return "lower"
    if all(p >= tolerance and i[0] > 0 for p, i in zip(points, intervals)):
        return "higher"
    if all(i[0] <= 0 <= i[1] for i in intervals):
        return "no difference shown"
    return "not robust"


def select_groups(cells, key: str, g: dict) -> dict[str, list[int]]:
    share = cells[f"flooded_share_{key}"]
    flooded = cells[share >= g["flooded_share_min"]]
    out = {"All flooded cells": flooded.index.tolist()}
    for rid, sub in flooded.groupby("region_id"):
        if len(sub) >= g["min_cells"]:
            out[f"Flooded, {sub['region_name'].iloc[0]}"] = sub.index.tolist()
    lived = flooded[(flooded["population"] >= g["min_residents"]) & flooded["older_known"].astype(bool)]
    if len(lived) >= 2 * g["min_cells"]:
        os_ = lived["older"] / lived["population"]
        med = float(os_.median())
        out["Flooded, more older residents"] = lived.index[os_ > med].tolist()
        out["Flooded, fewer older residents"] = lived.index[os_ <= med].tolist()
    return out


def control_cells(cells, g: dict, ring=None) -> list[int]:
    ring = ring or g["control_ring_m"]
    widest = cells[[c for c in cells.columns if c.startswith("flooded_share_")]].max(axis=1)
    wet = cells[widest > 0]
    dry = cells[widest == 0]
    if wet.empty:
        return []
    zone = wet.geometry.union_all()
    outer, inner = zone.buffer(ring[1]), zone.buffer(ring[0])
    cent = dry.geometry.centroid
    keep = cent.within(outer) & ~cent.within(inner)
    return dry.index[keep].tolist()


def _season_cell(v, iv=None) -> str:
    if v is None:
        return "n/a"
    if v < 0:
        return "below zero: mostly still under water"
    return f"{v:.0%}" if iv is None else f"{v:.0%} ({iv[0]:.0%} to {iv[1]:.0%})"


def _iv_lookup(summary, ring, dname, gname, season):
    for r in summary.get("season_intervals", []):
        if r["ring"] == ring and r["definition"] == dname and r["group"] == gname and r["season"] == season:
            return r["interval"]
    return None


def report(summary: dict) -> str:
    seasons = summary["seasons"]
    lines = [
        "# Thriving: when did the flooded land of Thessaly come back?",
        "",
        "Generated automatically by `thrive thriving`. `sources.json` records what was read and when.",
        "",
        f"Measure: greenness (NDVI) from Sentinel-2 ({summary['collection']}), per 1 km cell and per ten-day period, compared with the same period of {', '.join(str(y) for y in summary['baseline_years'])} in the same cell. Each group is divided by unflooded cells {summary['control_ring_km'][0]:g} to {summary['control_ring_km'][1]:g} km from the flood, so that a dry or wet year does not count as damage or recovery. 100% means as green as normal, relative to those neighbours.",
        f"Images: {summary['items_used']:,} of {summary['items_listed']:,} scenes used ({summary['items_failed']} could not be read, {summary['items_excluded']} failed the reflectance check). Control: {summary['control_cells']:,} cells.",
        f"Ten-day periods in which a group is not normally green (average greenness below {summary['min_baseline_ndvi']:.2f} in the years before) are skipped, because a bare flooded field then looks the same as a bare normal one. Cells that are not green in a normal year at all (median below {summary['min_cell_ndvi']:.2f}: lakes, towns, bare ground) are left out.",
        "",
        "| Period | Year | Scenes | Expected at least |",
        "| --- | --- | --- | --- |",
    ]
    for name, rows in summary["scenes_by_year"].items():
        for y in rows:
            lines.append(f"| {name.split(',')[1].strip().split(' period')[0]} | {y['year']} | {y['scenes']:,} | {y['needed']:,} |")
    lines.append("")
    for gl in summary["groups_left_out"]:
        lines.append(f"Left out: {gl['group']} ({gl['definition']}), only {gl['green_cells']} of {gl['cells']} cells are green in a normal year.")
    if summary["groups_left_out"]:
        lines.append("")
    main_ring = summary["control_rings"][0]["ring"]
    lines += ["## Greenness season by season", "", f"Average over the ten-day periods of each season with a clear view; a season needs at least {summary['season_min_periods']} such periods. In brackets, the 95% interval from {summary['replicates']:,} resamplings of the squares (Poisson bootstrap), with control squares {main_ring} from the flood. It shows how much a figure depends on which squares happen to be in a group."]
    for d in summary["definitions"]:
        lines += ["", f"### {d['name']}", "", "| Group | Cells | Residents | " + " | ".join(x["name"] for x in seasons) + " |", "| --- | --- | --- | " + " | ".join("---" for _ in seasons) + " |"]
        for gname, gr in d["groups"].items():
            lines.append(f"| {gname} | {gr['cells']:,} | {gr['residents']:,.0f} | " + " | ".join(_season_cell(gr["seasons"][x["name"]], _iv_lookup(summary, main_ring, d["name"], gname, x["name"])) for x in seasons) + " |")
    rings_txt = ", ".join(f"{r['ring']} ({r['control_cells']:,} squares)" for r in summary["control_rings"])
    lines += ["", "## What holds under every flood definition and every control area", "", f"Each comparison is repeated under all {len(summary['definitions'])} flood definitions and with control squares at {len(summary['control_rings'])} distances from the flood: {rings_txt}. A difference counts as a finding only if, every time, it is at least {summary['season_tolerance'] * 100:.0f} points and its 95% interval stays on one side of zero. If the interval includes zero every time, no difference is shown. Anything else is not robust."]
    for c in summary["comparisons"]:
        verdict_txt = {"lower": f"{c['a']} lower", "higher": f"{c['a']} higher"}.get(c["verdict"], c["verdict"])
        lines += ["", f"**{c['a']} against {c['b']}, {c['season']}: {verdict_txt}**", "", "| Control area | Flood definition | Difference | 95% interval |", "| --- | --- | --- | --- |"]
        for dt in c["detail"]:
            dtxt = "n/a" if dt["difference"] is None else f"{dt['difference'] * 100:+.1f} points"
            itxt = "n/a" if dt["interval"] is None else f"{dt['interval'][0] * 100:+.1f} to {dt['interval'][1] * 100:+.1f}"
            lines.append(f"| {dt['ring']} | {dt['definition']} | {dtxt} | {itxt} |")
    lines += ["", f"## When did each group come back (counted from {summary['recovery_start']})", "", f"A group counts as recovered at a threshold α on the first of {summary['persistence']} ten-day periods in a row in which its greenness, relative to the control, is at least α of normal. Gaps of up to {summary['max_gap']} periods are interpolated. The count starts with the first growing season after the flood, for the reason given under Limits."]
    for d in summary["definitions"]:
        lines += ["", f"### {d['name']}", "", "| Group | Lowest point | " + " | ".join(f"Recovered at {int(a * 100)}%" for a in summary["alphas"]) + " |", "| --- | --- | " + " | ".join("---" for _ in summary["alphas"]) + " |"]
        for gname, gr in d["groups"].items():
            lr = gr["lowest_ratio"]
            low = "n/a" if lr is None else ("below zero" if lr < 0 else f"{lr:.0%}") + f" ({gr['lowest_date']})"
            rec = ["not within the period" if gr["recovered"][str(a)] is None else f"{gr['recovered'][str(a)]} (day {gr['days'][str(a)]})" for a in summary["alphas"]]
            lines.append(f"| {gname} | {low} | " + " | ".join(rec) + " |")
        lines.append("")
        lines.append(f"Order of recovery the same under every threshold: **{'yes' if d['stable'] else 'no'}**.")
        if d.get("older_gap_days") is not None:
            lines.append("Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: " + "; ".join(f"α {int(float(a) * 100)}%: {'n/a' if v is None else f'{v:+d}'}" for a, v in d["older_gap_days"].items()) + ".")
    lines += [
        "",
        f"Recovery days, across every flood definition and threshold: **{summary['direction']}**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.",
        "",
        "## Limits",
        "",
        "Autumn greenness after the flood is hard to read. The storm struck a few weeks before the cotton harvest, and in a normal year the harvested fields of the plain are bare by October, so a field that was never harvested, or that later grew weeds or another crop, can look as green as normal or greener while yielding nothing. Greenness alone cannot tell crop from weeds, so greenness right after the flood does not mean the land was working again. That is why the recovery count starts with the next growing season.",
        "",
        "Greenness measures fields and gardens coming back, not households: a farm can be green again while its owners are still waiting for help, and a village can be rebuilt on land that stays bare. Clouds remove many autumn and winter images, crops rotate between years, and farmers may have left fields fallow on purpose. Greenness below zero means the ground is mostly water. The cells with more older residents are compared with those with fewer within the flooded area only, and both include the fields around each village.",
    ]
    return "\n".join(lines) + "\n"


def run(config_path: Path, out_dir: Path, searcher: Callable | None = None, reader: Callable | None = None) -> dict:
    import geopandas as gpd

    cfg = load_config(config_path)
    st, per, px, g, rc = cfg["stac"], cfg["periods"], cfg["pixels"], cfg["groups"], cfg["recovery"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = gpd.read_file(cfg["cells"]["path"], layer=cfg["cells"].get("layer", "cells")).to_crs(3035).reset_index(drop=True)
    keys = [d["key"] for d in cfg["definitions"]]
    missing = [k for k in keys if f"flooded_share_{k}" not in cells.columns]
    if missing:
        raise KeyError(f"cells file lacks flood shares for {missing}; columns: {list(cells.columns)}")
    groups_by_def = {k: select_groups(cells, k, g) for k in keys}
    rings = [list(r) for r in g.get("control_rings", [g["control_ring_m"]])]
    controls = {tuple(r): control_cells(cells, g, r) for r in rings}
    control = controls[tuple(rings[0])]
    for r, cc in controls.items():
        if len(cc) < g["min_cells"]:
            raise ValueError(f"only {len(cc)} control cells found for the ring {r}")
    needed = sorted(set().union(*[set(c) for c in controls.values()]).union(*[set(i) for gs in groups_by_def.values() for i in gs.values()]))
    study = cells.loc[needed].reset_index().rename(columns={"index": "row"})
    grid = make_grid(study, float(px["resolution_m"]))
    from pyproj import Transformer

    t = Transformer.from_crs(3035, 4326, always_xy=True)
    minx, miny, maxx, maxy = study.total_bounds
    lon, lat = t.transform([minx, maxx, maxx, minx], [miny, miny, maxy, maxy])
    bbox = (min(lon), min(lat), max(lon), max(lat))
    search = searcher or (lambda a, b: stac_items(st, bbox, a, b))
    checks, lists = [], {}
    for name, (a, b) in {"baseline": per["baseline"], "after": per["after"]}.items():
        try:
            found = [i for i in search(a, b) if i.get("cloud") is None or float(i["cloud"]) <= st["max_cloud"]]
            lists[name] = found
            years = year_counts(found, a, b, int(st["min_items_per_year"]))
            thin = [f"{y['year']}: {y['scenes']} scenes, at least {y['needed']} expected" for y in years if not y["ok"]]
            ok = not thin
            checks.append({"check": f"Sentinel-2 scenes, {name} period {a} to {b}", "url": st["url"], "ok": ok, "items": len(found), "by_year": years, "error": None if ok else "too few scenes in " + "; ".join(thin)})
        except Exception as exc:
            checks.append({"check": f"Sentinel-2 scenes, {name} period {a} to {b}", "url": st["url"], "ok": False, "items": 0, "error": str(exc)})
    (out_dir / "preflight.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    if not all(c["ok"] for c in checks):
        raise RuntimeError("preflight failed: " + " | ".join(f"{c['check']}: {c['error']}" for c in checks if not c["ok"]))
    items = lists["baseline"] + lists["after"]
    obs, inventory = collect(items, grid, px, reader or read_item, int(st.get("workers", 8)), float(px["default_scale"]), float(px["default_offset"]), float(px["max_negative_share"]))
    (out_dir / "items.json").write_text(json.dumps(inventory, indent=2, default=str) + "\n", encoding="utf-8")
    failed = sum(1 for i in inventory if "error" in i)
    if failed > float(st["max_failed_share"]) * len(inventory):
        raise RuntimeError(f"{failed} of {len(inventory)} scenes could not be read; see items.json")
    obs["cell"] = study["row"].to_numpy()[obs["cell"].astype(int).to_numpy()] if len(obs) else obs["cell"]
    dek = dekad_table(obs)
    years = list(range(int(per["baseline"][0][:4]), int(per["baseline"][1][:4]) + 1))
    base = baseline_table(dek, years, int(rc["baseline_window"]))
    flood_day = date.fromisoformat(per["flood_date"])
    post = dekads_between(date.fromisoformat(per["after"][0]), date.fromisoformat(per["after"][1]))
    alphas = [float(a) for a in rc["alphas"]]
    min_base = float(rc["min_baseline_ndvi"])
    level = base.groupby(level="cell").median()
    green = set(level[level >= float(rc["min_cell_ndvi"])].index)
    control = [c for c in control if c in green]
    ctrl = group_series(dek, base, control, post, float(rc["min_coverage"]), min_base)
    series_rows, rec_rows, defs_out, gaps_all, skipped_groups, season_rows = [], [], [], [], [], []
    se = cfg["seasons"]
    season_list = se["list"]
    post_dates = [dekad_start(*p) for p in post]
    rec_start = date.fromisoformat(rc["recovery_start"])
    for d in cfg["definitions"]:
        k = d["key"]
        rel, info, raw = {}, {}, {}
        for gname, idx_all in groups_by_def[k].items():
            idx = [c for c in idx_all if c in green]
            if len(idx) < g["min_cells"]:
                skipped_groups.append({"definition": d["name"], "group": gname, "cells": len(idx_all), "green_cells": len(idx)})
                continue
            s = group_series(dek, base, idx, post, float(rc["min_coverage"]), min_base)
            r = fill(pd.Series(s["ratio"].to_numpy() / ctrl["ratio"].to_numpy()), int(rc["max_gap"]))
            rel[gname] = r
            raw[gname] = s["ratio"].to_numpy()
            sub = cells.loc[idx]
            info[gname] = {"cells": len(idx), "cells_left_out_not_green": len(idx_all) - len(idx), "residents": float(sub["population"].sum()), "older_share": float(sub["older"].sum() / sub["population"].sum()) if sub["population"].sum() > 0 else None}
            for i, row in s.iterrows():
                series_rows.append({"definition": d["name"], "group": gname, "date": row["date"], "group_ratio": row["ratio"], "control_ratio": ctrl["ratio"].iloc[i], "relative": r.iloc[i], "coverage": row["coverage"], "control_coverage": ctrl["coverage"].iloc[i]})
        mask = np.array([dekad_start(*p) >= rec_start for p in post])
        finding = robust_recovery({gname: np.where(mask, v.to_numpy(), np.nan) for gname, v in rel.items()}, {gname: 1.0 for gname in rel}, alphas, int(rc["persistence"]))
        groups_out = {}
        for gname, v in rel.items():
            arr = v.to_numpy()
            lowest = int(np.nanargmin(arr)) if np.isfinite(arr).any() else None
            recovered, days = {}, {}
            for a, dd in zip(alphas, finding.days):
                i = dd[gname]
                recovered[str(a)] = None if i is None else dekad_start(*post[i]).isoformat()
                days[str(a)] = None if i is None else (dekad_start(*post[i]) - flood_day).days
                rec_rows.append({"definition": d["name"], "group": gname, "alpha": a, "recovered": recovered[str(a)], "days_after_flood": days[str(a)]})
            sv = {x["name"]: season_value(raw[gname], ctrl["ratio"].to_numpy(), post_dates, x["start"], x["end"], int(se["min_periods"])) for x in season_list}
            for x in season_list:
                season_rows.append({"definition": d["name"], "group": gname, "season": x["name"], "greenness_vs_normal": sv[x["name"]][0], "ten_day_periods": sv[x["name"]][1]})
            groups_out[gname] = {**info[gname], "seasons": {n: v[0] for n, v in sv.items()}, "lowest_ratio": None if lowest is None else float(arr[lowest]), "lowest_date": None if lowest is None else dekad_start(*post[lowest]).isoformat(), "recovered": recovered, "days": days}
        gaps = None
        a_name, b_name = "Flooded, more older residents", "Flooded, fewer older residents"
        if a_name in groups_out and b_name in groups_out:
            horizon = (dekad_start(*post[-1]) - flood_day).days + 10
            gaps = {}
            for a in alphas:
                da, db = groups_out[a_name]["days"][str(a)], groups_out[b_name]["days"][str(a)]
                gaps[str(a)] = None if da is None and db is None else (horizon if da is None else da) - (horizon if db is None else db)
            gaps_all.extend(gaps.values())
        defs_out.append({"key": k, "name": d["name"], "groups": groups_out, "stable": finding.stable, "orders": [list(o) for o in finding.orders], "older_gap_days": gaps})
    unc = cfg["uncertainty"]
    reps = int(unc["replicates"])
    rng = np.random.default_rng(int(unc["seed"]))
    green_groups = {d["key"]: {gn: [c for c in idx if c in green] for gn, idx in groups_by_def[d["key"]].items() if len([c for c in idx if c in green]) >= g["min_cells"]} for d in cfg["definitions"]}
    gmats, gweights = {}, {}
    for kd, gs in green_groups.items():
        for gn, idx in gs.items():
            P, B = matrices(dek, base, idx, post)
            pr, valid = point_ratio(P, B, float(rc["min_coverage"]), min_base)
            W = poisson_weights(rng, reps, len(idx))
            gmats[(kd, gn)] = (pr, replicate_ratio(P, valid, B, W))
    ring_rows, sens = [], []
    for r in rings:
        cc = [c for c in controls[tuple(r)] if c in green]
        P, B = matrices(dek, base, cc, post)
        cpr, cvalid = point_ratio(P, B, float(rc["min_coverage"]), min_base)
        crep = replicate_ratio(P, cvalid, B, poisson_weights(rng, reps, len(cc)))
        ring_name = f"{r[0] / 1000:g} to {r[1] / 1000:g} km"
        for dd in cfg["definitions"]:
            for gn in green_groups[dd["key"]]:
                gp, grep_ = gmats[(dd["key"], gn)]
                for x in season_list:
                    pt, rp, nper = season_with_interval(gp, grep_, cpr, crep, post_dates, x["start"], x["end"], int(se["min_periods"]))
                    ring_rows.append({"ring": ring_name, "definition": dd["name"], "group": gn, "season": x["name"], "value": pt, "interval": interval(rp), "periods": nper, "_rep": rp})
        sens.append({"ring": ring_name, "control_cells": len(cc)})
    def find(ring, dname, gn, season):
        for row in ring_rows:
            if row["ring"] == ring and row["definition"] == dname and row["group"] == gn and row["season"] == season:
                return row
        return None
    comparisons = []
    tol = float(se["tolerance"])
    for cmp_ in cfg.get("comparisons", []):
        for x in se["compare"]:
            diffs = []
            for dd in defs_out:
                ga, gb = dd["groups"].get(cmp_["a"]), dd["groups"].get(cmp_["b"])
                va = None if ga is None else ga["seasons"].get(x)
                vb = None if gb is None else gb["seasons"].get(x)
                diffs.append(None if va is None or vb is None else va - vb)
            cells_out, pts, ivs = [], [], []
            for sr in sens:
                for dd in cfg["definitions"]:
                    ra, rb = find(sr["ring"], dd["name"], cmp_["a"], x), find(sr["ring"], dd["name"], cmp_["b"], x)
                    if ra is None or rb is None or ra["value"] is None or rb["value"] is None:
                        pts.append(None)
                        ivs.append(None)
                        cells_out.append({"ring": sr["ring"], "definition": dd["name"], "difference": None, "interval": None})
                        continue
                    dp = ra["value"] - rb["value"]
                    iv = interval(ra["_rep"] - rb["_rep"])
                    pts.append(dp)
                    ivs.append(iv)
                    cells_out.append({"ring": sr["ring"], "definition": dd["name"], "difference": dp, "interval": iv})
            comparisons.append({"a": cmp_["a"], "b": cmp_["b"], "season": x, "differences": diffs, "verdict_point": compare(diffs, tol), "detail": cells_out, "verdict": verdict(pts, ivs, tol)})
    for row in ring_rows:
        row.pop("_rep", None)
    summary = {
        "collection": st["collection"],
        "control_rings": sens,
        "replicates": reps,
        "season_intervals": ring_rows,
        "seasons": season_list,
        "season_min_periods": int(se["min_periods"]),
        "season_tolerance": tol,
        "comparisons": comparisons,
        "recovery_start": rc["recovery_start"],
        "baseline_years": years,
        "flood_date": per["flood_date"],
        "control_ring_km": [x / 1000 for x in g["control_ring_m"]],
        "control_cells": len(control),
        "scenes_by_year": {c["check"]: c["by_year"] for c in checks},
        "min_baseline_ndvi": min_base,
        "min_cell_ndvi": float(rc["min_cell_ndvi"]),
        "groups_left_out": skipped_groups,
        "items_listed": len(inventory),
        "items_used": int(obs["item"].nunique()) if len(obs) else 0,
        "items_failed": failed,
        "items_excluded": sum(1 for i in inventory if i.get("excluded_offset_check")),
        "persistence": int(rc["persistence"]),
        "max_gap": int(rc["max_gap"]),
        "alphas": alphas,
        "definitions": defs_out,
        "direction": direction(gaps_all) if gaps_all else "no data",
    }
    sources = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stac": st["url"],
        "collection": st["collection"],
        "bbox": bbox,
        "periods": per,
        "cells_file": cfg["cells"]["path"],
        "study_cells": len(study),
        "pixel_size_m": px["resolution_m"],
        "valid_scene_classes": px["valid_classes"],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2, default=str) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(report(summary), encoding="utf-8")
    with pd.ExcelWriter(out_dir / "thriving.xlsx", engine="openpyxl") as xl:
        pd.DataFrame(season_rows).to_excel(xl, sheet_name="Seasons", index=False)
        pd.DataFrame([{**{k2: v2 for k2, v2 in r_.items() if k2 != "interval"}, "low": None if r_["interval"] is None else r_["interval"][0], "high": None if r_["interval"] is None else r_["interval"][1]} for r_ in ring_rows]).to_excel(xl, sheet_name="Seasons with intervals", index=False)
        pd.DataFrame([{"comparison": f"{c['a']} against {c['b']}", "season": c["season"], "verdict": c["verdict"], **{k2: v2 for k2, v2 in dt.items() if k2 != "interval"}, "low": None if dt["interval"] is None else dt["interval"][0], "high": None if dt["interval"] is None else dt["interval"][1]} for c in comparisons for dt in c["detail"]]).to_excel(xl, sheet_name="Comparisons in detail", index=False)
        pd.DataFrame([{**{k2: v2 for k2, v2 in c.items() if k2 not in ("differences", "detail")}, **{f"difference, {dd['name']}": v for dd, v in zip(defs_out, c["differences"])}} for c in comparisons]).to_excel(xl, sheet_name="Comparisons", index=False)
        pd.DataFrame(rec_rows).to_excel(xl, sheet_name="Recovery", index=False)
        pd.DataFrame(series_rows).to_excel(xl, sheet_name="Ten-day series", index=False)
        pd.DataFrame([{"definition": d["name"], "group": gn, **{k2: v2 for k2, v2 in gr.items() if k2 not in ("recovered", "days")}} for d in defs_out for gn, gr in d["groups"].items()]).to_excel(xl, sheet_name="Groups", index=False)
        pd.DataFrame(inventory).to_excel(xl, sheet_name="Scenes", index=False)
        pd.DataFrame([{"field": k2, "value": json.dumps(v2, default=str) if isinstance(v2, (list, dict, tuple)) else v2} for k2, v2 in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    return summary
