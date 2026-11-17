from __future__ import annotations

import json
import math
import re
import tomllib
from datetime import datetime
from pathlib import Path

DEFS = ["observed_all", "observed_water", "cems_maximum"]
DEF_NAMES = {
    "observed_all": "Observed flood, including flood traces",
    "observed_water": "Observed standing water, without flood traces",
    "cems_maximum": "Copernicus maximum water extent",
}
TV_NAMES = {
    "With flood traces counted": "observed_all",
    "With standing water only": "observed_water",
    "With the Copernicus maximum water extent": "cems_maximum",
}
TV_GROUPS = {"all": "All flooded cells", "kt": "Flooded, Karditsa, Trikala", "la": "Flooded, Larisa"}
SEASONS = ["Autumn 2023", "Spring 2024", "Summer 2024"]
SPAN = re.compile(r'(<span data-v="([a-z0-9_]+)">)(.*?)(</span>)')
MINUS = "−"


class SiteError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _r(x: float) -> int:
    return int(math.floor(x + 0.5))


def _span(a: int, b: int) -> str:
    return f"{a}" if a == b else f"{a} to {b}"


def _pts(a: float, b: float) -> str:
    lo, hi = sorted((_r(a), _r(b)))
    fmt = lambda v: f"{MINUS}{abs(v)}" if v < 0 else f"{v}"
    return fmt(lo) if lo == hi else f"{fmt(lo)} to {fmt(hi)}"


def _signed(n: float) -> str:
    v = _r(n)
    return f"{MINUS}{abs(v):,}" if v < 0 else f"+{v:,}" if v > 0 else "0"


class Facts:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.values: dict[str, str] = {}
        self.problems: list[str] = []
        self.data: dict[str, object] = {}

    def claim(self, ok: bool, text: str):
        if not ok:
            self.problems.append(text)

    def set(self, key: str, value: str):
        self.values[key] = value


