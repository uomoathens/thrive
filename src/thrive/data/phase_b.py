import io
import json
import shutil
import tempfile
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from thrive.data.download import Fetcher, fetch, fetch_to_file, sha256

VECTOR_EXT = (".gpkg", ".geojson", ".json", ".shp", ".kml")


def load_config(path: Path) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def activation_products(detail_url: str, code: str, types, fetcher: Fetcher = fetch) -> tuple[dict, list[dict]]:
    payload = json.loads(fetcher(detail_url.format(code=code)))
    results = payload.get("results") or []
    if not results:
        raise ValueError(f"no Copernicus EMS activation found for {code}")
    act = results[0]
    wanted = {t.upper() for t in types}
    products = []
    for aoi in act.get("aois") or []:
        for p in aoi.get("products") or []:
            if str(p.get("type", "")).upper() in wanted and p.get("downloadPath") and p.get("feasible", True) is not False:
                products.append({
                    "aoi": aoi.get("number"),
                    "aoi_name": aoi.get("name"),
                    "type": p.get("type"),
                    "monitoring": p.get("monitoringNumber"),
                    "url": p["downloadPath"],
                })
    return act, products


def _one_per_layer(paths):
    chosen = {}
    for path in paths:
        key = str(path.with_suffix("")).lower()
        rank = VECTOR_EXT.index(path.suffix.lower())
        if key not in chosen or rank < chosen[key][0]:
            chosen[key] = (rank, path)
    return [p for _, p in sorted(chosen.values(), key=lambda x: str(x[1]))]


def _classes(gdf) -> dict:
    out = {}
    for col in gdf.columns:
        if col == "geometry" or gdf[col].dtype.kind not in "OUS":
            continue
        values = gdf[col].dropna().astype(str)
        if 0 < values.nunique() <= 12:
            out[col] = {k: int(v) for k, v in values.value_counts().items()}
    return out


def _polygons(path: Path, crs: int, class_columns=()):
    import geopandas as gpd

    gdf = gpd.read_file(path)
    if gdf.empty or gdf.crs is None:
        return None
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    if gdf.empty:
        return None
    col = _find(gdf.columns, class_columns) if class_columns else None
    gdf = gdf.assign(flood_class=gdf[col].fillna("").astype(str) if col else "")
    return gdf.to_crs(crs)


def flood_polygons(zip_bytes: bytes, words, crs: int, check_words=(), class_columns=()):
    found, layers, details, check = [], [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmp)
        files = [p for p in Path(tmp).rglob("*") if p.is_file() and p.suffix.lower() in VECTOR_EXT and not p.name.startswith(".")]
        for path in _one_per_layer(files):
            name = path.name.lower()
            layers.append(path.name)
            if any(w in name for w in words):
                gdf = _polygons(path, crs, class_columns)
                if gdf is not None:
                    found.append(gdf[["flood_class", "geometry"]])
                    details.append({"layer": path.name, "features": len(gdf), "classes": _classes(gdf)})
            elif any(w in name for w in check_words):
                gdf = _polygons(path, crs)
                if gdf is not None:
                    check.append(gdf[["geometry"]])
    return found, layers, details, check


def regions(geojson: bytes, prefix: str, crs: int, margin_m: float = 20000):
    import geopandas as gpd

    gdf = gpd.read_file(io.BytesIO(geojson))
    col = "NUTS_ID" if "NUTS_ID" in gdf.columns else "id"
    name = next((c for c in ("NAME_LATN", "NUTS_NAME", "NAME") if c in gdf.columns), col)
    gdf = gdf.rename(columns={col: "region_id", name: "region_name"})[["region_id", "region_name", "geometry"]].to_crs(crs)
    gdf["region_id"] = gdf["region_id"].astype(str)
    target = gdf[gdf["region_id"].str.startswith(prefix)].copy()
    if target.empty:
        raise ValueError(f"no regions with code starting {prefix}")
    minx, miny, maxx, maxy = target.total_bounds
    near = gdf.cx[minx - margin_m:maxx + margin_m, miny - margin_m:maxy + margin_m].copy()
    return target.reset_index(drop=True), near.reset_index(drop=True)


