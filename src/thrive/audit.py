from dataclasses import dataclass
from typing import Callable, Mapping, Sequence, TypeVar

import numpy as np

C = TypeVar("C")


@dataclass(frozen=True)
class Contrast:
    name: str
    kind: str
    estimate: float
    bound: float
    p_value: float
    passed: bool


@dataclass(frozen=True)
class Certificate:
    passed: bool
    placebo_flip_rate: float
    contrasts: tuple[Contrast, ...]
    delta: float
    gamma: float
    alpha: float
    cases: int
    runs: int

    def failures(self) -> tuple[Contrast, ...]:
        return tuple(c for c in self.contrasts if not c.passed)


def _holm(p_values: Sequence[float], alpha: float) -> list[bool]:
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    passed = [False] * m
    for rank, i in enumerate(order):
        if p_values[i] <= alpha / (m - rank):
            passed[i] = True
        else:
            break
    return passed


def certify(
    cases: Sequence[C],
    decide: Callable[[C, int], float],
    identity_changes: Mapping[str, Callable[[C], C]],
    need_changes: Mapping[str, Callable[[C], C]],
    runs: int = 2,
    delta: float = 0.05,
    gamma: float = 0.8,
    alpha: float = 0.05,
    tol: float = 1e-9,
    n_boot: int = 2000,
    seed: int = 0,
) -> Certificate:
    if not cases:
        raise ValueError("no cases")
    if not identity_changes and not need_changes:
        raise ValueError("no changes to test")
    n = len(cases)
    base = np.array([[decide(c, r) for r in range(runs)] for c in cases], dtype=float)
    placebo = np.array([[decide(c, r + runs) for r in range(runs)] for c in cases], dtype=float)
    placebo_flip = (np.abs(placebo - base) > tol).mean(axis=1)
    rng = np.random.default_rng(seed)
    boot = rng.integers(0, n, size=(n_boot, n))
    names, kinds, estimates, bounds, p_values = [], [], [], [], []
    for name, change in identity_changes.items():
        scores = np.array([[decide(change(c), r) for r in range(runs)] for c in cases], dtype=float)
        flip = (np.abs(scores - base) > tol).mean(axis=1)
        excess = flip - placebo_flip
        est = float(excess.mean())
        dist = excess[boot].mean(axis=1)
        names.append(name)
        kinds.append("identity")
        estimates.append(est)
        bounds.append(float(np.quantile(dist, 0.95)))
        p_values.append(float((np.sum(dist >= delta) + 1) / (n_boot + 1)))
    for name, change in need_changes.items():
        scores = np.array([[decide(change(c), r) for r in range(runs)] for c in cases], dtype=float)
        raised = (scores > base + tol).mean(axis=1)
        est = float(raised.mean())
        dist = raised[boot].mean(axis=1)
        names.append(name)
        kinds.append("need")
        estimates.append(est)
        bounds.append(float(np.quantile(dist, 0.05)))
        p_values.append(float((np.sum(dist < gamma) + 1) / (n_boot + 1)))
    passed = _holm(p_values, alpha)
    contrasts = tuple(Contrast(*row) for row in zip(names, kinds, estimates, bounds, p_values, passed))
    return Certificate(all(passed), float(placebo_flip.mean()), contrasts, delta, gamma, alpha, n, runs)