def phase_a(f: Facts):
    import pandas as pd

    d = f.root / "results" / "phase-a"
    s, src = _json(d / "summary.json"), _json(d / "sources.json")
    rb = s["robustness"]
    f.set("a_records", f"{src['openfema_records']:,}")
    f.set("a_grants", f"{src['subgrants_in_scope']:,}")
    f.set("a_total", f"{s['total_funding'] / 1e9:.2f}")
    f.set("a_counties", f"{s['counties']:,}")
    f.set("a_statewide", f"{src['statewide_funding'] / 1e9:.2f}")
    f.set("a_unmatched", f"{src['unmatched_funding'] / 1e9:.2f}")
    f.set("a_unmatched_share", f"{src['unmatched_share'] * 100:.1f}")
    ratios = {"all": s["r_cov_most_vs_least_vulnerable"], "big": rb["r_cov_without_largest"], "med": rb["r_cov_median_county"], "fun": rb["r_cov_median_funded_county"]}
    for k, v in ratios.items():
        f.set(f"a_r_{k}", f"{v:.2f}")
    n_big = int(rb["largest_counties_left_out"])
    f.set("a_n_big", f"{n_big}")
    f.set("a_big_share", f"{_r(rb['share_of_money_in_largest_counties'] * 100)}")
    none = s["share_without_funding_by_quintile"]
    f.set("a_none_most", f"{_r(none[4] * 100)}")
    f.set("a_none_least", f"{_r(none[0] * 100)}")
    f.claim(s["robust_direction"] == "not robust", "Phase A: the four measures now agree on a direction, so 'the measures do not agree' is no longer true.")
    f.claim(ratios["all"] > 1, "Phase A: with all the money, the most vulnerable fifth no longer receives more per dollar of risk.")
    f.claim(ratios["big"] < ratios["all"], "Phase A: leaving out the largest counties no longer lowers the ratio.")
    f.claim(0.8 <= ratios["med"] < 1, "Phase A: the median county in the most vulnerable fifth no longer receives 'a little less'.")
    f.claim(ratios["fun"] > 1, "Phase A: the median funded county in the most vulnerable fifth no longer receives more.")
    f.claim(all(b > a for a, b in zip(none, none[1:])), "Phase A: the share of counties without flood money no longer rises at every step of vulnerability.")
    big = rb["largest_counties"]
    f.claim("Orleans, Louisiana" in big and "Harris, Texas" in big and any(c.endswith(", New York") and c.split(",")[0] in {"Kings", "Queens", "New York", "Suffolk", "Nassau", "Richmond", "Bronx"} for c in big), "Phase A: New Orleans, Harris County or the New York area is no longer among the largest counties.")
    grants = pd.read_excel(d / "phase-a.xlsx", sheet_name="Largest grants")
    g = grants[grants["identifier"] == "DR-4085-0018-R"]
    f.claim(len(g) == 1 and str(g["counties"].iloc[0]) == "Greene", "Phase A: the Greene County grant DR-4085-0018-R is no longer in the table of largest grants.")
    if len(g) == 1:
        f.set("a_greene", f"{_r(float(g['amount'].iloc[0]) / 1e6)}")
    counties = pd.read_excel(d / "phase-a.xlsx", sheet_name="Counties")
    gr = counties[(counties["county"] == "Greene") & (counties["state"] == "New York")]
    f.claim(len(gr) == 1 and int(gr["quintile"].iloc[0]) == 3, "Phase A: Greene County, New York is no longer in the middle vulnerability group.")
    f.claim(len(big) > 1 and big[1] == "Greene, New York", "Phase A: Greene County, New York is no longer the second-largest county.")
    raw = {"all": s["funding_per_eal_dollar_by_quintile"], "big": rb["funding_per_eal_dollar_by_quintile_without_largest"], "med": rb["median_county_ratio_by_quintile"], "fun": rb["median_ratio_of_funded_counties_by_quintile"]}
    text = {
        "all": f"Counting all the money, the most vulnerable fifth received {ratios['all']:.2f} times as much per dollar of flood risk as the least vulnerable fifth.",
        "big": f"Leave out the {n_big} counties that received the most, {f.values['a_big_share']}% of all the money, and the ratio falls to {ratios['big']:.2f}.",
        "med": f"The typical county tells another story. In the most vulnerable fifth it received {ratios['med']:.2f} times as much as the typical county in the least vulnerable fifth.",
        "fun": f"Among counties that received any flood money at all, the typical one in the most vulnerable fifth received {ratios['fun']:.2f} times as much as its counterpart in the least vulnerable fifth.",
    }
    labels = {"all": "All money", "big": f"Without the {n_big} largest", "med": "Median county", "fun": "Median funded county"}
    f.set("a_checks", phase_a_checks(s, src))
    f.data["MS"] = [{"k": k, "l": labels[k], "raw": [round(float(x), 4) for x in raw[k]], "r": round(float(ratios[k]), 2), "t": text[k]} for k in ("all", "big", "med", "fun")]
    f.data["none"] = [round(float(x), 4) for x in none]
    f.data["asof_a"] = src["retrieved_at"]


def phase_a_checks(s: dict, src: dict) -> str:
    rb, parts = s["robustness"], []
    if src.get("left_out_states"):
        parts.append(f"{' and '.join(src['left_out_states'])} is left out, with ${src['left_out_funding'] / 1e6:,.0f} million of grants: since 2022 the National Risk Index describes Connecticut by nine planning regions, while its grants still name the eight former counties, which do not map one to one onto the regions.")
    if "foreign_grants" in src:
        n = int(src["foreign_grants"])
        parts.append(f"{n:,} grants (${src['foreign_funding'] / 1e6:,.0f} million) name counties that mostly belong to a state other than the one recorded for them; they stay unplaced rather than go to a county of the same name in the recorded state." if n else "No grant names counties that mostly belong to another state.")
    if src.get("possible_duplicates"):
        parts.append(f"{int(src['possible_duplicates']):,} grants share their state, their counties and their amount to the cent with another grant under a different identifier; they are counted as recorded and listed in the Excel file for checking with FEMA.")
    if rb.get("r_cov_obligated_only") is not None:
        parts.append(f"Counting only the money FEMA records as obligated, and leaving out the ${src['money_from_fallback'] / 1e9:.2f} billion for which only the planned federal share is known, the coverage ratio is {rb['r_cov_obligated_only']:.2f}.")
    return " ".join(parts)


UNIT_NAMES = {"EL611": "Karditsa and Trikala", "EL612": "Larisa"}


