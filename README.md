# Pomodoro Habit Time Tracker

A command-line focus timer that guides you through 25-minute work sessions, 5-minute short breaks, and a 15-minute break after every fourth session. Choose how many sessions to complete, follow the live countdown, and review your total focused time when you're done.

## Features
- 25-minute focus sessions
- 5-minute short breaks
- 15-minute long breaks after every fourth session
- Daily total of focused minutes
- Simple user input and timer flow

## Files
- `main.py` - main Pomodoro application
- `test_pomodoro.py` - validation tests for timer logic
- `preview.html` - standalone browser preview of the timer interface

## Run
```bash
python3 main.py
```

## Test
```bash
python3 -m pytest -q
```

## Assignment tasks

### 1.1.1 Problem/Need
The project addresses the need for a practical productivity tool that helps users manage study and work time by breaking it into focused intervals and rest periods. This reduces distraction and improves concentration during long tasks.

### 1.1.2 Design/Plan
The design uses the standard Pomodoro cycle: work for 25 minutes, short break for 5 minutes, and long break for 15 minutes after every fourth session. The tracker is organized into reusable functions so it is easy to understand, maintain, and expand.

### 1.1.3 Implementation and Testing
The tracker was implemented in Python and tested to verify time formatting, break selection, and session planning. The test suite confirms the logic works correctly before the program is used.
