"""SQLite-backed habit definitions and completion history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal

    HabitPeriod = Literal["daily", "weekly"]
else:
    HabitPeriod = str

DEFAULT_HABITS: tuple[tuple[str, HabitPeriod, str], ...] = (
    ("Read 20 pages", "daily", "Spend time reading each day."),
    ("Exercise", "daily", "Do some intentional physical activity."),
    ("Journal", "daily", "Write a short daily reflection."),
    ("Meal prep", "weekly", "Prepare meals for the week."),
    ("Review weekly goals", "weekly", "Review progress and set priorities."),
)


@dataclass(frozen=True)
class Habit:
    """A habit tracked daily or once per calendar week."""

    id: int
    name: str
    period: HabitPeriod
    description: str
    created_at: date
    created_timestamp: datetime | None = None


@dataclass(frozen=True)
class HabitCompletion:
    """A habit completion and its recorded timestamp, if it predates timestamp support."""

    completed_on: date
    completed_at: datetime | None


class HabitStore:
    """Persist habits and timestamped completions in a SQLite database."""

    def __init__(self, database_path: str | Path = "habits.sqlite3") -> None:
        self.database_path = str(database_path)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                period TEXT NOT NULL CHECK (period IN ('daily', 'weekly')),
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                created_timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS completions (
                habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                completed_on TEXT NOT NULL,
                completed_at TEXT,
                PRIMARY KEY (habit_id, completed_on)
            );
            """
        )
        habit_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(habits)")
        }
        if "created_timestamp" not in habit_columns:
            with self.connection:
                self.connection.execute(
                    "ALTER TABLE habits ADD COLUMN created_timestamp TEXT"
                )
        completion_columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(completions)")
        }
        if "completed_at" not in completion_columns:
            with self.connection:
                self.connection.execute(
                    "ALTER TABLE completions ADD COLUMN completed_at TEXT"
                )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> HabitStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _habit_from_row(row: sqlite3.Row) -> Habit:
        return Habit(
            id=row["id"],
            name=row["name"],
            period=row["period"],
            description=row["description"],
            created_at=date.fromisoformat(row["created_at"]),
            created_timestamp=(
                datetime.fromisoformat(row["created_timestamp"])
                if row["created_timestamp"] is not None
                else None
            ),
        )

    @staticmethod
    def _parse_date(value: date | str | None) -> date:
        if value is None:
            return datetime.now().astimezone().date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Date must use YYYY-MM-DD format.") from error

    @staticmethod
    def _parse_timestamp(value: datetime | str) -> datetime:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError(
                    "Completion timestamp must use ISO 8601 format with a timezone."
                ) from error
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Completion timestamp must include a timezone.")
        return value

    def create_habit(
        self,
        name: str,
        period: HabitPeriod,
        description: str = "",
    ) -> Habit:
        name = name.strip()
        if not name:
            raise ValueError("Habit name cannot be empty.")
        if period not in ("daily", "weekly"):
            raise ValueError("Habit period must be 'daily' or 'weekly'.")

        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO habits
                        (name, period, description, created_at, created_timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        period,
                        description.strip(),
                        date.today().isoformat(),
                        datetime.now().astimezone().isoformat(timespec="seconds"),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(f"A habit named '{name}' already exists.") from error
        return self.get_habit(name)

    def get_habit(self, name: str) -> Habit:
        row = self.connection.execute(
            "SELECT * FROM habits WHERE name = ? COLLATE NOCASE", (name.strip(),)
        ).fetchone()
        if row is None:
            raise KeyError(f"Habit '{name}' was not found.")
        return self._habit_from_row(row)

    def list_habits(self) -> list[Habit]:
        rows = self.connection.execute(
            "SELECT * FROM habits ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [self._habit_from_row(row) for row in rows]

    def delete_habit(self, name: str) -> None:
        habit = self.get_habit(name)
        with self.connection:
            self.connection.execute("DELETE FROM habits WHERE id = ?", (habit.id,))

    def record_completion(
        self,
        name: str,
        completed_on: date | str | None = None,
        *,
        completed_at: datetime | str | None = None,
    ) -> bool:
        habit = self.get_habit(name)
        if completed_at is None:
            timestamp = datetime.now().astimezone()
            if completed_on is not None:
                completion_date = self._parse_date(completed_on)
                timestamp = datetime.combine(completion_date, timestamp.timetz())
        else:
            timestamp = self._parse_timestamp(completed_at)
            completion_date = timestamp.date()
            if completed_on is not None and self._parse_date(completed_on) != completion_date:
                raise ValueError(
                    "Completion date must match the date in the completion timestamp."
                )
        if completed_on is not None:
            completion_date = self._parse_date(completed_on)
        else:
            completion_date = timestamp.date()
        timestamp_text = timestamp.isoformat(timespec="seconds")
        with self.connection:
            if habit.period == "weekly":
                week_start = completion_date - timedelta(days=completion_date.weekday())
                week_end = week_start + timedelta(days=6)
                existing = self.connection.execute(
                    "SELECT 1 FROM completions WHERE habit_id = ? AND completed_on BETWEEN ? AND ?",
                    (habit.id, week_start.isoformat(), week_end.isoformat()),
                ).fetchone()
                if existing:
                    return False
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO completions
                    (habit_id, completed_on, completed_at)
                VALUES (?, ?, ?)
                """,
                (habit.id, completion_date.isoformat(), timestamp_text),
            )
        return cursor.rowcount == 1

    def completion_records(
        self,
        name: str,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> list[HabitCompletion]:
        habit = self.get_habit(name)
        query = """
            SELECT completed_on, completed_at
            FROM completions
            WHERE habit_id = ?
        """
        parameters: list[int | str] = [habit.id]
        if start_date is not None:
            query += " AND completed_on >= ?"
            parameters.append(self._parse_date(start_date).isoformat())
        if end_date is not None:
            query += " AND completed_on <= ?"
            parameters.append(self._parse_date(end_date).isoformat())
        query += " ORDER BY completed_on, completed_at"
        rows = self.connection.execute(query, parameters).fetchall()
        return [
            HabitCompletion(
                completed_on=date.fromisoformat(row["completed_on"]),
                completed_at=(
                    datetime.fromisoformat(row["completed_at"])
                    if row["completed_at"] is not None
                    else None
                ),
            )
            for row in rows
        ]

    def completion_dates(
        self,
        name: str,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> list[date]:
        habit = self.get_habit(name)
        query = "SELECT completed_on FROM completions WHERE habit_id = ?"
        parameters: list[int | str] = [habit.id]
        if start_date is not None:
            query += " AND completed_on >= ?"
            parameters.append(self._parse_date(start_date).isoformat())
        if end_date is not None:
            query += " AND completed_on <= ?"
            parameters.append(self._parse_date(end_date).isoformat())
        query += " ORDER BY completed_on"
        rows = self.connection.execute(query, parameters).fetchall()
        return [date.fromisoformat(row["completed_on"]) for row in rows]

    def seed_defaults(
        self,
        today: date | None = None,
        include_sample_data: bool = True,
    ) -> int:
        """Add five defaults and optionally seed four completed calendar weeks."""
        if self.connection.execute("SELECT COUNT(*) FROM habits").fetchone()[0]:
            return 0

        today = today or date.today()
        sample_timezone = datetime.now().astimezone().tzinfo
        created_timestamp = datetime.combine(
            today,
            time(12),
            tzinfo=sample_timezone,
        ).isoformat(timespec="seconds")
        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO habits
                    (name, period, description, created_at, created_timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (*habit, today.isoformat(), created_timestamp)
                    for habit in DEFAULT_HABITS
                ],
            )

            if include_sample_data:
                current_week_start = today - timedelta(days=today.weekday())
                first_day = current_week_start - timedelta(weeks=4)
                habits = self.list_habits()
                for habit_index, habit in enumerate(habits):
                    if habit.period == "daily":
                        for offset in range(28):
                            if (offset + habit_index) % 6 != 0:
                                completion_day = first_day + timedelta(days=offset)
                                self.connection.execute(
                                    """
                                    INSERT INTO completions
                                        (habit_id, completed_on, completed_at)
                                    VALUES (?, ?, ?)
                                    """,
                                    (
                                        habit.id,
                                        completion_day.isoformat(),
                                        datetime.combine(
                                            completion_day,
                                            time(12),
                                            tzinfo=sample_timezone,
                                        ).isoformat(timespec="seconds"),
                                    ),
                                )
                    else:
                        for week in range(4):
                            completion_day = first_day + timedelta(days=week * 7 + habit_index % 5)
                            self.connection.execute(
                                """
                                INSERT INTO completions
                                    (habit_id, completed_on, completed_at)
                                VALUES (?, ?, ?)
                                """,
                                (
                                    habit.id,
                                    completion_day.isoformat(),
                                    datetime.combine(
                                        completion_day,
                                        time(12),
                                        tzinfo=sample_timezone,
                                    ).isoformat(timespec="seconds"),
                                ),
                            )
        return len(DEFAULT_HABITS)