import json
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from thrive.data.crops_heat import crop_hectares, pick_year_file, sample_cells
from thrive.data.crops_probe import contains, crawl, load_config, tif_header
from thrive.data.download import Fetcher, fetch, fetch_to_file

UNITS = {"EL611": "Καρδίτσα και Τρίκαλα", "EL612": "Λάρισα", "EL613": "Μαγνησία και Σποράδες"}
CROPS = {"cotton": "Βαμβάκι", "maize": "Καλαμπόκι"}


def longest_run(flags: np.ndarray) -> np.ndarray:
    best = np.zeros(flags.shape[0], dtype=int)
    cur = np.zeros(flags.shape[0], dtype=int)
    for j in range(flags.shape[1]):
        cur = np.where(flags[:, j], cur + 1, 0)
        best = np.maximum(best, cur)
    return best


def summer_heat(dates: list[date], tmax: np.ndarray, year: int, start: str, end: str, thresholds: list[int], run_threshold: int, min_share: float) -> pd.DataFrame | None:
    a, b = date.fromisoformat(f"{year}-{start}"), date.fromisoformat(f"{year}-{end}")
    sel = np.array([a <= d <= b for d in dates])
    expected = (b - a).days + 1
    if sel.sum() < expected:
        return None
    block = tmax[:, sel]
    valid = np.isfinite(block)
    out = pd.DataFrame({"cell": np.arange(tmax.shape[0]), "year": year, "days_valid": valid.sum(axis=1)})
    ok = out["days_valid"].to_numpy() >= min_share * expected
    filled = np.where(valid, block, -np.inf)
    for t in thresholds:
        out[f"days_{t}"] = np.where(ok, (filled >= t).sum(axis=1), np.nan)
    out[f"longest_{run_threshold}"] = np.where(ok, longest_run(filled >= run_threshold), np.nan)
    out["tmax_max"] = np.where(ok, filled.max(axis=1), np.nan)
    return out


def by_unit(heat: pd.DataFrame, crops: pd.DataFrame, cells, rule_t: int, rule_days: int, extreme_t: int, extreme_days: int) -> pd.DataFrame:
    h = heat.merge(crops, left_on="cell", right_index=True).merge(cells[["region_id"]], left_on="cell", right_index=True)
    rows = []
    for (y, rid), g in h.groupby(["year", "region_id"]):
        g = g[g[f"days_{rule_t}"].notna()]
        row = {"Έτος": int(y), "Περιφερειακή Ενότητα": UNITS.get(rid, rid)}
        for crop, label in CROPS.items():
            w = g[crop]
            tot = float(w.sum())
            row[f"{label}, εκτάρια"] = round(tot)
            row[f"{label}, εκτάρια με ≥{rule_days} ημέρες ≥{rule_t}°C"] = round(float(w[g[f"days_{rule_t}"] >= rule_days].sum()))
            row[f"{label}, εκτάρια με ≥{extreme_days} ημέρες ≥{extreme_t}°C"] = round(float(w[g[f"days_{extreme_t}"] >= extreme_days].sum()))
            row[f"{label}, μέσος αριθμός ημερών ≥{rule_t}°C"] = round(float((g[f"days_{rule_t}"] * w).sum() / tot), 1) if tot > 0 else None
        rows.append(row)
    return pd.DataFrame(rows)


def report(s: dict, table: pd.DataFrame) -> str:
    def md(df):
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join("" if pd.isna(r[c]) else str(r[c]) if c == "Έτος" else (f"{r[c]:,.0f}" if isinstance(r[c], (int, np.integer)) or (isinstance(r[c], float) and float(r[c]).is_integer()) else str(r[c])) for c in cols) + " |")
        return "\n".join(lines) + "\n"

    lines = [
        "# Summer heat on cotton and maize in Thessaly",
        "",
        "Generated automatically by `thrive crops-exposure`. `sources.json` records what was read and when.",
        "",
        f"This is a count, not a model. For every 1 km square of Thessaly, the hectares of cotton and maize come from the EU crop map 2022 (JRC EUCROPMAP), and the hot days of each Summer ({s['season'][0]} to {s['season'][1]}) from the daily maximum temperature of the European Drought Observatory (Copernicus, JRC MARS, 10 km grid). A day is hot at or above {s['rule_threshold']}°C; a Summer counts as exposed with at least {s['rule_days']} such days, and as extreme with at least {s['extreme_days']} days at or above {s['extreme_threshold']}°C.",
        "",
        f"Summers: {', '.join(str(y) for y in s['years'])}." + (f" Left out because the temperature file does not yet cover the whole Summer: {', '.join(str(y) for y in s['skipped'])}." if s["skipped"] else ""),
        "",
        md(table),
        "## Limits",
        "",
        "- Exposure is not damage. Irrigation, the stage of the crop and the variety decide how much a hot day costs; this count says only how many hot days fell on the land where these crops grow.",
        "- The crop map is of 2022; crops rotate, so the same hectares are used for every Summer. The cotton class of the map is the class of other non-permanent industrial crops, mostly cotton in Thessaly; its 2022 area is 19% above the Eurostat cotton area.",
        "- Temperature is a 10 km grid of air temperature; it does not see the microclimate of a single field.",
    ]
    return "\n".join(lines) + "\n"


