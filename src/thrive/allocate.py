from dataclasses import dataclass, field
from itertools import combinations
from typing import Sequence

from thrive.fairness import group_disparity
from thrive.weights import equity_weights


@dataclass(frozen=True)
class Household:
    benefit: float
    income: float
    group: str = ""


@dataclass(frozen=True)
class Project:
    name: str
    cost: float
    households: tuple[Household, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Plan:
    eta: float
    selected: tuple[str, ...]
    cost: float
    benefit: float
    weighted_benefit: float
    coverage_disparity: float


def project_values(projects: Sequence[Project], eta: float, reference: float | None = None) -> list[float]:
    pairs = [(i, h) for i, p in enumerate(projects) for h in p.households]
    values = [0.0] * len(projects)
    if not pairs:
        return values
    w = equity_weights([h.income for _, h in pairs], eta, reference)
    for k, (i, h) in enumerate(pairs):
        values[i] += h.benefit * float(w[k])
    return values


def _best_subset(costs: Sequence[float], values: Sequence[float], budget: float, max_exact: int) -> tuple[int, ...]:
    idx = [i for i, c in enumerate(costs) if c <= budget]
    if len(idx) > max_exact:
        chosen, spent = [], 0.0
        for i in sorted(idx, key=lambda i: values[i] / costs[i] if costs[i] else float("inf"), reverse=True):
            if spent + costs[i] <= budget:
                chosen.append(i)
                spent += costs[i]
        return tuple(sorted(chosen))
    best, best_v, best_c = (), 0.0, 0.0
    for k in range(1, len(idx) + 1):
        for combo in combinations(idx, k):
            c = sum(costs[i] for i in combo)
            if c > budget:
                continue
            v = sum(values[i] for i in combo)
            if v > best_v + 1e-12 or (abs(v - best_v) <= 1e-12 and c < best_c):
                best, best_v, best_c = combo, v, c
    return best


def allocate(projects: Sequence[Project], budget: float, eta: float, reference: float | None = None, max_exact: int = 20) -> Plan:
    if budget < 0:
        raise ValueError("budget must be non-negative")
    values = project_values(projects, eta, reference)
    chosen = set(_best_subset([p.cost for p in projects], values, budget, max_exact))
    covered, groups = [], []
    for i, p in enumerate(projects):
        for h in p.households:
            covered.append(1.0 if i in chosen else 0.0)
            groups.append(h.group)
    disparity = group_disparity(covered, groups) if len(set(groups)) > 1 else 0.0
    return Plan(
        eta=eta,
        selected=tuple(projects[i].name for i in sorted(chosen)),
        cost=float(sum(projects[i].cost for i in chosen)),
        benefit=float(sum(h.benefit for i in chosen for h in projects[i].households)),
        weighted_benefit=float(sum(values[i] for i in chosen)),
        coverage_disparity=float(disparity),
    )


def pareto_front(projects: Sequence[Project], budget: float, etas: Sequence[float], reference: float | None = None) -> list[Plan]:
    return [allocate(projects, budget, e, reference) for e in etas]
