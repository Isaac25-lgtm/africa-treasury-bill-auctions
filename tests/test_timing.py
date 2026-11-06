import numpy as np
import pandas as pd

from treasury_auctions.forecast import _features, alert_budget, fit_predict, prev_business_day


def rows():
    # three auctions of one series; the second's result is (artificially) published late
    return pd.DataFrame(dict(
        country="UG", event_id=["e1", "e2", "e3"], series="UG-91", tenor="91",
        held_date=["2024-01-03", "2024-01-17", "2024-01-31"],
        O_result=[10.0, 10.0, 10.0], B=[20.0, 5.0, 30.0], A=[10.0, 5.0, 10.0],
        available_from=["2024-01-04", "2024-02-15", "2024-02-01"],  # e2 released after e3's origin
        release_date=["2024-01-03", "2024-02-14", "2024-01-31"],
        O_announced=[10.0, 10.0, 12.0], first_public_date=["2023-12-28", "2024-01-11", "2024-01-31"],
    ))


def test_prev_business_day_skips_weekend():
    assert prev_business_day("2024-01-08") == "2024-01-05"  # Monday -> Friday
    assert prev_business_day("2024-01-10") == "2024-01-09"


def test_future_result_excluded_and_old_lag_used():
    f = _features(rows(), strict=True).set_index("event_id")
    # e3 (origin 2024-01-30): e2 not yet public; last eligible is e1 (coverage 2.0, met)
    assert f.loc["e3", "n_hist"] == 1
    assert f.loc["e3", "cov_last"] == 2.0
    # same-auction outcome never used: e1 has no history at all
    assert f.loc["e1", "n_hist"] == 0 and np.isnan(f.loc["e1", "cov_last"])


def test_announcement_after_origin_ignored():
    f = _features(rows(), strict=True).set_index("event_id")
    # e3's announcement is first public on the bid day itself, after the previous-business-day origin
    assert not f.loc["e3", "offer_known"] and np.isnan(f.loc["e3", "log_offer"])
    assert f.loc["e2", "offer_known"]


def test_labels_and_classes():
    f = _features(rows(), strict=True).set_index("event_id")
    assert list(f.label) == [0, 1, 0]  # e2: A < O with B < O


def test_absent_classes_keep_probability_mapping():
    rng = np.random.default_rng(0)
    tr = pd.DataFrame({"x": rng.normal(size=60), "label": [0] * 30 + [2] * 30})  # class 1 never seen
    te = pd.DataFrame({"x": rng.normal(size=5)})
    p = fit_predict(tr, te, ["x"], "logit", 1)
    assert p.shape == (5, 3) and np.allclose(p.sum(axis=1), 1) and np.all(np.isfinite(p))
    assert (p[:, 1] < 1e-5).all()


def test_too_little_training_data_returns_none():
    tr = pd.DataFrame({"x": [1.0, 2.0], "label": [0, 1]})
    assert fit_predict(tr, tr, ["x"], "logit", 1) is None


def test_alert_threshold_uses_only_earlier_folds():
    n = 60
    df = pd.DataFrame(dict(level="tenor", country="UG", model="m", event_id=[f"e{i}" for i in range(n)],
                           held_date=pd.date_range("2023-01-02", periods=n, freq="7D").strftime("%Y-%m-%d"),
                           fold=pd.date_range("2023-01-01", periods=n, freq="7D").strftime("%Y-%m-%d"),
                           p0=np.linspace(0.9, 0.1, n), label=[0] * n, S=0.0))
    a = alert_budget(df)
    assert set(a.columns) >= {"alert_rate", "misses_alerted", "false_alerts"}
    # no alerts possible before 20 earlier predictions exist
    assert a.alert_rate.max() <= 1.0
