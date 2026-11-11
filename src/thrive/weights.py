from typing import Sequence

import numpy as np


def equity_weights(incomes: Sequence[float], eta: float, reference: float | None = None) -> np.ndarray:
    y = np.asarray(incomes, dtype=float)
    if np.any(y <= 0):
        raise ValueError("incomes must be positive")
    if eta < 0:
        raise ValueError("eta must be non-negative")
    ref = float(y.mean()) if reference is None else float(reference)
    return (ref / y) ** eta


def weighted_benefit(benefits: Sequence[float], incomes: Sequence[float], eta: float, reference: float | None = None) -> float:
    b = np.asarray(benefits, dtype=float)
    return float((b * equity_weights(incomes, eta, reference)).sum())


def crossover(f, lo: float = 0.0, hi: float = 10.0, tol: float = 1e-10) -> float | None:
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(hi - lo) < tol or fm == 0:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2
