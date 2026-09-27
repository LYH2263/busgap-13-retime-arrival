import pytest
from app.services.timeparse import parse_actual_arrive

def test_parse_iso_with_t():
    assert parse_actual_arrive("2026-09-17T07:08:00").isoformat() == "2026-09-17T07:08:00"

def test_parse_iso_with_space_and_minutes():
    assert parse_actual_arrive("2026-09-17 07:08").isoformat() == "2026-09-17T07:08:00"

def test_parse_strips_whitespace():
    assert parse_actual_arrive("  2026-09-17 07:08  ").hour == 7

def test_parse_aware_becomes_naive():
    assert parse_actual_arrive("2026-09-17T07:08:00+08:00").tzinfo is None

@pytest.mark.parametrize("bad", ["", "   ", None, 123, "abc", "07:08", "2026-13-40 99:99", "2026/09/17 07:08"])
def test_parse_rejects_empty_or_unparseable(bad):
    with pytest.raises(ValueError):
        parse_actual_arrive(bad)
