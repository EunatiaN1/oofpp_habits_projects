# Pomodoro Habit Time Tracker

A command-line Pomodoro timer and persistent habit tracker. Focus in 25-minute sessions with scheduled breaks, then manage daily and weekly habits, record completions, and review progress analytics.

## Requirements
- Python 3.7 or later
- `pytest` to run the test suite

## Features
- 25-minute focus sessions
- 5-minute short breaks
- 15-minute long breaks after every fourth session
- Daily total of focused minutes
- Daily and weekly habit tracking with SQLite persistence
- Timezone-aware habit creation and completion timestamps
- Five predefined habits and four weeks of sample completion history
- Timezone-aware completion timestamps, with date-based daily and weekly rules
- Habit creation, deletion, check-offs, completion history, rates, and streak analytics

## Files
- `main.py` - main Pomodoro application
- `habit_tracker.py` - `Habit` model, SQLite storage, and predefined habits
- `habit_analytics.py` - daily and weekly completion-rate and streak calculations
- `habit_cli.py` - command-line interface for habit tracking
- `test_pomodoro.py` - validation tests for timer logic
- `test_habits.py` - tests for habit storage, analytics, and CLI behavior
- `preview.html` - standalone browser preview of the timer interface

## Run
```bash
python3 main.py
```

## Habit Tracking

Initialize the default habits and four weeks of example data:

```bash
python3 habit_cli.py init
```

Running `python3 habit_cli.py` without a command lists existing habits and suggests initialization if the database is empty.

The database is stored in `habits.sqlite3` in the project directory. To create the five predefined habits without sample completions, run `python3 habit_cli.py init --no-sample-data` instead.

```bash
python3 habit_cli.py list
python3 habit_cli.py complete "Read 20 pages"
python3 habit_cli.py complete "Read 20 pages" --at "2026-11-03T18:30:00+02:00"
python3 habit_cli.py history
python3 habit_cli.py history "Read 20 pages"
python3 habit_cli.py analyze
python3 habit_cli.py create "Stretch" --period daily
python3 habit_cli.py create "Plan meals" --period weekly
python3 habit_cli.py delete "Stretch"
```

Completions are stored with an ISO 8601 timestamp and timezone offset. Omitting `--at` records the current local time. Supply `--at` to record a specific timestamp; it must include a timezone. The `--date YYYY-MM-DD` option remains available for backdated entries and uses the current local clock time on that date. `history` displays saved completion dates and times.

Daily habits can be completed once per calendar date. The `list` command includes each habit's creation timestamp. Weekly habits use Monday-to-Sunday calendar weeks and can be completed once per week. Analytics default to a trailing 28-day window; set `--days` to change the window or pass a habit name to analyze only that habit. Use `--db PATH` before the command to select another SQLite database.

Existing databases are upgraded automatically when opened. Legacy habits and date-only completion records keep their dates and are shown with an unavailable time rather than having a time fabricated. Newly created habits and newly recorded or seeded completions include timestamps.

## Test

Install the test dependency in the Python environment you use for this project:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run the test modules through pytest (rather than running `test_habits.py` directly):

```bash
python3 -m pytest -q
```

## Assignment tasks

### 1.1.1 Problem/Need
The project addresses the need for a practical productivity tool that helps users manage study and work time by breaking it into focused intervals and rest periods. This reduces distraction and improves concentration during long tasks.

### 1.1.2 Design/Plan
The timer uses 25-minute work sessions, 5-minute short breaks, and a 15-minute break after every fourth session. Habit definitions and completion dates are stored in SQLite. Daily and weekly analytics are implemented as pure functions, separate from the storage and command-line layers.

### 1.1.3 Finalization
The finalization review confirmed that the project documentation describes the delivered timer, SQLite habit tracker, CLI, and analytics. The full test suite validates timer planning, habit persistence, seeded history, weekly completion rules, analytics, and CLI commands. The final submission abstract and ZIP archive are prepared as separate deliverables.
