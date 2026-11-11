import pytest

from thrive.fairness import group_disparity


def test_equal_groups_have_no_disparity():
    assert group_disparity([1, 1, 0, 0], ["a", "b", "a", "b"]) == pytest.approx(0)


def test_disparity_value():
    assert group_disparity([1, 1, 0, 0], ["a", "a", "b", "b"]) == pytest.approx(1.0)


def test_length_mismatch():
    with pytest.raises(ValueError):
        group_disparity([1, 0], ["a"])