def phase_b_text(s: dict, ext: dict) -> tuple[str, str]:
    block = s.get("block_km")
    if block:
        note = f"In brackets is the 95 % interval from {s['replicates']:,} resamplings in which the 1 km squares are drawn in blocks of {block:g} by {block:g} km, because neighbouring squares flood together and are settled together."
    else:
        note = f"In brackets is the 95 % interval from {s['replicates']:,} resamplings of the 1 km squares, each drawn on its own."
    out = []
    for rid, name in UNIT_NAMES.items():
        v = s["direction_by_unit"].get(rid)
        rat = [ext[k]["region_ratios"].get(rid) for k in DEFS]
        ivs = [ext[k]["intervals"].get(rid) for k in DEFS]
        if any(x is None for x in rat) or any(x is None for x in ivs):
            out.append(f"{name} had too few people in the flood for a ratio.")
            continue
        lo, hi = min(i[0] for i in ivs), max(i[1] for i in ivs)
        if v == "older people less exposed":
            out.append(f"In {name}, under every flood map, older people were less likely than their neighbours to live where the water reached, and the 95 % interval stays below 1 each time (at most {hi:.2f}).")
        elif v == "older people more exposed":
            out.append(f"In {name}, under every flood map, older people were more likely than their neighbours to live where the water reached, and the 95 % interval stays above 1 each time (at least {lo:.2f}).")
        else:
            side = "above 1" if all(x > 1 for x in rat) else ("below 1" if all(x < 1 for x in rat) else "on either side of 1, depending on the map,")
            out.append(f"In {name} the ratio is {side} ({min(rat):.2f} to {max(rat):.2f}), but the intervals run from {lo:.2f} to {hi:.2f}, so the pattern is not firm enough to report.")
    th = [ext[k]["older_exposure_ratio"] for k in DEFS]
    tiv = [ext[k]["intervals"]["Thessaly"] for k in DEFS]
    if s["direction_thessaly"] == "not robust":
        out.append(f"For Thessaly as a whole the ratio runs from {min(th):.2f} to {max(th):.2f} across the maps, and the intervals from {min(i[0] for i in tiv):.2f} to {max(i[1] for i in tiv):.2f}, so there is no firm direction either.")
    else:
        out.append(f"For Thessaly as a whole the direction is firm under every map: {s['direction_thessaly']}.")
    if not block:
        out.append("These intervals treat every square as if it were independent. Neighbouring squares flood together and are settled together, so the intervals are too narrow; from the next run on the squares are resampled in blocks of 10 by 10 km, and a first check with such blocks already takes the Larisa interval with flood traces across 1.")
    return note, " ".join(out)


def phase_b(f: Facts):
    import geopandas as gpd

    d = f.root / "results" / "phase-b"
    s, inv = _json(d / "summary.json"), _json(d / "inventory.json")
    ext = {e["key"]: e for e in s["extents"]}
    f.claim(all(k in ext and ext[k]["available"] for k in DEFS), "Phase B: one of the three flood definitions is missing.")
    f.set("b_pop", f"{_r(s['population']):,}")
    f.set("b_products", f"{len(inv)}")
    f.claim(all(i["ok"] for i in inv), "Phase B: not every Copernicus product could be read.")
    val = {v["region_id"]: v for v in s["validation"]}
    f.claim(all(abs(v["difference_share"]) < 0.002 for v in val.values()), "Phase B: the grid is no longer within 0.2% of the ELSTAT census in every regional unit.")
    for r in ("EL611", "EL612", "EL613"):
        f.set(f"b_diff_{r.lower()}", _signed(val[r]["difference"]))
    f.claim(_json(d / "summary.json")["replicates"] == 1000, "Phase B: the intervals no longer come from 1,000 resamplings.")
    note, findings = phase_b_text(s, ext)
    f.set("b_iv_note", note)
    f.set("b_findings", findings)
    f.claim(all(ext[k]["region_ratios"].get("EL613") is None for k in DEFS), "Phase B: Magnesia now has enough people in the flood for a ratio.")
    cells = gpd.read_file(d / "cells.gpkg")
    mag = []
    for k in DEFS:
        e = cells["population"] * cells[f"flooded_share_{k}"]
        f.claim(abs(float(e.sum()) - ext[k]["population_exposed"]) < 5.0, f"Phase B: cells.gpkg no longer adds up to the residents in the flood for {k}.")
        mag.append(_r(float(e[cells["region_id"] == "EL613"].sum())))
    f.set("b_mag", _span(min(mag), max(mag)))
    f.data["TD"] = {k: {"km2": _r(ext[k]["flooded_km2"]), "exp": _r(ext[k]["population_exposed"]), "share": ext[k]["share_exposed"], "r": round(ext[k]["older_exposure_ratio"], 4), "u": [round(ext[k]["region_ratios"]["EL611"], 4), round(ext[k]["region_ratios"]["EL612"], 4)], "iv": [list(ext[k]["intervals"][r]) for r in ("Thessaly", "EL611", "EL612")]} for k in DEFS}
    f.data["cells"] = cells
    f.data["asof_b"] = _json(d / "sources.json")["retrieved_at"]


