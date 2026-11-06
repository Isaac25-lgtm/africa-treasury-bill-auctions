"""BoU invitations join to results by scheduled auction date first, then by printed number."""

import pandas as pd

from treasury_auctions.panel import _ug_invitation_event_ids

EV = pd.DataFrame({
    "event_id": ["UG-996", "UG-997", "UG-1171", "UG-1171-2024-02-14", "UG-1176"],
    "auction_no": [996, 997, 1171, 1171, 1176],
    "held_date": ["2017-04-26", "2017-05-10", "2024-01-31", "2024-02-14", "2024-04-11"],
})


def _inv(no, auction_date, url="https://bou.or.ug/uploads/x.pdf"):
    return {"auction_no": no, "auction_date": auction_date, "url": url}


def test_misprinted_invitation_joins_by_date():
    inv = pd.DataFrame([_inv(996, "2017-05-10")])
    ids, flags = _ug_invitation_event_ids(inv, EV)
    assert ids.tolist() == ["UG-997"]
    assert "prints #996" in flags.iloc[0]


def test_reused_result_number_joins_by_date():
    inv = pd.DataFrame([_inv(1172, "2024-02-14")])
    ids, _ = _ug_invitation_event_ids(inv, EV)
    assert ids.tolist() == ["UG-1171-2024-02-14"]


def test_rescheduled_auction_joins_by_number_with_flag():
    inv = pd.DataFrame([_inv(1176, "2024-04-10")])
    ids, flags = _ug_invitation_event_ids(inv, EV)
    assert ids.tolist() == ["UG-1176"]
    assert "scheduled 2024-04-10 but held 2024-04-11" in flags.iloc[0]


def test_unmatched_invitation_keeps_printed_number():
    inv = pd.DataFrame([_inv(1221, None, "https://bou.or.ug/uploads/Issue_No_1221_Auction_scheduled_for_28_January_2026.pdf")])
    ids, flags = _ug_invitation_event_ids(inv, EV)
    assert ids.tolist() == ["UG-1221"]
    assert flags.iloc[0] == ""


def test_number_match_too_far_in_time_is_not_joined():
    inv = pd.DataFrame([_inv(996, "2017-06-30")])
    ids, flags = _ug_invitation_event_ids(inv, EV)
    # falls through to the printed-number key without a join flag; the later pre-close date check
    # (first public on or before the held date) decides whether it is ever used as an announced offer
    assert ids.tolist() == ["UG-996"]
    assert flags.iloc[0] == ""