def grid_source(path: Path, cfg: dict, work: Path) -> tuple[Path, str | None, dict]:
    import pyogrio

    path = Path(path)
    info = {"file": path.name}
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(".gpkg")]
            info["zip_members"] = zf.namelist()
            if not members:
                raise ValueError(f"no GeoPackage inside {path.name}; it holds: {zf.namelist()}")
            for m in members:
                target = work / Path(m).name
                with zf.open(m) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                layer, cols = _layer_with(target, cfg["population"])
                if layer is not None:
                    info.update({"member": m, "layer": layer, "columns": cols})
                    return target, layer, info
                target.unlink()
        raise KeyError(f"no layer with a population column among {cfg['population']} in {members}")
    layer, cols = _layer_with(path, cfg["population"])
    if layer is None:
        raise KeyError(f"no layer with a population column among {cfg['population']} in {path.name}; layers: {pyogrio.list_layers(path).tolist()}")
    info.update({"layer": layer, "columns": cols})
    return path, layer, info


def _find(columns, names):
    lower = {str(c).lower(): c for c in columns}
    return next((lower[n.lower()] for n in names if n.lower() in lower), None)


def _layer_with(path: Path, names):
    import pyogrio

    for lname, _ in pyogrio.list_layers(path):
        cols = list(pyogrio.read_info(path, layer=lname)["fields"])
        if _find(cols, names) is not None:
            return lname, cols
    return None, []


def _count(series):
    v = pd.to_numeric(series, errors="coerce")
    return v.where(v >= 0)


def grid_cells(gpkg_path: Path, layer, area, cfg: dict, crs: int):
    import geopandas as gpd
    from shapely.geometry import box

    pad = float(cfg["cell_size_m"])
    minx, miny, maxx, maxy = area.total_bounds
    pts = gpd.read_file(gpkg_path, layer=layer, bbox=(minx - pad, miny - pad, maxx + pad, maxy + pad))
    if pts.crs is None or pts.crs.to_epsg() != crs:
        pts = pts.to_crs(crs)
    pop = _find(pts.columns, cfg["population"])
    if pop is None:
        raise KeyError(f"no population column among {cfg['population']}; columns are: {sorted(pts.columns)}")
    older = _find(pts.columns, cfg.get("older", []))
    if older is None and cfg.get("older_required", False):
        raise KeyError(f"no age column among {cfg.get('older')}; columns are: {sorted(pts.columns)}")
    half = float(cfg["cell_size_m"]) / 2
    if set(pts.geometry.geom_type) <= {"Point"}:
        geoms = [box(p.x - half, p.y - half, p.x + half, p.y + half) for p in pts.geometry]
    else:
        geoms = list(pts.geometry)
    population = _count(pts[pop])
    old = _count(pts[older]) if older else pd.Series(float("nan"), index=pts.index)
    cells = gpd.GeoDataFrame({
        "population": population.fillna(0.0).to_numpy(),
        "population_missing": population.isna().to_numpy(),
        "older": old.fillna(0.0).to_numpy(),
        "older_known": old.notna().to_numpy(),
    }, geometry=geoms, crs=crs)
    return cells, pop, older, sorted(pts.columns)


