from datetime import date, timedelta

import pytest

from habit_analytics import analyze_habit
from habit_cli import main
from habit_tracker import DEFAULT_HABITS, Habit, HabitStore


@pytest.fixture
def store(tmp_path):
    habit_store = HabitStore(tmp_path / "habits.sqlite3")
    yield habit_store
    habit_store.close()


def test_seed_defaults_adds_five_habits_and_four_weeks(store):
    today = date(2026, 9, 28)

    assert store.seed_defaults(today=today) == 5
    assert store.seed_defaults(today=today) == 0
    assert len(store.list_habits()) == len(DEFAULT_HABITS)

    meal_prep_dates = store.completion_dates("Meal prep")
    assert len(meal_prep_dates) == 4
    assert meal_prep_dates == [
        date(2026, 9, 2),
        date(2026, 9, 9),
        date(2026, 9, 16),
        date(2026, 9, 23),
    ]


def test_create_validates_names_periods_and_duplicates(store):
    habit = store.create_habit("Stretch", "daily", "Move between study sessions.")

    assert habit.name == "Stretch"
    assert habit.period == "daily"
    assert habit.description == "Move between study sessions."
    with pytest.raises(ValueError, match="already exists"):
        store.create_habit("stretch", "daily")
    with pytest.raises(ValueError, match="period"):
        store.create_habit("Meditate", "monthly")
    with pytest.raises(ValueError, match="cannot be empty"):
        store.create_habit("  ", "daily")


def test_daily_completion_is_idempotent_and_dates_can_be_filtered(store):
    store.create_habit("Read", "daily")

    assert store.record_completion("Read", "2026-09-27")
    assert not store.record_completion("Read", date(2026, 9, 27))
    assert store.record_completion("Read", "2026-09-28")
    assert store.completion_dates("Read", "2026-09-28", "2026-09-28") == [
        date(2026, 9, 28)
    ]
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        store.record_completion("Read", "09/28/2026")


def test_weekly_completion_can_only_be_recorded_once_per_calendar_week(store):
    store.create_habit("Plan week", "weekly")

    assert store.record_completion("Plan week", "2026-12-28")
    assert not store.record_completion("Plan week", "2027-01-01")
    assert len(store.completion_dates("Plan week")) == 1


def test_delete_removes_habit_and_completion_history(store):
    store.create_habit("Journal", "daily")
    store.record_completion("Journal", "2026-09-28")

    store.delete_habit("Journal")

    assert store.list_habits() == []
    with pytest.raises(KeyError, match="was not found"):
        store.completion_dates("Journal")


def test_daily_analytics_reports_rate_and_streaks():
    today = date(2026, 9, 28)
    habit = Habit(1, "Read", "daily", "", today)
    completions = [today - timedelta(days=offset) for offset in (0, 1, 2, 4)]

    stats = analyze_habit(habit, completions, today=today, days=5)

    assert stats.completed_periods == 4
    assert stats.total_periods == 5
    assert stats.completion_rate == 80
    assert stats.current_streak == 3
    assert stats.longest_streak == 3


def test_weekly_analytics_groups_monday_to_sunday():
    today = date(2026, 9, 28)
    habit = Habit(1, "Plan", "weekly", "", today)
    completions = [date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21)]

    stats = analyze_habit(habit, completions, today=today, days=22)

    assert stats.completed_periods == 3
    assert stats.total_periods == 4
    assert stats.current_streak == 0
    assert stats.longest_streak == 3


def test_analytics_rejects_empty_window():
    habit = Habit(1, "Read", "daily", "", date(2026, 9, 28))

    with pytest.raises(ValueError, match="at least one day"):
        analyze_habit(habit, [], days=0)


def test_cli_supports_init_create_complete_analyze_and_delete(tmp_path, capsys):
    database = str(tmp_path / "habits.sqlite3")

    assert main(["--db", database, "init", "--no-sample-data"]) == 0
    assert main(["--db", database, "create", "Walk", "--period", "daily"]) == 0
    assert main(["--db", database, "complete", "Walk", "--date", "2026-09-28"]) == 0
    assert main(["--db", database, "analyze", "Walk", "--days", "1"]) == 0
    assert "Walk (daily): 100% (1/1 periods)" in capsys.readouterr().out
    assert main(["--db", database, "delete", "Walk"]) == 0


def test_cli_without_subcommand_lists_habits_with_initialization_hint(tmp_path, capsys):
    database = str(tmp_path / "habits.sqlite3")

    assert main(["--db", database]) == 0

    assert "No habits found" in capsys.readouterr().out
