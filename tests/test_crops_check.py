import numpy as np
import pandas as pd

from thrive.data.crops_check import add_next, forecast, judge, placebo


def panel(seed=0, lead=0.0, beta=-0.02):
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(80):
        lvl = rng.normal(0, 0.2)
        for y in range(2019, 2026):
            hot = {k: float(rng.poisson(2)) for k in range(15, 28)}
            g = rng.normal(0, 0.03)
            for k in range(15, 27):
                rows.append({"cell": c, "year": y, "k": k, "block": c // 8, "hot37": hot[k], "nxt": hot[k + 1], "sma": rng.normal(),
                             "y": lvl + 0.01 * k + g + beta * hot[k] + lead * hot[k + 1] + rng.normal(0, 0.01)})
    return pd.DataFrame(rows)


def test_add_next_takes_the_following_period():
    p = pd.DataFrame({"cell": [0, 0, 0], "year": 2024, "k": [15, 16, 17], "hot37": [1.0, 2.0, 3.0]})
    out = add_next(p, ["hot37"]).sort_values("k")
    assert out["hot37_next"].tolist()[:2] == [2.0, 3.0]
    assert np.isnan(out["hot37_next"].tolist()[2])


def test_placebo_is_quiet_without_a_lead_and_loud_with_one():
    quiet = placebo(panel(1).drop(columns=["nxt"]).pipe(lambda d: add_next(d, ["hot37"])), "hot37", "hot37_next", "sma")
    assert quiet["lo_next"] <= 0 <= quiet["hi_next"]
    p = panel(2, lead=0.02)
    p["hot37_next"] = p["nxt"]
    loud = placebo(p, "hot37", "hot37_next", "sma")
    assert loud["lo_next"] > 0


def test_forecast_improves_when_heat_matters():
    f = forecast(panel(3), "hot37", "sma", (2019, 2022), 2024)
    assert f["improves"] and f["rmse_with"] < f["rmse_without"]
    g = forecast(panel(4, beta=0.0), "hot37", "sma", (2019, 2022), 2024)
    assert abs(g["rmse_with"] - g["rmse_without"]) < 0.002


def test_judge_needs_every_check():
    good_main = [{"b": -0.01, "lo": -0.02, "hi": -0.001}]
    good_pl = [{"b_next": 0.0, "lo_next": -0.01, "hi_next": 0.01}]
    good_fc = [{"improves": True}]
    assert judge(good_main, good_pl, good_fc)[0] == "lower greenness after hot days"
    v, why = judge(good_main, [{"b_next": 0.01, "lo_next": 0.005, "hi_next": 0.02}], good_fc)
    assert v == "not robust" and "placebo" in why[0]
    v, why = judge(good_main, good_pl, [{"improves": False}])
    assert v == "not robust" and "unseen" in why[0]
