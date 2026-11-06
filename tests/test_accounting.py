import math

import numpy as np
import pandas as pd
import pytest

from treasury_auctions.measures import (
    across_tenors,
    auction_wide,
    maturity_profile,
    near_threshold_mixed,
    outcome_class,
    shortfall_parts,
    volume_share,
    weighted_maturity,
)


@pytest.mark.parametrize(
    "O,B,A,S,D,R",
    [(100, 70, 50, 50, 30, 20), (100, 130, 70, 30, 0, 30), (100, 150, 120, 0, 0, 0), (100, 0, 0, 100, 100, 0)],
)
def test_handoff_decomposition_cases(O, B, A, S, D, R):
    s, d, r = shortfall_parts([O], [B], [A])
    assert (s[0], d[0], r[0]) == (S, D, R)
    assert s[0] == d[0] + r[0]


def test_identity_random():
    rng = np.random.default_rng(1)
    O = rng.uniform(1, 100, 500)
    B = rng.uniform(0, 200, 500)
    A = B * rng.uniform(0, 1, 500)
    S, D, R = shortfall_parts(O, B, A)
    assert np.allclose(S, D + R)
    assert (R >= 0).all() and (D >= 0).all()


def test_aggregate_vs_tenor_and_maturity():
    rows = pd.DataFrame({"country": "X", "event_id": "e1", "tenor": [91, 364], "O": [50, 50], "B": [60, 90],
                         "A": [25, 75]})
    agg = auction_wide(rows)
    assert agg.S.iloc[0] == 0
    ten = across_tenors(rows)
    assert ten.S_tenor.iloc[0] == 25
    mp = maturity_profile(rows)
    assert mp.mat_offered.iloc[0] == pytest.approx(227.5)
    assert mp.mat_accepted.iloc[0] == pytest.approx(295.75)
    assert mp.mat_shift.iloc[0] == pytest.approx(68.25)


def test_no_acceptance_gives_undefined_maturity():
    assert math.isnan(weighted_maturity([0, 0, 0], [91, 182, 364]))
    rows = pd.DataFrame({"country": "X", "event_id": "e", "tenor": [91, 182, 364], "O": [1, 1, 1], "B": [0, 0, 0],
                         "A": [0, 0, 0]})
    assert math.isnan(maturity_profile(rows).mat_accepted.iloc[0])


def test_volume_share_undefined_without_shortfall():
    assert math.isnan(volume_share([0, 0], [0, 0]))
    assert volume_share([30, 0], [50, 30]) == pytest.approx(30 / 80)


def test_classes_and_threshold_ties():
    O, B, A = [100, 100, 100, 100], [70, 130, 150, 100], [50, 70, 120, 95]
    assert list(outcome_class(O, B, A)) == [1, 2, 0, 2]
    # exact tie at materiality boundary counts as met
    assert outcome_class([100], [100], [95], tol=0.05)[0] == 0
    assert outcome_class([100], [100], [94.99], tol=0.05)[0] == 2
    # B in [(1-tol)O, O): policy keeps class 1, pilot convention moves it to 2
    assert outcome_class([100], [97], [80], tol=0.05, convention="policy")[0] == 1
    assert outcome_class([100], [97], [80], tol=0.05, convention="pilot")[0] == 2
    assert near_threshold_mixed([100], [97], [80], 0.05)[0]


def test_uganda_1237_ground_truth():
    rows = pd.DataFrame({"country": "UG", "event_id": "1237", "tenor": [91, 182, 364], "O": [15, 35, 300],
                         "B": [81.9349, 60.2513, 933.5267], "A": [4.2349, 10.2513, 424.5267]})
    agg = auction_wide(rows)
    assert agg.O.iloc[0] == pytest.approx(350)
    assert agg.B.iloc[0] == pytest.approx(1075.7129)
    assert agg.A.iloc[0] == pytest.approx(439.0129)
    assert agg.S.iloc[0] == 0  # total filled
    ten = across_tenors(rows)
    assert ten.tenor_misses.iloc[0] == 2  # 91 and 182 under-filled
    assert ten.D_tenor.iloc[0] == 0  # bids exceeded every tenor offer
