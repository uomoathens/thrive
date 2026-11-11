import io
import json
import tempfile
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from thrive.data.download import Fetcher, fetch, fetch_to_file, sha256

VECTOR_EXT = (".shp", ".geojson", ".json", ".gpkg", ".kml")


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


def flood_polygons(zip_bytes: bytes, words, crs: int):
    import geopandas as gpd

    found, layers = [], []
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmp)
        for path in sorted(Path(tmp).rglob("*")):
            if path.suffix.lower() not in VECTOR_EXT or path.name.startswith("."):
                continue
            name = path.name.lower()
            layers.append(path.name)
            if not any(w in name for w in words):
                continue
            gdf = gpd.read_file(path)
            if gdf.empty or gdf.crs is None:
                continue
            gdf = gdf[gdf.geometry.notna() & gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
            if len(gdf):
                found.append(gdf.to_crs(crs)[["geometry"]])
    return found, layers


def regions(geojson: bytes, prefix: str, crs: int):
    import geopandas as gpd

    gdf = gpd.read_file(io.BytesIO(geojson))
    col = "NUTS_ID" if "NUTS_ID" in gdf.columns else "id"
    gdf = gdf[gdf[col].astype(str).str.startswith(prefix)].copy()
    if gdf.empty:
        raise ValueError(f"no regions with code starting {prefix}")
    name = next((c for c in ("NAME_LATN", "NUTS_NAME", "NAME") if c in gdf.columns), col)
    gdf = gdf.rename(columns={col: "region_id", name: "region_name"})[["region_id", "region_name", "geometry"]]
    return gdf.to_crs(crs)


def grid_cells(gpkg_path: Path, area, cfg: dict, crs: int):
    import geopandas as gpd
    from shapely.geometry import box

    minx, miny, maxx, maxy = area.total_bounds
    pts = gpd.read_file(gpkg_path, bbox=(minx, miny, maxx, maxy))
    if pts.crs is None or pts.crs.to_epsg() != crs:
        pts = pts.to_crs(crs)
    pop = next((c for c in cfg["population"] if c in pts.columns), None)
    if pop is None:
        raise KeyError(f"no population column among {cfg['population']}; columns are: {sorted(pts.columns)}")
    older = next((c for c in cfg.get("older", []) if c in pts.columns), None)
    half = float(cfg["cell_size_m"]) / 2
    if set(pts.geometry.geom_type) <= {"Point"}:
        geoms = [box(p.x - half, p.y - half, p.x + half, p.y + half) for p in pts.geometry]
    else:
        geoms = list(pts.geometry)
    cells = gpd.GeoDataFrame({
        "population": pd.to_numeric(pts[pop], errors="coerce").fillna(0.0),
        "older": pd.to_numeric(pts[older], errors="coerce").fillna(0.0) if older else 0.0,
    }, geometry=geoms, crs=crs)
    return cells, pop, older, sorted(pts.columns)


def exposure(cells, flood, regs):
    import geopandas as gpd

    cells = cells.copy()
    cells["cell_id"] = range(len(cells))
    cells["cell_area"] = cells.geometry.area
    joined = gpd.overlay(cells, regs, how="intersection", keep_geom_type=True)
    joined["share_in_region"] = joined.geometry.area / joined["cell_area"]
    flood_union = gpd.GeoDataFrame(geometry=[flood.union_all()], crs=cells.crs)
    wet = gpd.overlay(joined, flood_union, how="intersection", keep_geom_type=True)
    wet["flooded_area"] = wet.geometry.area
    wet_area = wet.groupby(["cell_id", "region_id"])["flooded_area"].sum()
    j = joined.set_index(["cell_id", "region_id"])
    j["flooded_share"] = (wet_area.reindex(j.index).fillna(0.0) / j["cell_area"]).clip(upper=1.0)
    j = j.reset_index()
    j["population_in_region"] = j["population"] * j["share_in_region"]
    j["older_in_region"] = j["older"] * j["share_in_region"]
    j["population_exposed"] = j["population"] * j["flooded_share"]
    j["older_exposed"] = j["older"] * j["flooded_share"]
    j["flooded_km2"] = j["cell_area"] * j["flooded_share"] / 1e6
    by_region = j.groupby(["region_id", "region_name"]).agg(
        population=("population_in_region", "sum"),
        older=("older_in_region", "sum"),
        flooded_km2=("flooded_km2", "sum"),
        population_exposed=("population_exposed", "sum"),
        older_exposed=("older_exposed", "sum"),
        cells_touched=("flooded_share", lambda s: int((s > 0).sum())),
    ).reset_index()
    by_region["share_exposed"] = by_region["population_exposed"] / by_region["population"]
    by_region["older_share_of_exposed"] = by_region["older_exposed"] / by_region["population_exposed"].where(by_region["population_exposed"] > 0)
    by_region["older_share_of_population"] = by_region["older"] / by_region["population"].where(by_region["population"] > 0)
    cells_out = j[j["flooded_share"] > 0][["cell_id", "region_id", "region_name", "population", "older", "flooded_share", "population_exposed", "older_exposed"]]
    return by_region, cells_out


def report(summary: dict, by_region: pd.DataFrame, sources: dict) -> str:
    lines = [
        "# Phase B: who was in the water of Storm Daniel?",
        "",
        "Generated automatically by `thrive phase-b`. `sources.json` records what was downloaded and when.",
        "",
        f"Flood extent: union of every flood polygon in the Copernicus EMS {sources['activation']} products ({sources['products_used']} products, {sources['flood_layers_used']} flood layers). This is the largest extent observed from satellites, not the depth of the water.",
        f"Population: Eurostat GISCO 1 km grid, column `{sources['population_column']}`" + (f", people aged 65 and over from `{sources['older_column']}`." if sources["older_column"] else "; the grid file has no age column, so older people are not counted."),
        "",
        "| Regional unit | Residents | Flooded area (km²) | Residents in flooded cells | Share of residents | Aged 65+ among those exposed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in by_region.itertuples():
        older = "n/a" if not sources["older_column"] or pd.isna(r.older_share_of_exposed) else f"{r.older_share_of_exposed:.0%}"
        lines.append(f"| {r.region_name} | {r.population:,.0f} | {r.flooded_km2:,.1f} | {r.population_exposed:,.0f} | {r.share_exposed:.1%} | {older} |")
    lines += [
        "",
        f"Thessaly in total: {summary['population_exposed']:,.0f} of {summary['population']:,.0f} residents ({summary['share_exposed']:.1%}) lived in the parts of 1 km cells that satellites saw under water, over {summary['flooded_km2']:,.0f} km².",
        "",
        "Limits: people are assumed to be spread evenly within each 1 km cell, so a cell that is half under water counts half its residents. Satellites miss water under cloud, in narrow streets and under trees, and the extent mixes several dates. Exposure is not harm: a household in a flooded cell may have been dry on an upper floor, and one outside may have lost everything.",
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
        gp = work / "grid.gpkg"
        grid_digest = check("GISCO 1 km grid", g["url"], lambda: fetch_to_file(g["url"], gp))
    else:
        gp = Path(grid_path)
        grid_digest = sha256(gp.read_bytes())
        checks.append({"check": "GISCO 1 km grid", "url": str(grid_path), "ok": True, "error": None})
    (out_dir / "preflight.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    if not all(x["ok"] for x in checks):
        raise RuntimeError("preflight failed: " + " | ".join(f"{x['check']} {x['url']}: {x['error']}" for x in checks if not x["ok"]))
    act, products = got
    if not products:
        raise ValueError(f"{c['activation']} lists no downloadable products of type {c['product_types']}")
    words = [w.lower() for w in c["flood_layer_words"]]
    inventory, parts, digests = [], [], {}
    for p in products:
        try:
            data = fetcher(p["url"])
            digests[p["url"]] = sha256(data)
            found, layers = flood_polygons(data, words, crs)
            parts.extend(found)
            inventory.append({**p, "ok": True, "layers": layers, "flood_layers": len(found), "error": None})
        except Exception as exc:
            inventory.append({**p, "ok": False, "layers": [], "flood_layers": 0, "error": str(exc)})
    (out_dir / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    if not parts:
        raise ValueError("no flood polygons found in any product; see inventory.json for the layers each product holds")
    flood = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=crs)
    flood["geometry"] = flood.geometry.buffer(0)
    regs = regions(nuts_bytes, r["prefix"], crs)
    cells, pop_col, older_col, grid_columns = grid_cells(gp, regs, g, crs)
    by_region, wet_cells = exposure(cells, flood, regs)
    total = by_region[["population", "older", "flooded_km2", "population_exposed", "older_exposed"]].sum()
    summary = {
        "population": float(total["population"]),
        "population_exposed": float(total["population_exposed"]),
        "share_exposed": float(total["population_exposed"] / total["population"]) if total["population"] > 0 else None,
        "flooded_km2": float(total["flooded_km2"]),
        "older_exposed": float(total["older_exposed"]) if older_col else None,
        "older_share_of_exposed": float(total["older_exposed"] / total["population_exposed"]) if older_col and total["population_exposed"] > 0 else None,
        "older_share_of_population": float(total["older"] / total["population"]) if older_col and total["population"] > 0 else None,
        "regions": by_region.to_dict(orient="records"),
    }
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
        "regions": regs["region_id"].tolist(),
        "grid_url": g["url"],
        "grid_sha256": grid_digest,
        "grid_columns": grid_columns,
        "population_column": pop_col,
        "older_column": older_col,
        "crs": f"EPSG:{crs}",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=float) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(report(summary, by_region, sources), encoding="utf-8")
    with pd.ExcelWriter(out_dir / "phase-b.xlsx", engine="openpyxl") as xl:
        by_region.to_excel(xl, sheet_name="Regional units", index=False)
        wet_cells.to_excel(xl, sheet_name="Flooded cells", index=False)
        pd.DataFrame(inventory).assign(layers=lambda d: d["layers"].map(lambda x: "; ".join(x))).to_excel(xl, sheet_name="Products", index=False)
        pd.DataFrame([{"field": k, "value": json.dumps(v) if isinstance(v, (list, dict)) else v} for k, v in sources.items()]).to_excel(xl, sheet_name="Sources", index=False)
    flood.dissolve().to_file(out_dir / "flood-extent.gpkg", driver="GPKG")
    return summary
