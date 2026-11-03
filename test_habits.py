import sqlite3
from datetime import date, datetime, timedelta

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
    assert all(
        habit.created_timestamp is not None
        for habit in store.list_habits()
    )

    meal_prep_dates = store.completion_dates("Meal prep")
    assert len(meal_prep_dates) == 4
    assert meal_prep_dates == [
        date(2026, 9, 2),
        date(2026, 9, 9),
        date(2026, 9, 16),
        date(2026, 9, 23),
    ]
    assert all(
        completion.completed_at is not None
        for completion in store.completion_records("Meal prep")
    )


def test_create_validates_names_periods_and_duplicates(store):
    habit = store.create_habit("Stretch", "daily", "Move between study sessions.")

    assert habit.name == "Stretch"
    assert habit.period == "daily"
    assert habit.description == "Move between study sessions."
    assert habit.created_timestamp is not None
    assert habit.created_timestamp.tzinfo is not None
    with HabitStore(store.database_path) as reopened:
        assert reopened.get_habit("Stretch").created_timestamp == habit.created_timestamp
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


def test_completion_records_store_timezone_aware_timestamps(store):
    store.create_habit("Read", "daily")
    completed_at = "2026-09-27T18:42:15+02:00"

    assert store.record_completion("Read", completed_at=completed_at)

    record = store.completion_records("Read")[0]
    assert record.completed_on == date(2026, 9, 27)
    assert record.completed_at == datetime.fromisoformat(completed_at)
    assert record.completed_at.utcoffset() == timedelta(hours=2)
    with HabitStore(store.database_path) as reopened:
        assert reopened.completion_records("Read")[0].completed_at == record.completed_at


def test_completion_timestamp_requires_timezone_and_matching_date(store):
    store.create_habit("Read", "daily")

    with pytest.raises(ValueError, match="include a timezone"):
        store.record_completion(
            "Read",
            completed_at=datetime(2026, 9, 27, 18, 42, 15),
        )
    with pytest.raises(ValueError, match="must match the date"):
        store.record_completion(
            "Read",
            "2026-09-28",
            completed_at="2026-09-27T18:42:15+02:00",
        )


def test_legacy_database_migration_preserves_dates_without_inventing_times(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE habits (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                period TEXT NOT NULL CHECK (period IN ('daily', 'weekly')),
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE completions (
                habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                completed_on TEXT NOT NULL,
                PRIMARY KEY (habit_id, completed_on)
            );
            INSERT INTO habits (id, name, period, created_at)
                VALUES (1, 'Read', 'daily', '2026-09-01');
            INSERT INTO completions (habit_id, completed_on)
                VALUES (1, '2026-09-27');
            """
        )

    with HabitStore(database) as migrated:
        assert migrated.get_habit("Read").created_timestamp is None
        assert migrated.completion_dates("Read") == [date(2026, 9, 27)]
        assert migrated.completion_records("Read")[0].completed_at is None
        assert migrated.record_completion(
            "Read",
            completed_at="2026-09-28T18:42:15+02:00",
        )
        assert migrated.completion_dates("Read") == [
            date(2026, 9, 27),
            date(2026, 9, 28),
        ]


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


def test_cli_supports_habit_workflows_and_completion_history(tmp_path, capsys):
    database = str(tmp_path / "habits.sqlite3")
    today = date.today().isoformat()
    completed_at = datetime.now().astimezone().replace(microsecond=0)

    assert main(["--db", database, "init", "--no-sample-data"]) == 0
    assert main(["--db", database, "create", "Walk", "--period", "daily"]) == 0
    assert main(
        [
            "--db",
            database,
            "complete",
            "Walk",
            "--at",
            completed_at.isoformat(),
        ]
    ) == 0
    assert main(["--db", database, "analyze", "Walk", "--days", "1"]) == 0
    assert "Walk (daily): 100% (1/1 periods)" in capsys.readouterr().out
    assert main(["--db", database, "history", "Walk"]) == 0
    history_output = capsys.readouterr().out
    assert "Walk:" in history_output
    assert completed_at.isoformat() in history_output
    assert main(["--db", database, "complete", "Walk", "--date", today]) == 0
    assert main(["--db", database, "delete", "Walk"]) == 0


def test_cli_without_subcommand_lists_habits_with_initialization_hint(tmp_path, capsys):
    database = str(tmp_path / "habits.sqlite3")

    assert main(["--db", database]) == 0

    assert "No habits found" in capsys.readouterr().out