def exposure(cells, flood, target, near):
    import geopandas as gpd

    cells = cells.copy()
    cells["cell_id"] = range(len(cells))
    pieces = gpd.overlay(cells, near, how="intersection", keep_geom_type=True)
    pieces["piece_area"] = pieces.geometry.area
    land = pieces.groupby("cell_id")["piece_area"].sum()
    pieces["land_area"] = pieces["cell_id"].map(land)
    placed = set(pieces["cell_id"])
    target_ids = set(target["region_id"])
    near_target = cells[cells.intersects(target.buffer(1500).union_all())]
    unplaced = near_target[~near_target["cell_id"].isin(placed)]
    pieces = pieces[pieces["region_id"].isin(target_ids)].copy()
    flood_union = gpd.GeoDataFrame(geometry=[flood.union_all()], crs=cells.crs)
    pieces["piece_id"] = range(len(pieces))
    wet = gpd.overlay(pieces[["piece_id", "geometry"]], flood_union, how="intersection", keep_geom_type=True)
    wet_area = wet.assign(a=wet.geometry.area).groupby("piece_id")["a"].sum()
    pieces["wet_area"] = pieces["piece_id"].map(wet_area).fillna(0.0)
    pieces["wet_area"] = pieces[["wet_area", "piece_area"]].min(axis=1)
    k = pieces["piece_area"] / pieces["land_area"]
    w = pieces["wet_area"] / pieces["land_area"]
    known = pieces["older_known"].astype(bool)
    pieces["population_in_region"] = pieces["population"] * k
    pieces["population_exposed"] = pieces["population"] * w
    pieces["population_with_age"] = (pieces["population"] * k).where(known, 0.0)
    pieces["population_exposed_with_age"] = (pieces["population"] * w).where(known, 0.0)
    pieces["older_in_region"] = (pieces["older"] * k).where(known, 0.0)
    pieces["older_exposed"] = (pieces["older"] * w).where(known, 0.0)
    pieces["flooded_km2"] = pieces["wet_area"] / 1e6
    pieces["land_km2"] = pieces["piece_area"] / 1e6
    pieces["missing_population_cell"] = pieces["population_missing"].astype(bool)
    by_region = pieces.groupby(["region_id", "region_name"]).agg(
        population=("population_in_region", "sum"),
        population_exposed=("population_exposed", "sum"),
        population_with_age=("population_with_age", "sum"),
        population_exposed_with_age=("population_exposed_with_age", "sum"),
        older=("older_in_region", "sum"),
        older_exposed=("older_exposed", "sum"),
        land_km2=("land_km2", "sum"),
        flooded_km2=("flooded_km2", "sum"),
        cells=("cell_id", "nunique"),
        cells_flooded=("wet_area", lambda s: int((s > 0).sum())),
        cells_missing_population=("missing_population_cell", "sum"),
    ).reset_index()
    add_shares(by_region)
    cells_out = pieces[pieces["wet_area"] > 0].assign(
        flooded_share_of_land=lambda d: d["wet_area"] / d["land_area"],
        older_known=lambda d: d["older_known"].astype(bool),
    )[["cell_id", "region_id", "region_name", "population", "older", "older_known", "land_km2", "flooded_km2", "flooded_share_of_land", "population_exposed", "older_exposed"]]
    per_cell = pieces.sort_values("piece_area", ascending=False).groupby("cell_id").agg(
        region_id=("region_id", "first"),
        region_name=("region_name", "first"),
        land_km2=("land_km2", "sum"),
        flooded_km2=("flooded_km2", "sum"),
    )
    per_cell["flooded_share"] = (per_cell["flooded_km2"] / per_cell["land_km2"].where(per_cell["land_km2"] > 0)).fillna(0.0).clip(upper=1.0)
    return by_region, cells_out, float(unplaced["population"].sum()), int(len(unplaced)), per_cell


def add_shares(df):
    def div(a, b):
        return a / b.where(b > 0)

    df["share_exposed"] = div(df["population_exposed"], df["population"])
    df["age_coverage"] = div(df["population_with_age"], df["population"])
    df["older_share_of_population"] = div(df["older"], df["population_with_age"])
    df["older_share_of_exposed"] = div(df["older_exposed"], df["population_exposed_with_age"])
    df["older_exposure_ratio"] = div(df["older_share_of_exposed"], df["older_share_of_population"])
    return df


