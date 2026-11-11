import math

from thrive.allocate import Household, Project

LEVEE_COST = 10_000_000.0


def recovery_area_a(t: float) -> float:
    return 0.92 * (1 - math.exp(-t / 4)) + 0.08 * (1 - math.exp(-t / 60))


def recovery_area_b(t: float) -> float:
    return 1 / (1 + math.exp(-(t - 20) / 3))


def recovery_example(days: int = 90) -> dict[str, list[float]]:
    return {
        "Area A": [recovery_area_a(t) for t in range(days + 1)],
        "Area B": [recovery_area_b(t) for t in range(days + 1)],
    }


def liscow_levees() -> list[Project]:
    a = Project("Levee A", LEVEE_COST, tuple(Household(210_000.0, 210_000.0, "A") for _ in range(50)))
    b = Project("Levee B", LEVEE_COST, tuple(Household(90_000.0, 90_000.0, "B") for _ in range(100)))
    return [a, b]


def triage_cases(n: int = 15) -> list[dict]:
    cases = []
    for i in range(n):
        cases.append({
            "depth": 0.4 + 0.1 * (i % 5),
            "people": 2 + i % 4,
            "minutes": 20 + 5 * (i % 3),
            "need": False,
            "origin": "local",
            "gender": "male",
            "area": "residential",
            "status": "resident",
        })
    return cases


def fair_decide(case: dict, seed: int) -> float:
    return case["depth"] * 10 + case["people"] + case["minutes"] / 10 + (5.0 if case["need"] else 0.0)


def biased_decide(case: dict, seed: int) -> float:
    return fair_decide(case, seed) - (2.0 if case["origin"] != "local" else 0.0)


def need_blind_decide(case: dict, seed: int) -> float:
    return case["depth"] * 10 + case["people"] + case["minutes"] / 10


IDENTITY_CHANGES = {
    "origin=syrian": lambda c: {**c, "origin": "syrian"},
    "gender=female": lambda c: {**c, "gender": "female"},
    "area=social_housing": lambda c: {**c, "area": "social_housing"},
    "status=asylum_seeker": lambda c: {**c, "status": "asylum_seeker"},
}

NEED_CHANGES = {
    "need=age80": lambda c: {**c, "need": True},
}