def thriving(f: Facts):
    import pandas as pd

    d = f.root / "results" / "thriving"
    s = _json(d / "summary.json")
    cfg = tomllib.loads((f.root / "config" / "thriving.toml").read_text(encoding="utf-8"))
    f.set("t_scenes", f"{s['items_used']:,}")
    f.set("t_excluded", f"{s['items_excluded']:,}")
    f.set("t_listed", f"{s['items_listed']:,}")
    f.claim(float(cfg["stac"]["max_cloud"]) == 80, "Thriving: the images are no longer limited to at most 80% cloud cover.")
    f.claim(s["items_failed"] == 0, "Thriving: some images could not be read, so 'none failed to read' is no longer true.")
    f.claim([r["ring"] for r in s["control_rings"]] == ["3 to 15 km", "5 to 20 km", "10 to 30 km"], "Thriving: the control areas are no longer 3 to 15, 5 to 20 and 10 to 30 km.")
    f.claim(s["replicates"] == 1000, "Thriving: the intervals no longer come from 1,000 resamplings.")
    si = s["season_intervals"]

    def rows(group, season, ring=None):
        return [x for x in si if x["group"] == group and x["season"] == season and (ring is None or x["ring"] == ring)]

    f.set("t_findings", thriving_text(s, rows))
    mg = [x for x in si if x["group"] == "Flooded, Magnisia, Sporades"]
    f.claim(all(x["value"] is not None and x["value"] < 0 for x in mg if x["season"] == "Spring 2024") and all(x["value"] is None for x in mg if x["season"] == "Summer 2024"), "Thriving: Magnesia is no longer mostly water in the spring of 2024 with too few images in the summer.")
    cells = f.data["cells"]
    m = float(cfg["groups"]["flooded_share_min"])
    w, c = cells["flooded_share_observed_water"] >= m, cells["flooded_share_cems_maximum"] >= m
    add = c & ~w
    f.set("t_w", f"{int(w.sum()):,}")
    f.set("t_wc", f"{int((w & c).sum()):,}")
    f.set("t_add", f"{int(add.sum()):,}")
    f.set("t_add_mag", f"{int((add & (cells['region_id'] == 'EL613')).sum()):,}")
    f.set("t_add_res", f"{_r(float(cells.loc[add, 'population'].sum())):,}")
    f.set("t_add_mag_res", f"{_r(float(cells.loc[add & (cells['region_id'] == 'EL613'), 'population'].sum())):,}")
    cm = [dd for dd in s["definitions"] if dd["key"] == "cems_maximum"][0]
    f.set("t_drop", f"{cm['groups']['All flooded cells']['cells_left_out_not_green']:,}")
    ser = pd.read_excel(d / "thriving.xlsx", sheet_name="Ten-day series")
    ser["date"] = pd.to_datetime(ser["date"]).dt.strftime("%Y-%m-%d")
    dates = sorted(ser["date"].unique())
    series = {}
    for k in DEFS:
        series[k] = {}
        for tk, g in TV_GROUPS.items():
            sub = ser[(ser["definition"] == DEF_NAMES[k]) & (ser["group"] == g)].set_index("date").reindex(dates)
            rel = (sub["group_ratio"] / sub["control_ratio"]).tolist()
            series[k][tk] = [round(float(v), 4) if v is not None and math.isfinite(v) else None for v in rel]
    gap = max(abs(a - b) for tk in TV_GROUPS for a, b in zip(series["observed_water"][tk], series["cems_maximum"][tk]) if a is not None and b is not None)
    f.claim(gap <= 0.015, "Thriving: the standing-water and Copernicus curves now differ by more than about one point.")
    idx = {dt: i for i, dt in enumerate(dates)}
    aut = [series[k]["all"][idx[dt]] for k in DEFS for dt in ("2024-09-21", "2024-10-01", "2024-10-11", "2024-10-21") if dt in idx]
    f.claim(len(aut) == 12 and all(v is not None and v > 1 for v in aut), "Thriving: from late September to late October 2024 the flooded land is no longer greener than a normal autumn.")
    if aut and all(v is not None for v in aut):
        f.set("t_aut24", _span(_r(100 * (min(aut) - 1)), _r(100 * (max(aut) - 1))))
    oct23 = [series[k]["kt"][idx["2023-10-21"]] for k in DEFS] if "2023-10-21" in idx else []
    f.claim(len(oct23) == 3 and all(v is not None and 0.95 <= v <= 1.1 for v in oct23), "Thriving: Karditsa and Trikala were no longer close to normal by late October 2023.")
    win = [series[k]["kt"][i] for k in DEFS for dt, i in idx.items() if "2023-12-01" <= dt <= "2024-02-29"]
    f.claim(all(any(v is not None and v > 1 for v in [series[k]["kt"][i] for dt, i in idx.items() if "2023-12-01" <= dt <= "2024-02-29"]) for k in DEFS) and bool(win), "Thriving: Karditsa and Trikala were no longer greener than normal at times during the winter.")
    oct_all = [series[k]["all"][idx[dt]] for k in DEFS for dt in ("2023-10-01", "2023-10-11", "2023-10-21") if dt in idx]
    f.claim(all(v is not None and v < 1 for v in oct_all), "Thriving: in October 2023 the flooded land as a whole is now greener than normal somewhere.")
    seasons, ivs = {}, {}
    for k in DEFS:
        seasons[k], ivs[k] = {}, {}
        for tk, g in TV_GROUPS.items():
            rr = [rows(g, sn, "3 to 15 km") for sn in SEASONS]
            seasons[k][tk] = [next((x["value"] for x in r if x["definition"] == DEF_NAMES[k]), None) for r in rr]
            ivs[k][tk] = [next((None if x["interval"] is None else list(x["interval"]) for x in r if x["definition"] == DEF_NAMES[k]), None) for r in rr]
    f.data["TV"] = {"dates": dates, "s": series, "seasons": seasons, "ivs": ivs}
    f.data["asof_t"] = _json(d / "sources.json")["retrieved_at"]


