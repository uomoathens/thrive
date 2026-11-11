from typing import Hashable, Sequence

import numpy as np


def group_disparity(outcomes: Sequence[float], groups: Sequence[Hashable]) -> float:
    y = np.asarray(outcomes, dtype=float)
    g = np.asarray(groups, dtype=object)
    if y.shape[0] != g.shape[0]:
        raise ValueError("outcomes and groups must have the same length")
    if y.size == 0:
        raise ValueError("no outcomes")
    overall = y.mean()
    return float(sum(abs(y[g == k].mean() - overall) for k in dict.fromkeys(g.tolist())))