def validation(by_region: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    ref = cfg.get("population", {})
    rows = []
    for r in by_region.itertuples():
        official = ref.get(r.region_id)
        rows.append({
            "region_id": r.region_id,
            "region_name": r.region_name,
            "grid_population": r.population,
            "census_population": official,
            "difference": None if official is None else r.population - official,
            "difference_share": None if not official else (r.population - official) / official,
        })
    return pd.DataFrame(rows)


def _pct(x, digits=1):
    return "n/a" if x is None or pd.isna(x) else f"{x:.{digits}%}"


def direction(ratios, tolerance: float = 1e-6) -> str:
    vals = [r for r in ratios if r is not None and not pd.isna(r)]
    if not vals:
        return "no data"
    if all(r > 1 + tolerance for r in vals):
        return "older people more exposed"
    if all(r < 1 - tolerance for r in vals):
        return "older people less exposed"
    return "not robust"


def extent_summary(by_region: pd.DataFrame, min_exposed: float) -> dict:
    sums = ["population", "population_exposed", "population_with_age", "population_exposed_with_age", "older", "older_exposed", "land_km2", "flooded_km2"]
    total = add_shares(pd.DataFrame([by_region[sums].sum()])).iloc[0]
    out = {k: float(total[k]) for k in sums}
    for k in ("share_exposed", "age_coverage", "older_share_of_population", "older_share_of_exposed", "older_exposure_ratio"):
        out[k] = None if pd.isna(total[k]) else float(total[k])
    out["region_ratios"] = {
        r.region_id: (None if r.population_exposed_with_age < min_exposed or pd.isna(r.older_exposure_ratio) else float(r.older_exposure_ratio))
        for r in by_region.itertuples()
    }
    return out


def report(summary: dict, by_region: pd.DataFrame, check: pd.DataFrame, sources: dict, notes: dict) -> str:
    age = sources["older_column"]
    ext = summary["extents"]
    main = ext[0]
    lines = [
        "# Phase B: who was in the water of Storm Daniel?",
        "",
        "Generated automatically by `thrive phase-b`. `sources.json` records what was downloaded and when.",
        "",
        f"Flood extent: the Copernicus EMS {sources['activation']} products ({sources['products_used']} products, {sources['flood_layers_used']} flood layers, each read once), merged over every date the satellites passed. The main table uses the first definition below; the others follow it.",
        f"Population: {sources['grid_name']}, column `{sources['population_column']}`" + (f"; people aged 65 and over from `{age}`." if age else "; the grid has no age column, so older people are not counted."),
        "",
        f"## Main result: {main['name']}",
        "",
        "| Regional unit | Residents | Flooded area (km²) | Residents in flooded parts of cells | Share of residents | Aged 65+ among all residents | Aged 65+ among those exposed | Ratio |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in by_region.itertuples():
        ratio = main["region_ratios"].get(r.region_id)
        lines.append(f"| {r.region_name} | {r.population:,.0f} | {r.flooded_km2:,.1f} | {r.population_exposed:,.0f} | {_pct(r.share_exposed)} | {_pct(r.older_share_of_population) if age else 'n/a'} | {_pct(r.older_share_of_exposed) if age else 'n/a'} | {'too few exposed' if ratio is None else f'{ratio:.2f}'} |")
    lines += [
        "",
        f"Thessaly in total: {main['population_exposed']:,.0f} of {main['population']:,.0f} residents ({_pct(main['share_exposed'])}) lived in the parts of 1 km cells inside this extent, over {main['flooded_km2']:,.0f} km².",
    ]
    if age:
        lines += [
            "",
            f"The ratio compares the share of people aged 65 and over among those exposed with their share among all residents. Above 1, older people were more likely than the average resident to live where the water reached. A regional unit with fewer than {notes['min_exposed']:,.0f} people exposed gets no ratio. The age count covers {_pct(main['age_coverage'])} of the population.",
        ]
    lines += [
        "",
        "## The same question under each flood definition",
        "",
        "| Flood definition | Flooded area in Thessaly (km²) | Residents exposed | Share of residents | Ratio, Thessaly | " + " | ".join(f"Ratio, {n}" for n in by_region["region_name"]) + " |",
        "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in by_region["region_name"]) + " |",
    ]
    for e in ext:
        cells = [("too few exposed" if e["region_ratios"].get(rid) is None else f"{e['region_ratios'][rid]:.2f}") for rid in by_region["region_id"]]
        ratio = "n/a" if e["older_exposure_ratio"] is None else f"{e['older_exposure_ratio']:.2f}"
        lines.append(f"| {e['name']} | {e['flooded_km2']:,.0f} | {e['population_exposed']:,.0f} | {_pct(e['share_exposed'])} | {ratio} | " + " | ".join(cells) + " |")
    if age:
        lines += [
            "",
            f"Direction for Thessaly as a whole, across all definitions: **{summary['direction_thessaly']}**. Direction inside the regional units, across all definitions and every unit with enough people exposed: **{summary['direction_within_units']}**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.",
            "",
            "Direction in each regional unit, across all definitions: " + "; ".join(f"{n}: **{summary['direction_by_unit'][rid]}**" for rid, n in zip(by_region["region_id"], by_region["region_name"])) + ".",
        ]
    lines += ["", "## Checks", "", "| Regional unit | Residents on the grid | Census 2021 (ELSTAT) | Difference |", "| --- | --- | --- | --- |"]
    for r in check.itertuples():
        census = "n/a" if pd.isna(r.census_population) else f"{r.census_population:,.0f}"
        diff = "n/a" if pd.isna(r.difference) else f"{r.difference:+,.0f} ({r.difference_share:+.1%})"
        lines.append(f"| {r.region_name} | {r.grid_population:,.0f} | {census} | {diff} |")
    lines += [
        "",
        f"Population on the grid near Thessaly that fell in no regional unit (cells at sea or on islets the 1:1 million boundaries leave out): {notes['unplaced_population']:,.0f} residents in {notes['unplaced_cells']} cells.",
    ]
    if notes.get("class_km2"):
        lines.append("Area of each flood class inside Thessaly, before merging (classes overlap between dates): " + "; ".join(f"{k or 'no class'} {v:,.0f} km²" for k, v in notes["class_km2"].items()) + ".")
    lines += [
        "",
        "## Limits",
        "",
        "People are assumed to be spread evenly over the land part of each 1 km cell, so a cell whose land is half under water counts half its residents. Satellites miss water under cloud, in narrow streets and under trees, and the extent mixes several dates. A flood trace marks ground where the water had already gone when the image was taken. Statistical offices may adjust small counts on the grid to protect confidentiality, and the grid flags each such figure, so single cells are approximate even where the totals match the census. Exposure is not harm: a household in a flooded cell may have stayed dry on an upper floor, and one outside may have lost everything.",
        "",
        "Magnesia and the town of Volos: the floods there were mostly flash floods in streets and streams that drained within hours, which satellites passing later rarely see. The low figure for Magnesia therefore says little about how hard it was hit.",
    ]
    return "\n".join(lines) + "\n"


def run(config_path: Path, out_dir: Path, fetcher: Fetcher = fetch, grid_path: Path | None = None) -> dict:
    import geopandas as gpd

    cfg = load_config(config_path)
    c, g, r, a = cfg["cems"], cfg["grid"], cfg["regions"], cfg["analysis"]
    crs = int(a["crs"])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = []
    grid_label = g.get("name", "population grid")

    def check(name, url, fn):
        try:
            value = fn()
            checks.append({"check": name, "url": url, "ok": True, "error": None})
            return value
        except Exception as exc:
            checks.append({"check": name, "url": url, "ok": False, "error": str(exc)})
            return None

    detail_url = c["detail"].format(code=c["activation"])
    got = check("Copernicus EMS activation", detail_url, lambda: activation_products(c["detail"], c["activation"], c["product_types"], fetcher))
    nuts_bytes = check("GISCO regions", r["url"], lambda: fetcher(r["url"]))
    work = Path(tempfile.mkdtemp(prefix="thrive-b-"))
    if grid_path is None:
        gp = work / Path(g["url"]).name
        grid_digest = check(grid_label, g["url"], lambda: fetch_to_file(g["url"], gp))
    else:
        gp = Path(grid_path)
        grid_digest = sha256(gp.read_bytes())
        checks.append({"check": grid_label, "url": str(grid_path), "ok": True, "error": None})
    (out_dir / "preflight.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    if not all(x["ok"] for x in checks):
        raise RuntimeError("preflight failed: " + " | ".join(f"{x['check']} {x['url']}: {x['error']}" for x in checks if not x["ok"]))
    act, products = got
    if not products:
        raise ValueError(f"{c['activation']} lists no downloadable products of type {c['product_types']}")
    words = [w.lower() for w in c["flood_layer_words"]]
    check_words = [w.lower() for w in c.get("check_layer_words", [])]
    class_columns = c.get("class_columns", [])
    inventory, parts, extra, digests = [], [], [], {}
    for p in products:
        try:
            data = fetcher(p["url"])
            digests[p["url"]] = sha256(data)
            found, layers, details, chk = flood_polygons(data, words, crs, check_words, class_columns)
            parts.extend(found)
            extra.extend(chk)
            inventory.append({**p, "ok": True, "layers": layers, "flood_layers": len(found), "flood_layer_details": details, "error": None})
        except Exception as exc:
            inventory.append({**p, "ok": False, "layers": [], "flood_layers": 0, "flood_layer_details": [], "error": str(exc)})
    (out_dir / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    if not parts:
        raise ValueError("no flood polygons found in any product; see inventory.json for the layers each product holds")
    flood = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=crs)
    flood["geometry"] = flood.geometry.buffer(0)
    maximum = None
    if extra:
        maximum = gpd.GeoDataFrame(pd.concat(extra, ignore_index=True), crs=crs)
        maximum["geometry"] = maximum.geometry.buffer(0)
    target, near = regions(nuts_bytes, r["prefix"], crs)
    src_path, layer, grid_info = grid_source(gp, g, work)
    (out_dir / "grid.json").write_text(json.dumps(grid_info, indent=2) + "\n", encoding="utf-8")
    cells, pop_col, older_col, grid_columns = grid_cells(src_path, layer, near[near.intersects(target.buffer(2000).union_all())], g, crs)
    min_exposed = float(a.get("min_exposed_for_ratio", 1000))
    defs = cfg.get("extent") or [{"key": "observed_all", "name": "Observed flood", "source": "observed", "exclude": []}]
    extents, main, shares = [], None, {}
    for d in defs:
        if d.get("source", "observed") == "observed":
            f = flood[~flood["flood_class"].isin(d.get("exclude", []))]
        else:
            f = maximum
        if f is None or f.empty:
            extents.append({"key": d["key"], "name": d["name"], "available": False})
            continue
        res = exposure(cells, f, target, near)
        shares[d["key"]] = res[4]
        if main is None:
            main = res
        extents.append({"key": d["key"], "name": d["name"], "available": True, **extent_summary(res[0], min_exposed)})
    by_region, wet_cells, unplaced_pop, unplaced_cells, first_cells = main
    cell_table = cells.assign(cell_id=range(len(cells))).set_index("cell_id").join(first_cells[["region_id", "region_name", "land_km2"]], how="inner")
    for key, pc in shares.items():
        cell_table[f"flooded_share_{key}"] = pc["flooded_share"].reindex(cell_table.index).fillna(0.0)
    usable = [e for e in extents if e["available"]]
    class_km2 = {}
    land = target[["geometry"]].union_all()
    for k, grp in flood.groupby("flood_class"):
        class_km2[k] = float(grp.union_all().intersection(land).area / 1e6)
    summary = {k: v for k, v in usable[0].items() if k not in ("key", "name", "available")}
    if not older_col:
        for k in ("age_coverage", "older_share_of_population", "older_share_of_exposed", "older_exposure_ratio"):
            summary[k] = None
    summary["extents"] = usable
    summary["extents_missing"] = [e["name"] for e in extents if not e["available"]]
    summary["direction_thessaly"] = direction([e["older_exposure_ratio"] for e in usable]) if older_col else "no data"
    summary["direction_within_units"] = direction([v for e in usable for v in e["region_ratios"].values()]) if older_col else "no data"
    summary["direction_by_unit"] = {rid: (direction([e["region_ratios"].get(rid) for e in usable]) if older_col else "no data") for rid in by_region["region_id"]}
    summary["regions"] = json.loads(by_region.to_json(orient="records"))
    check_df = validation(by_region, cfg.get("validation", {}))
    summary["validation"] = json.loads(check_df.to_json(orient="records"))
    notes = {"unplaced_population": unplaced_pop, "unplaced_cells": unplaced_cells, "min_exposed": min_exposed, "class_km2": dict(sorted(class_km2.items(), key=lambda x: -x[1]))}
    summary["checks"] = notes
    sources = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "activation": act.get("code", c["activation"]),
        "activation_name": act.get("name"),
        "products_listed": len(products),
        "products_used": sum(1 for i in inventory if i["ok"] and i["flood_layers"]),
        "flood_layers_used": len(parts),
        "product_sha256": digests,
        "regions_url": r["url"],
        "regions_sha256": sha256(nuts_bytes),
        "regions": target["region_id"].tolist(),
        "grid_name": grid_label,
        "grid_url": g["url"],
        "grid_sha256": grid_digest,
        "grid_member": grid_info.get("member"),
        "grid_layer": layer,
        "grid_columns": grid_columns,
        "population_column": pop_col,
        "older_column": older_col,
        "validation_source": cfg.get("validation", {}).get("source"),
        "crs": f"EPSG:{crs}",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(report(summary, by_region, check_df, sources, notes), encoding="utf-8")
    with pd.ExcelWriter(out_dir / "phase-b.xlsx", engine="openpyxl") as xl:
        by_region.to_excel(xl, sheet_name="Regional units", index=False)
        check_df.to_excel(xl, sheet_name="Checks", index=False)
        pd.DataFrame([{**{k: v for k, v in e.items() if k != "region_ratios"}, **{f"ratio {k}": v for k, v in e["region_ratios"].items()}} for e in usable]).to_excel(xl, sheet_name="Flood definitions", index=False)
        wet_cells.to_excel(xl, sheet_name="Flooded cells", index=False)
        pd.DataFrame(inventory).assign(
            layers=lambda d: d["layers"].map(lambda x: "; ".join(x)),
            flood_layer_details=lambda d: d["flood_layer_details"].map(json.dumps),
        ).to_excel(xl, sheet_name="Products", index=False)
        pd.DataFrame([{"field": k, "value": json.dumps(v) if isinstance(v, (list, dict)) else v} for k, v in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    cell_table.reset_index().drop(columns=["population_missing"]).to_file(out_dir / "cells.gpkg", layer="cells", driver="GPKG")
    flood.dissolve(by="flood_class").reset_index().to_file(out_dir / "flood-extent.gpkg", layer="observed-by-class", driver="GPKG")
    if maximum is not None:
        maximum[["geometry"]].dissolve().to_file(out_dir / "flood-extent.gpkg", layer="cems-maximum-water-extent", driver="GPKG")
    shutil.rmtree(work, ignore_errors=True)
    return summary