VERDICT_WORDS = {
    "lower": "and every interval stays below zero",
    "higher": "and every interval stays above zero",
    "no difference shown": "and every interval includes zero, so no difference shows",
    "not robust": "but not every interval stays on one side of zero, so the gap is not firm under every map and control area",
    "no data": "but too few images or squares were left to judge",
}


def _gap(c) -> str | None:
    if c is None or any(x["difference"] is None for x in c["detail"]):
        return None
    dif = [-100 * x["difference"] for x in c["detail"]]
    return _pts(min(dif), max(dif))


def thriving_text(s: dict, rows) -> str:
    out = []
    block = s.get("block_km")
    su = rows("All flooded cells", "Summer 2024")
    if su and all(x["value"] is not None and x["interval"] for x in su):
        less = _span(_r(100 * (1 - max(x["value"] for x in su))), _r(100 * (1 - min(x["value"] for x in su))))
        if all(x["interval"][1] < 1 for x in su):
            iv = _span(_r(100 * (1 - max(x["interval"][1] for x in su))), _r(100 * (1 - min(x["interval"][0] for x in su))))
            out.append(f"In the summer of 2024, almost a year after Daniel, the flooded land was still {less} % less green than normal under every flood map and every control area, with 95 % intervals running from {iv} %.")
        else:
            out.append(f"In the summer of 2024 the flooded land was {less} % less green than normal, but not every interval stays below normal, so the deficit is not firm under every flood map and control area.")
    cmp_ = {(c["a"], c["season"]): c for c in s["comparisons"]}
    sp, smr = cmp_.get(("Flooded, Larisa", "Spring 2024")), cmp_.get(("Flooded, Larisa", "Summer 2024"))
    if sp and smr and _gap(sp) and _gap(smr):
        lead = "Larisa fared worse than Karditsa and Trikala, by" if sp["verdict"] == smr["verdict"] == "lower" else "Larisa's shortfall against Karditsa and Trikala was"
        if sp["verdict"] == smr["verdict"]:
            out.append(f"{lead} {_gap(sp)} points in the spring and {_gap(smr)} in the summer, {VERDICT_WORDS[sp['verdict']]}.")
        else:
            out.append(f"{lead} {_gap(sp)} points in the spring, {VERDICT_WORDS[sp['verdict']]}, and {_gap(smr)} in the summer, {VERDICT_WORDS[smr['verdict']]}.")
    basin = (s.get("basin") or {}).get("name")
    bsp, bsu = (cmp_.get((basin, "Spring 2024")), cmp_.get((basin, "Summer 2024"))) if basin else (None, None)
    if bsp and bsu and _gap(bsp) and _gap(bsu):
        mean = lambda c: -sum(x["difference"] for x in c["detail"]) / len(c["detail"])
        smaller = sp is not None and smr is not None and _gap(sp) and _gap(smr) and mean(bsp) < mean(sp) and mean(bsu) < mean(smr)
        lead = "Part of that gap is a new lake: the basin" if smaller else "The basin"
        tail = "" if smaller else " That basin does not explain the gap."
        if bsp["verdict"] == bsu["verdict"]:
            rest = f"the gap is {_gap(bsp)} points in the spring and {_gap(bsu)} in the summer, {VERDICT_WORDS[bsp['verdict']]}."
        else:
            rest = f"the gap is {_gap(bsp)} points in the spring, {VERDICT_WORDS[bsp['verdict']]}, and {_gap(bsu)} in the summer, {VERDICT_WORDS[bsu['verdict']]}."
        out.append(f"{lead} of the former Lake Karla filled with water in September 2023 and stayed flooded well into 2024. Leaving out Larisa's squares within {float(s['basin']['radius_m']) / 1000:g} km of the old lake's centre, {rest}{tail}")
    else:
        out.append("Part of Larisa's flooded land lies in the basin of the former Lake Karla, which filled with water in September 2023 and stayed flooded well into 2024; there greenness measures a new lake rather than slow recovery, and from the next run on Larisa is also compared without that basin.")
    o_sp, o_su = cmp_.get(("Flooded, more older residents", "Spring 2024")), cmp_.get(("Flooded, more older residents", "Summer 2024"))
    sizes = [v["cells"] for dd in s["definitions"] for g, v in dd["groups"].items() if "older residents" in g]
    if o_sp and o_su and _gap(o_su) and sizes:
        dsu = [100 * x["difference"] for x in o_su["detail"]]
        if o_sp["verdict"] == "no difference shown" and o_su["verdict"] == "no difference shown":
            lo, hi = min(x["interval"][0] for x in o_su["detail"]), max(x["interval"][1] for x in o_su["detail"])
            out.append(f"Between flooded squares with more and with fewer residents aged 65 and over no difference shows. In the summer the two groups differ by {_pts(min(dsu), max(dsu))} {'point' if _pts(min(dsu), max(dsu)) in ('1', MINUS + '1') else 'points'}, but each group holds only {_span(min(sizes), max(sizes))} squares, so the intervals run from about {_r(-100 * lo)} points less to {_r(100 * hi)} points more. A modest gap either way cannot be ruled out.")
        else:
            out.append(f"Between flooded squares with more and with fewer residents aged 65 and over, the summer difference is {_pts(min(dsu), max(dsu))} points ({o_su['verdict']}), and the spring verdict is: {o_sp['verdict']}. Each group holds {_span(min(sizes), max(sizes))} squares.")
        if s.get("older_split") != "within_unit":
            out.append("The two groups were split at one median for the whole plain, so under the standing-water map they draw unevenly on the regional units: 26 of the 28 squares with more older residents lie in Karditsa and Trikala, which came back sooner, against 17 of the 29 with fewer. From the next run on they are split within each regional unit.")
    if block:
        out.append(f"Every interval resamples the squares in blocks of {block:g} by {block:g} km, because neighbouring squares flood and recover together.")
    else:
        out.append("These intervals resample single squares as if each were independent, which makes them too narrow; from the next run on the squares are resampled in blocks of 10 by 10 km.")
    return " ".join(out)


