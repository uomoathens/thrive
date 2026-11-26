import io
import json
import re
import tempfile
import tomllib
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from thrive.data.download import Fetcher, fetch, fetch_to_file

GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF,.tiff",
    "GDAL_HTTP_MAX_RETRY": "5",
    "GDAL_HTTP_RETRY_DELAY": "3",
    "VSI_CACHE": "TRUE",
}

RASTER_EXT = (".tif", ".tiff", ".nc", ".nc4", ".zip")
HREF = re.compile(r'href="([^"]+)"', re.I)
SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*([KMGT]?)\s*$")
DATE_PATTERNS = (
    (re.compile(r"(?<!\d)(19|20)(\d{2})[-_]?(0[1-9]|1[0-2])[-_]?(0[1-9]|[12]\d|3[01])(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(19|20)(\d{2})[-_]?(0[1-9]|1[0-2])(?!\d)"), "ym"),
    (re.compile(r"(?<!\d)(19|20)(\d{2})(?!\d)"), "y"),
)


def load_config(path: Path) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def parse_index(html: str, base: str) -> list[dict]:
    out, seen = [], set()
    for href in HREF.findall(html):
        if href.startswith(("?", "#", "mailto:")) or href in ("../", "./", "/"):
            continue
        url = urllib.parse.urljoin(base, href)
        if not url.startswith(base) or url == base or url in seen:
            continue
        seen.add(url)
        name = urllib.parse.unquote(url[len(base):].rstrip("/"))
        if not name or "/" in name:
            continue
        out.append({"name": name, "url": url, "is_dir": href.endswith("/")})
    sizes = parse_sizes(html)
    for row in out:
        row["size_bytes"] = sizes.get(row["name"])
    return out


def parse_sizes(html: str) -> dict:
    sizes = {}
    for line in re.split(r"</tr>|\n", html):
        m = HREF.search(line)
        if not m:
            continue
        name = urllib.parse.unquote(m.group(1).rstrip("/").split("/")[-1])
        text = re.sub(r"<[^>]+>", " ", line)
        text = re.sub(r"\s+", " ", text).strip()
        tail = text.split(" ")[-1] if text else ""
        s = SIZE.match(tail)
        if s and not tail.endswith("-"):
            sizes[name] = to_bytes(s.group(1), s.group(2))
    return sizes


def to_bytes(number: str, unit: str) -> int:
    scale = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}[unit.upper()]
    return int(float(number) * scale)


def crawl(url: str, fetcher: Fetcher, max_depth: int, path: str = "") -> list[dict]:
    if not url.endswith("/"):
        url += "/"
    entries = parse_index(fetcher(url).decode("utf-8", "replace"), url)
    files = []
    for e in entries:
        rel = f"{path}{e['name']}"
        if e["is_dir"]:
            if max_depth > 0:
                files += crawl(e["url"], fetcher, max_depth - 1, rel + "/")
        else:
            files.append({**e, "path": rel})
    return files


def dates_in(name: str) -> list[tuple[str, date]]:
    for pattern, kind in DATE_PATTERNS:
        found = []
        for m in pattern.finditer(name):
            y = int(m.group(1) + m.group(2))
            try:
                if kind == "ymd":
                    found.append((kind, date(y, int(m.group(3)), int(m.group(4)))))
                elif kind == "ym":
                    found.append((kind, date(y, int(m.group(3)), 1)))
                else:
                    found.append((kind, date(y, 1, 1)))
            except ValueError:
                continue
        if found:
            return found
    return []


def years_covered(files: list[dict], first: int, last: int) -> dict:
    counts = {y: 0 for y in range(first, last + 1)}
    for f in files:
        for _, d in dates_in(f["path"]):
            if d.year in counts:
                counts[d.year] += 1
                break
    return counts


