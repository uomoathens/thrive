import pytest

from thrive.examples import recovery_example
from thrive.recovery import recovery_day, robust_recovery, spread


def test_recovery_day_basic():
    assert recovery_day([0.2, 0.5, 0.91, 0.95], 1.0, 0.9) == 2


def test_recovery_day_needs_consecutive_days():
    series = [0.5, 0.95, 0.6, 0.92, 0.93, 0.94]
    assert recovery_day(series, 1.0, 0.9, persistence=1) == 1
    assert recovery_day(series, 1.0, 0.9, persistence=3) == 3


def test_recovery_day_never():
    assert recovery_day([0.1, 0.2], 1.0, 0.9) is None


@pytest.mark.parametrize("alpha", [0, -0.1, 1.5])
def test_recovery_day_rejects_bad_alpha(alpha):
    with pytest.raises(ValueError):
        recovery_day([1.0], 1.0, alpha)


def test_spread_censors_unrecovered_at_horizon():
    assert spread({"a": 2, "b": None}, horizon=10) == pytest.approx(8.0)


def test_example_matches_the_page():
    groups = recovery_example()
    finding = robust_recovery(groups, {g: 1.0 for g in groups}, [0.90, 0.97])
    assert finding.days[0] == {"Area A": 14, "Area B": 27}
    assert finding.days[1] == {"Area A": 59, "Area B": 31}
    assert finding.orders == (("Area A", "Area B"), ("Area B", "Area A"))
    assert finding.stable is False
    assert finding.penalty == pytest.approx(28.0)


def test_finding_kept_when_order_holds():
    groups = {"fast": [0.5, 0.95, 1.0, 1.0], "slow": [0.1, 0.3, 0.92, 0.99]}
    finding = robust_recovery(groups, {"fast": 1.0, "slow": 1.0}, [0.9, 0.95])
    assert finding.stable is True