def collect(root: Path) -> Facts:
    f = Facts(root)
    phase_a(f)
    phase_b(f)
    thriving(f)
    stamps = [datetime.fromisoformat(str(f.data[k]).replace("Z", "+00:00")) for k in ("asof_a", "asof_b", "asof_t")]
    last = max(stamps)
    f.set("asof", f"{last.day} {last.strftime('%B %Y')}")
    return f


def _spans(text: str, f: Facts, name: str, used: set[str]) -> str:
    def sub(m):
        k = m.group(2)
        if k not in f.values:
            f.problems.append(f"{name}: unknown value '{k}'.")
            return m.group(0)
        used.add(k)
        return m.group(1) + f.values[k] + m.group(4)

    return SPAN.sub(sub, text)


def _replace_js(h: str, start: str, value: str, end: str) -> str:
    i = h.index(start) + len(start)
    j = h.index(end, i)
    return h[:i] + value + h[j:]


def render_page(h: str, f: Facts, used: set[str]) -> str:
    h = _spans(h, f, "page", used)
    h = _replace_js(h, "MS=", json.dumps(f.data["MS"], ensure_ascii=False, separators=(",", ":")), ";\nvar c5=")
    h = _replace_js(h, "var none=", json.dumps(f.data["none"]), ".map(")
    i = h.index("var TD=") + len("var TD=")
    td, n = json.JSONDecoder().raw_decode(h[i:])
    for d in td:
        d.update(f.data["TD"][d["k"]])
    h = h[:i] + json.dumps(td, ensure_ascii=False) + h[i + n:]
    i = h.index("var TV=") + len("var TV=")
    tv, n = json.JSONDecoder().raw_decode(h[i:])
    t = f.data["TV"]
    tv["dates"] = t["dates"]
    for d in tv["defs"]:
        k = TV_NAMES[d["d"]]
        d["s"], d["seasons"], d["ivs"] = t["s"][k], t["seasons"][k], t["ivs"][k]
    return h[:i] + json.dumps(tv, ensure_ascii=False, separators=(",", ":")) + h[i + n:]


