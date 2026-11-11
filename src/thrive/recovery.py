from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np


def recovery_day(series: Sequence[float], baseline: float, alpha: float, persistence: int = 1) -> int | None:
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    if persistence < 1:
        raise ValueError("persistence must be at least 1")
    if baseline <= 0:
        raise ValueError("baseline must be positive")
    above = np.asarray(series, dtype=float) >= alpha * baseline
    run = 0
    for day, ok in enumerate(above):
        run = run + 1 if ok else 0
        if run == persistence:
            return day - persistence + 1
    return None


def recovery_days(groups: Mapping[str, Sequence[float]], baselines: Mapping[str, float], alpha: float, persistence: int = 1) -> dict[str, int | None]:
    return {g: recovery_day(s, baselines[g], alpha, persistence) for g, s in groups.items()}


def _censored(days: Mapping[str, int | None], horizon: int) -> dict[str, int]:
    return {g: (horizon if d is None else d) for g, d in days.items()}


def spread(days: Mapping[str, int | None], horizon: int) -> float:
    vals = np.array(list(_censored(days, horizon).values()), dtype=float)
    return float(np.abs(vals - vals.mean()).sum())


@dataclass(frozen=True)
class RecoveryFinding:
    alphas: tuple[float, ...]
    days: tuple[dict[str, int | None], ...]
    orders: tuple[tuple[str, ...], ...]
    penalty: float
    stable: bool


def robust_recovery(groups: Mapping[str, Sequence[float]], baselines: Mapping[str, float], alphas: Sequence[float], persistence: int = 1) -> RecoveryFinding:
    if not alphas:
        raise ValueError("at least one alpha is needed")
    horizon = max(len(s) for s in groups.values())
    all_days, orders, penalties = [], [], []
    for a in alphas:
        days = recovery_days(groups, baselines, a, persistence)
        cens = _censored(days, horizon)
        all_days.append(days)
        orders.append(tuple(sorted(cens, key=lambda g: (cens[g], g))))
        penalties.append(spread(days, horizon))
    return RecoveryFinding(tuple(alphas), tuple(all_days), tuple(orders), max(penalties), len(set(orders)) == 1)
