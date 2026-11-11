import pytest

from thrive.weights import crossover, equity_weights, weighted_benefit


def test_eta_zero_counts_every_unit_the_same():
    assert list(equity_weights([10, 20, 40], 0)) == [1, 1, 1]


def test_poorer_households_weigh_more():
    w = equity_weights([50, 100, 200], 1)
    assert w[0] > w[1] > w[2]


def test_reference_income_has_weight_one():
    assert equity_weights([130], 3, reference=130)[0] == pytest.approx(1)


@pytest.mark.parametrize("bad", [[0, 10], [-5, 10]])
def test_rejects_non_positive_income(bad):
    with pytest.raises(ValueError):
        equity_weights(bad, 1)


def test_rejects_negative_eta():
    with pytest.raises(ValueError):
        equity_weights([10], -1)


def test_weighted_benefit():
    assert weighted_benefit([100, 100], [50, 200], 1, reference=100) == pytest.approx(250)


def test_crossover_finds_root_and_none():
    assert crossover(lambda x: x - 2.5) == pytest.approx(2.5)
    assert crossover(lambda x: x + 1) is None