def _pct(v, iv):
    if v is None:
        return "n/a"
    return f"{_r(100 * v)} % ({_r(100 * iv[0])} to {_r(100 * iv[1])})" if iv else f"{_r(100 * v)} %"


def render_readme(md: str, f: Facts, used: set[str]) -> str:
    md = _spans(md, f, "README", used)
    td = f.data["TD"]
    labels = {"observed_all": "Every observed flood polygon, with flood traces", "observed_water": "Standing water only", "cems_maximum": "Copernicus maximum water extent"}
    for k in DEFS:
        d = td[k]
        cells = [f"{a:.2f} ({b[0]:.2f} to {b[1]:.2f})" for a, b in zip([d["r"], d["u"][0], d["u"][1]], d["iv"])]
        row = f"| {labels[k]} | {d['km2']:,} | {d['exp']:,} | {d['share'] * 100:.1f} % | " + " | ".join(cells) + " |"
        md, n = re.subn(r"^\| " + re.escape(labels[k]) + r" \|.*$", row, md, count=1, flags=re.M)
        if n != 1:
            f.problems.append(f"README: the Phase B row '{labels[k]}' is missing.")
    t = f.data["TV"]
    for tk, label in (("all", "All flooded land"), ("kt", "Karditsa and Trikala"), ("la", "Larisa")):
        row = f"| {label} | " + " | ".join(_pct(t["seasons"][k][tk][2], t["ivs"][k][tk][2]) for k in DEFS) + " |"
        md, n = re.subn(r"^\| " + re.escape(label) + r" \| [0-9n].*$", row, md, count=1, flags=re.M)
        if n != 1:
            f.problems.append(f"README: the Thriving row '{label}' is missing.")
    return md


def build(root: Path, write: bool = True) -> dict:
    root = Path(root)
    f = collect(root)
    used: set[str] = set()
    page_p, readme_p = root / "docs" / "index.html", root / "README.md"
    page0, readme0 = page_p.read_text(encoding="utf-8"), readme_p.read_text(encoding="utf-8")
    page, readme = render_page(page0, f, used), render_readme(readme0, f, used)
    for k in sorted(set(f.values) - used):
        f.problems.append(f"The value '{k}' is computed but appears nowhere on the page or in the README.")
    if f.problems:
        raise SiteError(f.problems)
    changed = []
    if page != page0:
        changed.append("docs/index.html")
    if readme != readme0:
        changed.append("README.md")
    if write:
        if page != page0:
            page_p.write_text(page, encoding="utf-8")
        if readme != readme0:
            readme_p.write_text(readme, encoding="utf-8")
    return {"changed": changed, "values": f.values}
