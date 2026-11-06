from treasury_auctions.fixtures_run import run_fixtures


def test_fixture_end_to_end(tmp_path):
    assert run_fixtures(keep=tmp_path)