def run(config_path: Path, out_dir: Path, fetcher: Fetcher = fetch) -> dict:
    import geopandas as gpd

    cfg = load_config(config_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cells = gpd.read_file(cfg["cells"]["path"], layer=cfg["cells"].get("layer", "cells")).to_crs(3035).reset_index(drop=True)
    cm = cfg["cropmap"]
    head = tif_header(cm["url"])
    if not contains(head["bounds4326"], list(cells.to_crs(4326).total_bounds)):
        raise RuntimeError(f"the crop map file {cm['url']} does not cover all of Thessaly")
    classes = {name: int(code) for name, code in cm["classes"].items()}
    crops = crop_hectares(cells, cm["url"], classes)
    keep = crops.index[crops.sum(axis=1) > 0].to_numpy()
    crops = crops.loc[keep]
    pts = cells.loc[keep]
    cx, cy = pts.geometry.centroid.x.to_numpy(), pts.geometry.centroid.y.to_numpy()

    e, ex = cfg["edo"], cfg["exposure"]
    thresholds = sorted({int(t) for t in e["thresholds"]} | {int(ex["threshold"]), int(ex["extreme_threshold"])})
    first, last = int(cfg["years"][0]), int(cfg["years"][1])
    files = crawl(e["base"] + e["tmax_dir"] + "/", fetcher, int(e["max_depth"]))
    parts, src, skipped = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        for y in range(first, last + 1):
            f = pick_year_file(files, y)
            if f is None:
                skipped.append(y)
                continue
            local = Path(tmp) / f["name"]
            digest = fetch_to_file(f["url"], local)
            dates, vals = sample_cells(local, cx, cy, "EPSG:3035")
            local.unlink()
            h = summer_heat(dates, vals, y, cfg["season"][0], cfg["season"][1], thresholds, int(ex["threshold"]), float(e["min_valid_share"]))
            src.append({"year": y, "url": f["url"], "sha256": digest, "last_day": dates[-1].isoformat()})
            if h is None:
                skipped.append(y)
                continue
            h["cell"] = keep[h["cell"].to_numpy()]
            parts.append(h)
    if not parts:
        raise RuntimeError("no Summer is fully covered by the temperature files")
    heat = pd.concat(parts, ignore_index=True)
    years = sorted(heat["year"].unique().tolist())
    table = by_unit(heat, crops, cells, int(ex["threshold"]), int(ex["days"]), int(ex["extreme_threshold"]), int(ex["extreme_days"]))

    sq = cells.loc[keep, ["cell_id", "region_id"]].copy()
    sq["Περιφερειακή Ενότητα"] = sq["region_id"].map(UNITS)
    cent = cells.loc[keep].geometry.centroid.to_crs(4326)
    sq["Γεωγραφικό μήκος"] = cent.x.round(5).to_numpy()
    sq["Γεωγραφικό πλάτος"] = cent.y.round(5).to_numpy()
    for crop, label in CROPS.items():
        sq[f"{label}, εκτάρια"] = crops[crop].round(1).to_numpy()
    wide = heat.pivot(index="cell", columns="year", values=f"days_{int(ex['threshold'])}")
    for y in years:
        sq[f"Ημέρες ≥{int(ex['threshold'])}°C, {y}"] = wide.reindex(keep)[y].to_numpy()
    sq = sq.drop(columns=["region_id"]).rename(columns={"cell_id": "Τετράγωνο 1 km"})

    summary = {
        "started": started,
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "squares": int(len(keep)),
        "cotton_ha": float(crops["cotton"].sum()),
        "maize_ha": float(crops["maize"].sum()),
        "years": years,
        "skipped": skipped,
        "season": cfg["season"],
        "rule_threshold": int(ex["threshold"]),
        "rule_days": int(ex["days"]),
        "extreme_threshold": int(ex["extreme_threshold"]),
        "extreme_days": int(ex["extreme_days"]),
    }
    notes = pd.DataFrame({"Σημείωση": [
        "Μέτρηση, όχι εκτίμηση ζημιάς: δείχνει πόσες ζεστές ημέρες έπεσαν εκεί όπου καλλιεργούνται βαμβάκι και καλαμπόκι.",
        f"Ζεστή ημέρα: μέγιστη θερμοκρασία ≥{int(ex['threshold'])}°C. Εκτεθειμένο Καλοκαίρι: ≥{int(ex['days'])} τέτοιες ημέρες ({cfg['season'][0]} έως {cfg['season'][1]}).",
        "Καλλιέργειες: Ευρωπαϊκός χάρτης καλλιεργειών 2022 (JRC EUCROPMAP), ίδιες εκτάσεις για κάθε έτος.",
        "Θερμοκρασία: Ευρωπαϊκό Παρατηρητήριο Ξηρασίας (Copernicus, JRC MARS), πλέγμα 10 km.",
        "Τετράγωνα: πλέγμα απογραφής 2021 της Eurostat (1 km).",
    ]})
    with pd.ExcelWriter(out_dir / "crops-exposure.xlsx") as xl:
        table.to_excel(xl, sheet_name="Ανά Περιφερειακή Ενότητα", index=False)
        sq.to_excel(xl, sheet_name="Ανά τετράγωνο", index=False)
        notes.to_excel(xl, sheet_name="Σημειώσεις", index=False)
    (out_dir / "report.md").write_text(report(summary, table), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "sources.json").write_text(json.dumps({"started": started, "crop_map": cm["url"], "tmax": src}, indent=2) + "\n", encoding="utf-8")
    return summary
