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
    lookup = np.full((rows, cols), -1, dtype=np.int64)
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
    obs = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["cell", "ndvi", "valid_share", "date", "item"])
    return obs, sorted(inventory, key=lambda x: (str(x["datetime"]), x["id"]))


def dekad_table(obs: pd.DataFrame) -> pd.DataFrame:
    if obs.empty:
        return pd.DataFrame(columns=["cell", "year", "k", "ndvi"])
    best = obs.sort_values("valid_share", ascending=False).drop_duplicates(["cell", "date"])
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


def control_cells(cells, g: dict) -> list[int]:
    widest = cells[[c for c in cells.columns if c.startswith("flooded_share_")]].max(axis=1)
    wet = cells[widest > 0]
    dry = cells[widest == 0]
    if wet.empty:
        return []
    zone = wet.geometry.union_all()
    outer, inner = zone.buffer(g["control_ring_m"][1]), zone.buffer(g["control_ring_m"][0])
    cent = dry.geometry.centroid
    keep = cent.within(outer) & ~cent.within(inner)
    return dry.index[keep].tolist()


def report(summary: dict) -> str:
    lines = [
        "# Thriving: when did the flooded land of Thessaly come back?",
        "",
        "Generated automatically by `thrive thriving`. `sources.json` records what was read and when.",
        "",
        f"Measure: greenness (NDVI) from Sentinel-2 ({summary['collection']}), per 1 km cell and per ten-day period, compared with the same period of {', '.join(str(y) for y in summary['baseline_years'])} in the same cell. Each group is divided by unflooded cells {summary['control_ring_km'][0]:g} to {summary['control_ring_km'][1]:g} km from the flood, so that a dry or wet year does not count as damage or recovery.",
        f"Images: {summary['items_used']} of {summary['items_listed']} scenes used ({summary['items_failed']} could not be read, {summary['items_excluded']} failed the reflectance check). Control: {summary['control_cells']} cells.",
        f"A group counts as recovered at a threshold α on the first of {summary['persistence']} ten-day periods in a row in which its greenness, relative to the control, is at least α of normal. Gaps of up to {summary['max_gap']} periods are interpolated.",
        f"Only ten-day periods in which the land is normally green count: the average greenness of the group in the years before must be at least {summary['min_baseline_ndvi']:.2f}. In autumn and winter the fields of the plain are bare even in a normal year, so a bare flooded field looks normal then and would count as recovered too early. Cells that are not green in a normal year at all (median below {summary['min_cell_ndvi']:.2f}: lakes, towns, bare ground) are left out.",
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
    for d in summary["definitions"]:
        lines += [f"## {d['name']}", "", "| Group | Cells | Residents | Lowest point | " + " | ".join(f"Recovered at {int(a * 100)}%" for a in summary["alphas"]) + " |", "| --- | --- | --- | --- | " + " | ".join("---" for _ in summary["alphas"]) + " |"]
        for gname, gr in d["groups"].items():
            low = "n/a" if gr["lowest_ratio"] is None else f"{gr['lowest_ratio']:.0%} ({gr['lowest_date']})"
            rec = ["not within the period" if gr["recovered"][str(a)] is None else f"{gr['recovered'][str(a)]} (day {gr['days'][str(a)]})" for a in summary["alphas"]]
            lines.append(f"| {gname} | {gr['cells']:,} | {gr['residents']:,.0f} | {low} | " + " | ".join(rec) + " |")
        lines += ["", f"Order of recovery the same under every threshold: **{'yes' if d['stable'] else 'no'}**."]
        if d.get("older_gap_days") is not None:
            lines.append("Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: " + "; ".join(f"α {int(float(a) * 100)}%: {'n/a' if v is None else f'{v:+d}'}" for a, v in d["older_gap_days"].items()) + ".")
        lines.append("")
    lines += [
        f"Across every flood definition and threshold: **{summary['direction']}**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.",
        "",
        "## Limits",
        "",
        "Greenness measures fields and gardens coming back, not households: a farm can be green again while its owners are still waiting for help, and a village can be rebuilt on land that stays bare. Clouds remove many autumn and winter images, crops rotate between years, and farmers may have left fields fallow on purpose. The cells with more older residents are compared with those with fewer within the flooded area only, and both include the fields around each village.",
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
    control = control_cells(cells, g)
    if len(control) < g["min_cells"]:
        raise ValueError(f"only {len(control)} control cells found")
    needed = sorted(set(control).union(*[set(i) for gs in groups_by_def.values() for i in gs.values()]))
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
    series_rows, rec_rows, defs_out, gaps_all, skipped_groups = [], [], [], [], []
    for d in cfg["definitions"]:
        k = d["key"]
        rel, info = {}, {}
        for gname, idx_all in groups_by_def[k].items():
            idx = [c for c in idx_all if c in green]
            if len(idx) < g["min_cells"]:
                skipped_groups.append({"definition": d["name"], "group": gname, "cells": len(idx_all), "green_cells": len(idx)})
                continue
            s = group_series(dek, base, idx, post, float(rc["min_coverage"]), min_base)
            r = fill(pd.Series(s["ratio"].to_numpy() / ctrl["ratio"].to_numpy()), int(rc["max_gap"]))
            rel[gname] = r
            sub = cells.loc[idx]
            info[gname] = {"cells": len(idx), "cells_left_out_not_green": len(idx_all) - len(idx), "residents": float(sub["population"].sum()), "older_share": float(sub["older"].sum() / sub["population"].sum()) if sub["population"].sum() > 0 else None}
            for i, row in s.iterrows():
                series_rows.append({"definition": d["name"], "group": gname, "date": row["date"], "group_ratio": row["ratio"], "control_ratio": ctrl["ratio"].iloc[i], "relative": r.iloc[i], "coverage": row["coverage"], "control_coverage": ctrl["coverage"].iloc[i]})
        finding = robust_recovery({gname: v.to_numpy() for gname, v in rel.items()}, {gname: 1.0 for gname in rel}, alphas, int(rc["persistence"]))
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
            groups_out[gname] = {**info[gname], "lowest_ratio": None if lowest is None else float(arr[lowest]), "lowest_date": None if lowest is None else dekad_start(*post[lowest]).isoformat(), "recovered": recovered, "days": days}
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
    summary = {
        "collection": st["collection"],
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
        pd.DataFrame(rec_rows).to_excel(xl, sheet_name="Recovery", index=False)
        pd.DataFrame(series_rows).to_excel(xl, sheet_name="Ten-day series", index=False)
        pd.DataFrame([{"definition": d["name"], "group": gn, **{k2: v2 for k2, v2 in gr.items() if k2 not in ("recovered", "days")}} for d in defs_out for gn, gr in d["groups"].items()]).to_excel(xl, sheet_name="Groups", index=False)
        pd.DataFrame(inventory).to_excel(xl, sheet_name="Scenes", index=False)
        pd.DataFrame([{"field": k2, "value": json.dumps(v2, default=str) if isinstance(v2, (list, dict, tuple)) else v2} for k2, v2 in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    return summary