def pick_sample(files: list[dict], target: date, max_bytes: int) -> dict | None:
    rank = {".tif": 0, ".tiff": 0, ".nc": 1, ".nc4": 1, ".zip": 2}
    best, best_key = None, None
    for f in files:
        ext = Path(f["name"]).suffix.lower()
        if ext not in rank:
            continue
        if f.get("size_bytes") and f["size_bytes"] > max_bytes:
            continue
        ds = dates_in(f["path"])
        if not ds:
            continue
        kind, d = ds[0]
        if kind == "y":
            gap = 0 if d.year == target.year else abs(d.year - target.year) * 365
        elif kind == "ym":
            gap = 0 if (d.year, d.month) == (target.year, target.month) else abs((d - target).days)
        else:
            gap = abs((d - target).days)
        key = (gap, rank[ext], f.get("size_bytes") or 0)
        if best_key is None or key < best_key:
            best, best_key = f, key
    return best


def window_stats(arr: np.ndarray, nodata) -> dict:
    a = np.asarray(arr, dtype="float64")
    valid = np.isfinite(a)
    if nodata is not None and np.isfinite(nodata):
        valid &= a != nodata
    v = a[valid]
    out = {"pixels": int(a.size), "valid_share": float(valid.mean()) if a.size else 0.0}
    if v.size:
        out.update({"min": float(v.min()), "mean": float(v.mean()), "max": float(v.max())})
    else:
        out.update({"min": None, "mean": None, "max": None})
    return out


def read_bbox(path: Path, bbox: list[float]) -> dict:
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds

    targets = [str(path)]
    if path.suffix.lower() in (".nc", ".nc4"):
        with rasterio.open(str(path)) as ds:
            subs = list(ds.subdatasets)
        if subs:
            targets = subs
    results = []
    for t in targets[:6]:
        with rasterio.open(t) as ds:
            crs = ds.crs or "EPSG:4326"
            b = transform_bounds("EPSG:4326", crs, *bbox) if str(crs) != "EPSG:4326" else bbox
            win = from_bounds(*b, transform=ds.transform).round_offsets().round_lengths()
            arr = ds.read(1, window=win, boundless=True, fill_value=np.nan if ds.dtypes[0].startswith("float") else 0)
            res = ds.res
            results.append({
                "layer": t.split(":")[-1],
                "crs": str(crs),
                "res": f"{res[0]:.5g} x {res[1]:.5g}",
                "bands": ds.count,
                "band_names": ", ".join(d for d in (ds.descriptions or ()) if d)[:200],
                **window_stats(arr, ds.nodata),
            })
    return {"layers": results}


def sample_indicator(entry: dict, sample: dict | None, bbox: list[float], workdir: Path) -> dict:
    if sample is None:
        return {"indicator": entry["key"], "sample": None, "ok": False, "error": "no file with a date and an accepted format under the size limit"}
    local = workdir / sample["name"]
    try:
        fetch_to_file(sample["url"], local)
        target = local
        if local.suffix.lower() == ".zip":
            with zipfile.ZipFile(local) as z:
                inner = [n for n in z.namelist() if Path(n).suffix.lower() in (".tif", ".tiff", ".nc", ".nc4")]
                if not inner:
                    raise ValueError("the zip holds no GeoTIFF or NetCDF")
                z.extract(inner[0], workdir)
                target = workdir / inner[0]
        stats = read_bbox(target, bbox)
        return {"indicator": entry["key"], "sample": sample["path"], "ok": True, "error": None, **stats}
    except Exception as exc:
        return {"indicator": entry["key"], "sample": sample["path"], "ok": False, "error": f"{type(exc).__name__}: {exc}"[:400]}
    finally:
        for p in workdir.iterdir():
            if p.is_file():
                p.unlink()


def probe_edo(cfg: dict, bbox: list[float], fetcher: Fetcher, workdir: Path) -> tuple[pd.DataFrame, list[dict]]:
    e = cfg["edo"]
    first, last = e["years"]
    target = date.fromisoformat(e["sample_date"])
    rows, samples = [], []
    for ind in e["indicator"]:
        url = e["base"] + ind["dir"] + "/"
        try:
            files = crawl(url, fetcher, e["max_depth"])
            error = None
        except Exception as exc:
            files, error = [], f"{type(exc).__name__}: {exc}"[:400]
        rasters = [f for f in files if Path(f["name"]).suffix.lower() in RASTER_EXT]
        covered = years_covered(rasters, first, last)
        exts = sorted({Path(f["name"]).suffix.lower() for f in rasters})
        rows.append({
            "indicator": ind["key"],
            "name": ind["name"],
            "directory": url,
            "listing_error": error,
            "files": len(files),
            "raster_files": len(rasters),
            "formats": ", ".join(exts),
            **{str(y): covered[y] for y in covered},
            "all_years_present": all(covered[y] > 0 for y in covered),
        })
        sample = pick_sample(rasters, target, int(e["max_sample_mb"]) * 1024 ** 2)
        samples.append(sample_indicator(ind, sample, bbox, workdir))
    return pd.DataFrame(rows), samples


