import numpy as np
import pytest

from thrive.audit import _holm, certify
from thrive.examples import IDENTITY_CHANGES, NEED_CHANGES, biased_decide, fair_decide, need_blind_decide, triage_cases


def test_fair_rule_passes():
    cert = certify(triage_cases(), fair_decide, IDENTITY_CHANGES, NEED_CHANGES)
    assert cert.passed
    assert cert.placebo_flip_rate == 0


def test_rule_that_uses_origin_fails_on_origin_only():
    cert = certify(triage_cases(), biased_decide, IDENTITY_CHANGES, NEED_CHANGES)
    assert not cert.passed
    assert [c.name for c in cert.failures()] == ["origin=syrian"]


def test_rule_that_ignores_need_fails_on_need():
    cert = certify(triage_cases(), need_blind_decide, IDENTITY_CHANGES, NEED_CHANGES)
    assert not cert.passed
    assert [c.name for c in cert.failures()] == ["need=age80"]


def test_noise_alone_is_absorbed_by_the_placebo():
    def noisy(case, seed):
        return fair_decide(case, seed) + np.random.default_rng(seed).normal(0, 1)

    cert = certify(triage_cases(30), noisy, IDENTITY_CHANGES, {}, runs=4, delta=0.2)
    assert cert.placebo_flip_rate == 1
    assert cert.passed


def test_holm_stops_at_first_failure():
    assert _holm([0.001, 0.04, 0.01], 0.05) == [True, True, True]
    assert _holm([0.001, 0.2, 0.01], 0.05) == [True, False, True]
    assert _holm([0.03, 0.03], 0.05) == [False, False]


def test_requires_cases_and_changes():
    with pytest.raises(ValueError):
        certify([], fair_decide, IDENTITY_CHANGES, NEED_CHANGES)
    with pytest.raises(ValueError):
        certify(triage_cases(), fair_decide, {}, {})
