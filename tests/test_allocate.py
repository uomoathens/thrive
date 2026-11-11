import math

import pytest

from thrive.allocate import Household, Project, allocate, pareto_front, project_values
from thrive.examples import LEVEE_COST, liscow_levees
from thrive.weights import crossover


def test_liscow_property_value():
    a, b = project_values(liscow_levees(), 0)
    assert a == pytest.approx(10.5e6)
    assert b == pytest.approx(9.0e6)


def test_liscow_equity_weights():
    a, b = project_values(liscow_levees(), 1)
    assert a == pytest.approx(6.5e6)
    assert b == pytest.approx(13.0e6)


def test_liscow_decision_flips():
    levees = liscow_levees()
    assert allocate(levees, LEVEE_COST, 0).selected == ("Levee A",)
    assert allocate(levees, LEVEE_COST, 1).selected == ("Levee B",)


def test_liscow_thresholds_match_the_page():
    levees = liscow_levees()
    flip = crossover(lambda e: project_values(levees, e)[0] - project_values(levees, e)[1])
    passes = crossover(lambda e: project_values(levees, e)[1] - LEVEE_COST)
    assert flip == pytest.approx(math.log(10.5 / 9) / math.log(210 / 90), abs=1e-9)
    assert round(flip, 2) == 0.18
    assert round(passes, 2) == 0.29


def test_budget_is_respected():
    projects = [Project(str(i), 3.0, (Household(5.0, 1.0),)) for i in range(5)]
    plan = allocate(projects, 10.0, 0)
    assert plan.cost <= 10.0
    assert len(plan.selected) == 3


def test_exact_beats_greedy_trap():
    projects = [
        Project("big", 10.0, (Household(10.0, 1.0),)),
        Project("small1", 6.0, (Household(7.0, 1.0),)),
        Project("small2", 4.0, (Household(5.0, 1.0),)),
    ]
    assert set(allocate(projects, 10.0, 0).selected) == {"small1", "small2"}


def test_coverage_disparity_reported():
    plan = allocate(liscow_levees(), LEVEE_COST, 0)
    assert plan.coverage_disparity > 0


def test_pareto_front_has_one_plan_per_eta():
    plans = pareto_front(liscow_levees(), LEVEE_COST, [0, 0.5, 1])
    assert [p.eta for p in plans] == [0, 0.5, 1]


def test_rejects_negative_budget():
    with pytest.raises(ValueError):
        allocate(liscow_levees(), -1, 0)
