from pathlib import Path

import pytest

from treasury_auctions.parsers import (
    classify_ug,
    first_date,
    gh_number,
    parse_gh_result,
    parse_ke_result,
    parse_ug_invitation,
    parse_ug_result,
    published_ratio_formula,
)

FX = Path(__file__).parent / "fixtures"


def read(name):
    return (FX / name).read_text(encoding="utf-8")


def test_ug_1237_ground_truth_cells():
    r = parse_ug_result(read("ug_1237_result.txt"))
    assert r.doc_type == "ug_bill_result" and not r.blocking
    assert r.event["auction_no"] == 1237
    assert r.event["held_date"] == "2026-11-04"
    assert r.event["settlement_date"] == "2026-11-05"
    got = {row["tenor"]: (row["O"] / 1e9, row["B"] / 1e9, row["A"] / 1e9) for row in r.rows}
    assert got[91] == pytest.approx((15, 81.9349, 4.2349))
    assert got[182] == pytest.approx((35, 60.2513, 10.2513))
    assert got[364] == pytest.approx((300, 933.5267, 424.5267))
    assert {row["cover_formula"] for row in r.rows} == {"B/A"}
    assert r.rows[0]["maturity_date"] == "2027-02-04"
    assert r.rows[0]["B_comp"] + r.rows[0]["B_noncomp"] == r.rows[0]["B"]


def test_ug_docx_runtogether_dates():
    r = parse_ug_result(read("ug_docx_runtogether.txt"))
    assert not r.blocking
    assert r.event["auction_no"] == 1235
    assert r.event["held_date"] == "2026-09-30"
    assert r.event["settlement_date"] == "2026-10-01"


def test_ug_two_digit_year_and_cover_bo():
    r = parse_ug_result(read("ug_2022_twodigit.txt"))
    assert r.event["held_date"] == "2022-05-11"
    assert r.event["settlement_date"] == "2022-05-12"
    # 182-day: 40/50 = 0.8 = B/O while B/A = 1.0
    assert r.rows[1]["cover_formula"] == "B/O"


def test_ug_malformed_number_blocks():
    r = parse_ug_result(read("ug_malformed.txt"))
    assert r.blocking  # never silently repaired


def test_ug_bond_excluded():
    assert classify_ug(read("ug_bond_result.txt")) != "ug_bill_result"


def test_ug_invitation_total_typo_flagged():
    r = parse_ug_invitation(read("ug_invitation_1236.txt"))
    assert r.doc_type == "ug_bill_invitation"
    assert r.event["auction_no"] == 1236
    assert r.event["auction_date"] == "2026-10-21"
    assert r.event["notice_date"] == "2026-10-15"
    assert {x["tenor"]: x["O_announced"] for x in r.rows} == {91: 15e9, 182: 35e9, 364: 300e9}
    assert any("printed total" in f for f in r.flags)


def test_ke_2026_10_26_ground_truth():
    r = parse_ke_result(read("ke_2026-10-26_result.txt"))
    assert not r.blocking, r.blocking
    assert r.event["value_date"] == "2026-10-26"
    assert r.event["issues"] == {91: 2705, 182: 2679, 364: 2634}
    assert [(x["O"], x["B"], x["A"]) for x in r.rows] == [
        (8000.0, 14336.63, 14334.18), (10000.0, 7693.14, 7685.02), (10000.0, 6801.35, 6773.91)]
    assert r.event["printed_totals"] == {"O": 28000.0, "B": 28831.11, "A": 28793.12}
    assert not any("printed total" in f for f in r.flags)  # sums within two-decimal rounding
    nx = r.event["next"]
    assert nx["value_date"] == "2026-11-02" and nx["closure_date"] == "2026-10-29"
    assert nx["offers"][:3] == [8000.0, 10000.0, 10000.0]
    assert r.event["signed_date"] == "2026-10-22"
    # value date must not stand in for the results date
    assert r.event["signed_date"] < r.event["value_date"]


def test_gh_joined_ordinal_date_uses_section_one_only():
    r = parse_gh_result(read("gh_1892_joined_date.txt"))
    assert not r.blocking, r.blocking
    assert r.event["tender_no"] == 1892
    assert r.event["held_date"] == "2024-03-01"  # never the previous tender's 23 Feb
    assert r.event["prev"]["held_date"] == "2024-02-23"
    assert r.event["O_result"] == 4137.0
    assert r.event["next"] == {**r.event["next"], "tender_no": 1893, "target": 4285.0}
    assert sum(x["B"] for x in r.rows) == pytest.approx(4963.25)
    assert sum(x["A"] for x in r.rows) == pytest.approx(4940.25)


def test_gh_malformed_amount_blocks():
    t = read("gh_1892_joined_date.txt").replace("GH¢1,866.37", "GH¢1.141.12")
    r = parse_gh_result(t)
    assert any("malformed" in b or "tenor rows" in b for b in r.blocking)
    assert gh_number("1.141.12") is None


@pytest.mark.parametrize("s,iso", [
    ("HELD ON 08-Nov-2017", "2017-11-08"), ("WEDNESDAY 04-DECEMBER-2019", "2019-12-04"),
    ("1STMARCH 2024", "2024-03-01"), ("30TH OCTOBER 2026", "2026-10-30"), ("November 05, 2026", "2026-11-05"),
    ("DATED 07/03/2022", "2022-03-07"), ("9-Mar-23", "2023-03-09"), ("30-SEP-2026SETTLEMENT", "2026-09-30"),
])
def test_dates(s, iso):
    assert first_date(s) == iso


def test_ratio_formula_identification():
    assert published_ratio_formula(19.348, 15, 81.9349, 4.2349) == "B/A"
    assert published_ratio_formula(0.734, 15, 11.006, 11.006) == "B/O"
    assert published_ratio_formula(2.0, 10, 20, 10) == "ambiguous:B/O|B/A"
    assert published_ratio_formula(9.9, 10, 20, 10) == "inconsistent"
