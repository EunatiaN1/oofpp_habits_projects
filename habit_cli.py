"""Command-line interface for creating and reviewing tracked habits."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from habit_analytics import analyze_habit
from habit_tracker import HabitStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and track daily or weekly habits.")
    parser.add_argument(
        "--db",
        default=os.environ.get("HABIT_DB", "habits.sqlite3"),
        help="SQLite database path (default: habits.sqlite3 or HABIT_DB)",
    )
    commands = parser.add_subparsers(dest="command")

    initialize = commands.add_parser("init", help="Add five predefined habits and sample history")
    initialize.add_argument(
        "--no-sample-data",
        action="store_true",
        help="Create the predefined habits without four weeks of sample completions",
    )

    commands.add_parser("list", help="List all habits")

    create = commands.add_parser("create", help="Create a habit")
    create.add_argument("name", help="Habit name")
    create.add_argument("--period", choices=("daily", "weekly"), required=True)
    create.add_argument("--description", default="", help="Optional habit description")

    delete = commands.add_parser("delete", help="Delete a habit and its completion history")
    delete.add_argument("name", help="Habit name")

    complete = commands.add_parser("complete", help="Record a habit completion")
    complete.add_argument("name", help="Habit name")
    complete.add_argument("--date", help="Completion date in YYYY-MM-DD format (default: today)")

    analyze = commands.add_parser(
        "analyze",
        aliases=["analyse"],
        help="Analyze one habit or all habits",
    )
    analyze.add_argument("name", nargs="?", help="Habit name (omit to analyze all habits)")
    analyze.add_argument("--days", type=int, default=28, help="Trailing analysis window (default: 28)")

    return parser


def _print_analysis(store: HabitStore, name: str | None, days: int) -> None:
    habits = [store.get_habit(name)] if name else store.list_habits()
    if not habits:
        print("No habits found. Run 'python3 habit_cli.py init' to add the predefined habits.")
        return

    for habit in habits:
        stats = analyze_habit(
            habit,
            store.completion_dates(habit.name),
            days=days,
        )
        print(
            f"{stats.habit_name} ({stats.period}): "
            f"{stats.completion_rate:.0f}% "
            f"({stats.completed_periods}/{stats.total_periods} periods), "
            f"current streak {stats.current_streak}, "
            f"best streak {stats.longest_streak}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with HabitStore(args.db) as store:
            if args.command == "init":
                seeded = store.seed_defaults(include_sample_data=not args.no_sample_data)
                if seeded:
                    suffix = "without sample completions" if args.no_sample_data else "with four weeks of sample history"
                    print(f"Initialized {seeded} predefined habits {suffix}.")
                else:
                    print("Habits already exist; defaults were not added.")
            elif args.command in (None, "list"):
                habits = store.list_habits()
                if not habits:
                    print("No habits found. Run 'python3 habit_cli.py init' to add the predefined habits.")
                for habit in habits:
                    description = f" - {habit.description}" if habit.description else ""
                    print(f"{habit.name} [{habit.period}]{description}")
            elif args.command == "create":
                habit = store.create_habit(args.name, args.period, args.description)
                print(f"Created {habit.name} ({habit.period}).")
            elif args.command == "delete":
                store.delete_habit(args.name)
                print(f"Deleted {args.name} and its completion history.")
            elif args.command == "complete":
                recorded = store.record_completion(args.name, args.date)
                if recorded:
                    print(f"Recorded completion for {args.name}.")
                else:
                    print(f"{args.name} is already complete for that date or week.")
            elif args.command in ("analyze", "analyse"):
                if args.days < 1:
                    raise ValueError("Analysis window must be at least one day.")
                _print_analysis(store, args.name, args.days)
    except (KeyError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())