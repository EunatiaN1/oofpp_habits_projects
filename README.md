# Pomodoro Habit Time Tracker

A command-line Pomodoro timer and persistent habit tracker. Focus in 25-minute sessions with scheduled breaks, then manage daily and weekly habits, record completions, and review progress analytics.

## Features
- 25-minute focus sessions
- 5-minute short breaks
- 15-minute long breaks after every fourth session
- Daily total of focused minutes
- Daily and weekly habit tracking with SQLite persistence
- Five predefined habits and four weeks of sample completion history
- Habit creation, deletion, check-offs, completion rates, and streak analytics

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

The database is stored in `habits.sqlite3` in the project directory. To create the five predefined habits without sample completions, run `python3 habit_cli.py init --no-sample-data` instead.

```bash
python3 habit_cli.py list
python3 habit_cli.py complete "Read 20 pages"
python3 habit_cli.py analyze
python3 habit_cli.py create "Stretch" --period daily
python3 habit_cli.py create "Plan meals" --period weekly
python3 habit_cli.py delete "Stretch"
```

Weekly habits use Monday-to-Sunday calendar weeks and can be completed once per week. Analytics default to a trailing 28-day window; set `--days` to change the window or pass a habit name to analyze only that habit. Use `--db PATH` before the command to select another SQLite database.

## Test
```bash
python3 -m pytest -q
```

## Assignment tasks

### 1.1.1 Problem/Need
The project addresses the need for a practical productivity tool that helps users manage study and work time by breaking it into focused intervals and rest periods. This reduces distraction and improves concentration during long tasks.

### 1.1.2 Design/Plan
The timer uses 25-minute work sessions, 5-minute short breaks, and a 15-minute break after every fourth session. Habit definitions and completion dates are stored in SQLite. Daily and weekly analytics are implemented as pure functions, separate from the storage and command-line layers.

### 1.1.3 Implementation and Testing
The project includes the Pomodoro timer and a habit-tracking CLI for creating, deleting, and completing habits. Unit tests cover timer planning, habit persistence, seeded history, weekly completion rules, analytics, and CLI commands.
