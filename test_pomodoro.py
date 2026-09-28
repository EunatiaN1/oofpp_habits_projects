from main import build_session_plan, format_time, get_break_type


def test_format_time():
    assert format_time(0) == "00:00"
    assert format_time(65) == "01:05"


def test_get_break_type():
    assert get_break_type(1) == "short"
    assert get_break_type(4) == "long"


def test_build_session_plan():
    plan = build_session_plan(4, 25 * 60, 5 * 60, 15 * 60)
    assert plan[0] == ("work", 1500)
    assert plan[1] == ("short_break", 300)
    assert plan[4] == ("work", 1500)
    assert plan[7] == ("long_break", 900)
    assert len(plan) == 8
