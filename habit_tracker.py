"""SQLite-backed habit definitions and completion history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

HabitPeriod = Literal["daily", "weekly"]

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


class HabitStore:
    """Persist habits and dated completions in a SQLite database."""

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
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS completions (
                habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                completed_on TEXT NOT NULL,
                PRIMARY KEY (habit_id, completed_on)
            );
            """
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
        )

    @staticmethod
    def _parse_date(value: date | str | None) -> date:
        if value is None:
            return date.today()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Date must use YYYY-MM-DD format.") from error

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
                    "INSERT INTO habits (name, period, description, created_at) VALUES (?, ?, ?, ?)",
                    (name, period, description.strip(), date.today().isoformat()),
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
    ) -> bool:
        habit = self.get_habit(name)
        completion_date = self._parse_date(completed_on)
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
                "INSERT OR IGNORE INTO completions (habit_id, completed_on) VALUES (?, ?)",
                (habit.id, completion_date.isoformat()),
            )
        return cursor.rowcount == 1

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
        with self.connection:
            self.connection.executemany(
                "INSERT INTO habits (name, period, description, created_at) VALUES (?, ?, ?, ?)",
                [(*habit, today.isoformat()) for habit in DEFAULT_HABITS],
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
                                    "INSERT INTO completions (habit_id, completed_on) VALUES (?, ?)",
                                    (habit.id, completion_day.isoformat()),
                                )
                    else:
                        for week in range(4):
                            completion_day = first_day + timedelta(days=week * 7 + habit_index % 5)
                            self.connection.execute(
                                "INSERT INTO completions (habit_id, completed_on) VALUES (?, ?)",
                                (habit.id, completion_day.isoformat()),
                            )
        return len(DEFAULT_HABITS)