def region_geometry(cfg: dict, fetcher: Fetcher):
    import geopandas as gpd

    raw = fetcher(cfg["region"]["nuts_url"])
    gdf = gpd.read_file(io.BytesIO(raw))
    sel = gdf[gdf["NUTS_ID"] == cfg["region"]["nuts2"]]
    if sel.empty:
        raise ValueError(f"{cfg['region']['nuts2']} not found in the NUTS file")
    return sel.to_crs(4326).geometry.iloc[0]


def tif_header(url: str) -> dict:
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.Env(**GDAL_ENV), rasterio.open("/vsicurl/" + url) as ds:
        b = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)
        return {"url": url, "crs": str(ds.crs), "bounds4326": b, "width": ds.width, "height": ds.height, "res": ds.res, "tiled": bool(ds.profile.get("tiled"))}


def intersects(b: tuple, bbox: list[float]) -> bool:
    return not (b[2] < bbox[0] or b[0] > bbox[2] or b[3] < bbox[1] or b[1] > bbox[3])


def class_counts(url: str, geom4326) -> dict:
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    from rasterio.windows import from_bounds
    from shapely.geometry import mapping, shape

    with rasterio.Env(**GDAL_ENV), rasterio.open("/vsicurl/" + url) as ds:
        g = shape(transform_geom("EPSG:4326", ds.crs, mapping(geom4326)))
        minx, miny, maxx, maxy = g.bounds
        minx, miny = max(minx, ds.bounds.left), max(miny, ds.bounds.bottom)
        maxx, maxy = min(maxx, ds.bounds.right), min(maxy, ds.bounds.top)
        if minx >= maxx or miny >= maxy:
            return {}
        win = from_bounds(minx, miny, maxx, maxy, transform=ds.transform).round_offsets().round_lengths()
        arr = ds.read(1, window=win)
        tr = ds.window_transform(win)
        inside = ~geometry_mask([mapping(g)], out_shape=arr.shape, transform=tr)
        vals = arr[inside].astype("int64")
        if not vals.size:
            return {}
        counts = np.bincount(vals)
        pixel_m2 = abs(ds.res[0] * ds.res[1])
        return {int(k): int(c) * pixel_m2 / 1e4 for k, c in enumerate(counts) if c}


def probe_cropmap(cfg: dict, geom4326, fetcher: Fetcher) -> tuple[pd.DataFrame, dict]:
    c = cfg["cropmap"]
    bbox = list(geom4326.bounds)
    files = crawl(c["base"], fetcher, c["max_depth"])
    tifs = [f for f in files if Path(f["name"]).suffix.lower() in (".tif", ".tiff")]
    with ThreadPoolExecutor(max_workers=int(c["header_workers"])) as pool:
        heads = list(pool.map(lambda f: _safe(tif_header, f["url"]), tifs))
    good = [h for h in heads if "error" not in h]
    hits = [h for h in good if intersects(h["bounds4326"], bbox)]
    if c.get("prefer_tiles", True):
        tiled = [h for h in hits if "/tiles/" in h["url"]]
        if tiled:
            hits = tiled
    totals: dict = {}
    errors = [h for h in heads if "error" in h]
    for h in hits:
        part = _safe(class_counts, h["url"], geom4326)
        if isinstance(part, dict) and "error" in part:
            errors.append(part)
            continue
        for k, v in part.items():
            totals[k] = totals.get(k, 0.0) + v
    names = {int(k): v for k, v in c["classes"].items()}
    rows = [{"class": k, "name": names.get(k, "unknown"), "hectares": round(v, 1)} for k, v in sorted(totals.items())]
    meta = {"tif_files": len(tifs), "headers_read": len(good), "files_over_region": len(hits), "files_used": [h["url"] for h in hits][:50], "errors": errors[:20]}
    return pd.DataFrame(rows, columns=["class", "name", "hectares"]), meta


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"[:300], "args": [str(a)[:200] for a in args]}


