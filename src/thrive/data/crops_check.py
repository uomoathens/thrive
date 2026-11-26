import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from thrive.data.crops_heat import demean, estimate, ols_cluster
from thrive.data.crops_probe import load_config


def add_next(panel: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    missing = [c for c in cols if f"{c}_next" not in panel]
    if not missing:
        return panel
    nxt = panel[["cell", "year", "k"] + missing].drop_duplicates(["cell", "year", "k"]).copy()
    nxt["k"] = nxt["k"] - 1
    nxt = nxt.rename(columns={c: f"{c}_next" for c in missing})
    return panel.merge(nxt, on=["cell", "year", "k"], how="left")


def placebo(panel: pd.DataFrame, heat: str, nxt: str, control: str) -> dict:
    cols = ["y", heat, nxt, control]
    d = panel.dropna(subset=cols).copy()
    d["ck"] = d["cell"].astype(str) + "|" + d["k"].astype(str)
    if len(d) < 100 or d[nxt].std() == 0:
        return {"n": int(len(d)), "b_next": None, "lo_next": None, "hi_next": None}
    r = demean(d, cols, ["ck", "year"])
    X = r[[heat, nxt, control]].to_numpy()
    b, se = ols_cluster(r["y"].to_numpy(), X, d["block"].to_numpy(), d["year"].nunique() - 1)
    return {"n": int(len(d)), "b_heat": float(b[0]), "b_next": float(b[1]), "se_next": float(se[1]), "lo_next": float(b[1] - 1.96 * se[1]), "hi_next": float(b[1] + 1.96 * se[1])}


def two_way(resid: np.ndarray, ck: np.ndarray, yr: np.ndarray, iters: int = 200) -> pd.Series:
    a = pd.Series(0.0, index=pd.Index(np.unique(ck)))
    g = pd.Series(0.0, index=pd.Index(np.unique(yr)))
    s = pd.Series(resid)
    for _ in range(iters):
        a = (s - g.reindex(yr).to_numpy()).groupby(ck).mean()
        g_new = (s - a.reindex(ck).to_numpy()).groupby(yr).mean()
        if np.allclose(g_new.to_numpy(), g.reindex(g_new.index).to_numpy(), atol=1e-12):
            g = g_new
            break
        g = g_new
    return a


def forecast(panel: pd.DataFrame, heat: str, control: str, train: tuple[int, int], test_year: int) -> dict:
    cols = ["y", heat, control]
    d = panel.dropna(subset=cols).copy()
    d["ck"] = d["cell"].astype(str) + "|" + d["k"].astype(str)
    tr = d[(d["year"] >= train[0]) & (d["year"] <= train[1])]
    te = d[d["year"] == test_year]
    out = {"test_year": test_year, "rows": 0, "rmse_without": None, "rmse_with": None, "improves": None}
    if len(tr) < 100 or te.empty:
        return out
    res = {}
    for name, xs in (("without", [control]), ("with", [heat, control])):
        r = demean(tr, ["y"] + xs, ["ck", "year"])
        X = r[xs].to_numpy()
        b = np.linalg.lstsq(X, r["y"].to_numpy(), rcond=None)[0]
        a = two_way(tr["y"].to_numpy() - tr[xs].to_numpy() @ b, tr["ck"].to_numpy(), tr["year"].to_numpy())
        t = te[te["ck"].isin(a.index)]
        base = a.reindex(t["ck"]).to_numpy() + t[xs].to_numpy() @ b
        err = t["y"].to_numpy() - base
        err = err - err.mean()
        res[name] = float(np.sqrt(np.mean(err ** 2)))
        out["rows"] = int(len(t))
    out["rmse_without"], out["rmse_with"] = res["without"], res["with"]
    out["improves"] = res["with"] < res["without"]
    return out


def judge(main: list[dict], plac: list[dict], fc: list[dict]) -> tuple[str, list[str]]:
    reasons = []
    if any(r.get("b") is None for r in main) or any(p.get("b_next") is None for p in plac) or any(f["improves"] is None for f in fc):
        return "no data", ["a check could not be computed"]
    if not all(r["hi"] < 0 for r in main):
        reasons.append("not every main estimate is below zero with its interval below zero")
    if not all(p["lo_next"] <= 0 <= p["hi_next"] for p in plac):
        reasons.append("the placebo shows an effect of heat that has not happened yet")
    if not all(f["improves"] for f in fc):
        reasons.append("hot days do not improve the prediction of every unseen Summer")
    return ("lower greenness after hot days" if not reasons else "not robust"), reasons


def report(s: dict, main: pd.DataFrame, plac: pd.DataFrame, fc: pd.DataFrame) -> str:
    def md(df):
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.iterrows():
            cells = []
            for c in cols:
                v = r[c]
                if isinstance(v, float):
                    cells.append("" if math.isnan(v) else (f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.4g}"))
                else:
                    cells.append(str(v))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines) + "\n"

    lines = [
        "# Heat and summer crops in Thessaly: placebo and unseen Summers",
        "",
        "Generated automatically by `thrive crops-check` from the panel of the latest `thrive crops-heat` run. The checks and the rule were fixed on " + s["plan_fixed"] + ", before they were computed; see `config/crops-check-plan.md`.",
        "",
        f"Verdict: **{s['verdict']}**." + ("" if not s["reasons"] else " Reason: " + "; ".join(s["reasons"]) + "."),
        "",
        "## Main estimates (common effect of each year)",
        "",
        md(main),
        "## Placebo: hot days of the next ten-day period",
        "",
        md(plac),
        f"## Unseen Summers: fitted on {s['train'][0]} to {s['train'][1]}",
        "",
        md(fc),
        "Prediction error is the root mean square error of log greenness after removing the normal of each square and ten-day period and the common level of the test Summer, which both models get alike.",
        "",
    ]
    return "\n".join(lines)


def run(config_path: Path, out_dir: Path) -> dict:
    cfg = load_config(config_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = pd.read_excel(cfg["panel"], sheet_name="panel")
    panel = panel[panel["ndvi"] > 0].copy()
    panel["y"] = np.log(panel["ndvi"])
    th = [int(t) for t in cfg["thresholds"]]
    panel = add_next(panel, [f"hot{t}" for t in th])
    control = cfg["control"]
    main, plac = [], []
    for t in th:
        for w in cfg["windows"]:
            col = f"hot{t}" if w == "this" else f"hot{t}_two"
            label = "this ten-day period" if w == "this" else "this and the previous ten-day period"
            main.append({"threshold_C": t, "hot_days_in": label, **estimate(panel, col, "year", control)})
            plac.append({"threshold_C": t, "hot_days_in": label, **placebo(panel, col, f"hot{t}_next", control)})
    fc = []
    for t in th:
        col = f"hot{t}" if cfg["forecast_window"] == "this" else f"hot{t}_two"
        for y in cfg["test_years"]:
            fc.append({"threshold_C": t, **forecast(panel, col, control, tuple(int(x) for x in cfg["train_years"]), int(y))})
    v, reasons = judge(main, plac, fc)
    summary = {
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan_fixed": cfg["plan_fixed"],
        "rows": int(len(panel)),
        "verdict": v,
        "reasons": reasons,
        "train": [int(x) for x in cfg["train_years"]],
        "main": main,
        "placebo": plac,
        "forecast": fc,
    }
    mdf = pd.DataFrame(main)[["threshold_C", "hot_days_in", "n", "b", "lo", "hi", "pct", "pct_lo", "pct_hi"]]
    pdf = pd.DataFrame(plac)[["threshold_C", "hot_days_in", "n", "b_next", "lo_next", "hi_next"]]
    fdf = pd.DataFrame(fc)
    with pd.ExcelWriter(out_dir / "crops-check.xlsx") as xl:
        mdf.to_excel(xl, sheet_name="main", index=False)
        pdf.to_excel(xl, sheet_name="placebo", index=False)
        fdf.to_excel(xl, sheet_name="unseen_summers", index=False)
    (out_dir / "report.md").write_text(report(summary, mdf, pdf, fdf), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    return summary