def eurostat_crops(cfg: dict, fetcher: Fetcher) -> tuple[pd.DataFrame, dict]:
    e = cfg["eurostat"]
    params = [("format", "JSON"), ("lang", "EN"), ("geo", cfg["region"]["nuts2"]), ("strucpro", e["strucpro"]), ("sinceTimePeriod", str(e["since"]))]
    url = e["api"].format(code=e["code"]) + "?" + urllib.parse.urlencode(params)
    payload = json.loads(fetcher(url))
    ids, sizes = payload["id"], payload["size"]
    cats, labels = [], {}
    for dim in ids:
        cat = payload["dimension"][dim]["category"]
        index = cat["index"]
        cats.append(sorted(index, key=index.get) if isinstance(index, dict) else list(index))
        labels[dim] = cat.get("label", {})
    strides = np.cumprod([1] + sizes[::-1][:-1])[::-1]
    values = payload.get("value", {})
    items = values.items() if isinstance(values, dict) else ((i, v) for i, v in enumerate(values) if v is not None)
    rows = []
    for key, value in items:
        if value is None:
            continue
        pos = int(key)
        row = {dim: cs[(pos // int(s)) % n] for dim, s, n, cs in zip(ids, strides, sizes, cats)}
        row["label"] = labels.get("crops", {}).get(row.get("crops"), "")
        row["thousand_ha"] = float(value)
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame, {"url": url, "updated": payload.get("updated"), "label": payload.get("label")}


def compare(classes: pd.DataFrame, crops: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    out = []
    year = str(cfg["compare"]["year"])
    for pair in cfg["compare"]["pair"]:
        map_ha = float(classes.loc[classes["class"].isin(pair["classes"]), "hectares"].sum()) if not classes.empty else 0.0
        stat = crops[crops["label"].str.contains(pair["label_contains"], case=False, regex=False)] if not crops.empty else crops
        stat_year = stat[stat["time"] == year] if not stat.empty and "time" in stat else stat
        stat_ha = float(stat_year["thousand_ha"].max() * 1000) if not stat_year.empty else None
        ratio = map_ha / stat_ha if stat_ha else None
        tol = float(cfg["compare"]["tolerance"])
        out.append({
            "crop": pair["name"],
            "map_classes": ", ".join(str(c) for c in pair["classes"]),
            "map_hectares": round(map_ha, 0),
            "eurostat_label": ", ".join(sorted(set(stat_year["label"]))) if not stat_year.empty else None,
            "eurostat_year": year,
            "eurostat_hectares": round(stat_ha, 0) if stat_ha else None,
            "map_to_eurostat": round(ratio, 2) if ratio else None,
            "within_tolerance": bool(ratio and abs(ratio - 1) <= tol),
        })
    return pd.DataFrame(out)


def verdicts(edo: pd.DataFrame, samples: list[dict], cmp: pd.DataFrame, cfg: dict) -> dict:
    needed = cfg["edo"]["needed"]
    ok_list = set(edo.loc[edo["all_years_present"], "indicator"]) & {s["indicator"] for s in samples if s["ok"]}
    q1 = all(k in ok_list for k in needed)
    cotton = cmp[cmp["crop"] == cfg["compare"]["cotton_name"]]
    q2 = bool(not cotton.empty and cotton["within_tolerance"].iloc[0])
    return {"edo_ready": q1, "edo_ready_indicators": sorted(ok_list), "cotton_mapped": q2}


def write_report(out: Path, edo, samples, classes, cmeta, crops, emeta, cmp, verdict, cfg) -> None:
    def table(df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return "_No rows._\n"
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join("" if pd.isna(r[c]) else str(r[c]) for c in cols) + " |")
        return "\n".join(lines) + "\n"

    lines = [
        "# Heat, drought and crops in Thessaly: feasibility probe",
        "",
        "Generated automatically by `thrive crops-probe`. It checks, before any analysis, whether the open European data needed for a study of heat and drought damage to crops in Thessaly can be downloaded automatically and whether cotton can be separated in the EU crop map. It produces no finding about crops.",
        "",
        "## Verdicts",
        "",
        f"1. European Drought Observatory data download automatically for every needed indicator and every year: **{'yes' if verdict['edo_ready'] else 'no'}** (ready: {', '.join(verdict['edo_ready_indicators']) or 'none'}).",
        f"2. Cotton area in the EU crop map 2022 matches the Eurostat cotton area of Thessaly within ±{int(float(cfg['compare']['tolerance']) * 100)}%: **{'yes' if verdict['cotton_mapped'] else 'no'}**.",
        "3. Whether heat stress can be separated from irrigation at field scale needs Sentinel-2 at 10 to 40 m and is the next step; the drought indicators here are about 5 km, coarser than the fields.",
        "",
        "## 1. European Drought Observatory files, by year",
        "",
        table(edo),
        "### Sample read over Thessaly",
        "",
    ]
    for s in samples:
        lines.append(f"- **{s['indicator']}**: {s.get('sample') or 'no sample'}; " + ("read" if s["ok"] else f"failed: {s['error']}"))
        for layer in s.get("layers", []):
            lines.append(f"  - {layer['layer']}: CRS {layer['crs']}, pixel {layer['res']}, {layer['pixels']} pixels, valid {layer['valid_share']:.0%}, min {layer['min']}, mean {layer['mean']}, max {layer['max']}")
    lines += ["", "## 2. EU crop map 2022 over Thessaly (NUTS " + cfg["region"]["nuts2"] + ")", "", f"GeoTIFF files listed: {cmeta['tif_files']}; headers read: {cmeta['headers_read']}; files over Thessaly: {cmeta['files_over_region']}.", "", table(classes), "### Eurostat crop areas, Thessaly", "", f"Source: {emeta.get('label')} (updated {emeta.get('updated')}).", ""]
    lines += [table(crops), "### Crop map against Eurostat", "", table(cmp)]
    if cmeta["errors"]:
        lines += ["### Read errors", ""] + [f"- {e.get('error')}" for e in cmeta["errors"]]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, out: Path, fetcher: Fetcher = fetch) -> dict:
    cfg = load_config(config_path)
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    geom = region_geometry(cfg, fetcher)
    bbox = list(geom.bounds)
    with tempfile.TemporaryDirectory() as tmp:
        edo, samples = probe_edo(cfg, bbox, fetcher, Path(tmp))
    try:
        classes, cmeta = probe_cropmap(cfg, geom, fetcher)
    except Exception as exc:
        classes, cmeta = pd.DataFrame(columns=["class", "name", "hectares"]), {"tif_files": 0, "headers_read": 0, "files_over_region": 0, "files_used": [], "errors": [{"error": f"{type(exc).__name__}: {exc}"[:400]}]}
    try:
        crops, emeta = eurostat_crops(cfg, fetcher)
    except Exception as exc:
        crops, emeta = pd.DataFrame(columns=["crops", "time", "label", "thousand_ha"]), {"error": f"{type(exc).__name__}: {exc}"[:400]}
    cmp = compare(classes, crops, cfg)
    verdict = verdicts(edo, samples, cmp, cfg)
    sample_rows = []
    for s in samples:
        for layer in s.get("layers", []) or [{}]:
            sample_rows.append({"indicator": s["indicator"], "sample": s.get("sample"), "ok": s["ok"], "error": s.get("error"), **layer})
    with pd.ExcelWriter(out / "crops-probe.xlsx") as xl:
        edo.to_excel(xl, sheet_name="edo_files", index=False)
        pd.DataFrame(sample_rows).to_excel(xl, sheet_name="edo_samples", index=False)
        classes.to_excel(xl, sheet_name="crop_map_classes", index=False)
        crops.to_excel(xl, sheet_name="eurostat_crops", index=False)
        cmp.to_excel(xl, sheet_name="comparison", index=False)
    write_report(out, edo, samples, classes, cmeta, crops, emeta, cmp, verdict, cfg)
    summary = {"started": started, "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"), **verdict, "crop_map": {k: v for k, v in cmeta.items() if k != "errors"}, "eurostat": emeta}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return summary
