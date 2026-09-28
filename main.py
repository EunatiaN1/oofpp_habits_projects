"""Pomodoro habit time tracker.

This program helps users structure study and work sessions using the
Pomodoro technique. Each work session lasts 25 minutes, followed by a short
or long break depending on the cycle. The tracker also totals daily focus
minutes to support habit tracking and productivity review.
"""

import time

WORK_DURATION = 25 * 60
SHORT_BREAK_DURATION = 5 * 60
LONG_BREAK_DURATION = 15 * 60


def format_time(total_seconds):
    """Return a duration in MM:SS format."""
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def get_break_type(session_number):
    """Return the correct break type for the session number."""
    return "long" if session_number % 4 == 0 else "short"


def build_session_plan(session_count, work_duration, short_break_duration, long_break_duration):
    """Build an ordered list of work and break activities for the day."""
    plan = []
    for session_number in range(1, session_count + 1):
        plan.append(("work", work_duration))
        if session_number % 4 == 0:
            plan.append(("long_break", long_break_duration))
        else:
            plan.append(("short_break", short_break_duration))
    return plan


def countdown(duration, label):
    """Display a running countdown for a work or break block."""
    remaining = duration
    while remaining > 0:
        print(f"{label}: {format_time(remaining)}", end="\r")
        time.sleep(1)
        remaining -= 1

    print(f"{label}: 00:00")


def run_tracker(session_count):
    """Run the Pomodoro workflow and print a completion summary."""
    session_plan = build_session_plan(
        session_count,
        WORK_DURATION,
        SHORT_BREAK_DURATION,
        LONG_BREAK_DURATION,
    )

    total_focus_minutes = 0
    print("\nWelcome to the Pomodoro Habit Time Tracker!")
    print("Use this timer to stay focused and maintain a healthy study rhythm.\n")

    focus_session = 0
    for activity, duration in session_plan:
        if activity == "work":
            focus_session += 1
            total_focus_minutes += duration // 60
            print(f"\nSession {focus_session} - Focus Time")
            countdown(duration, "Focus")
        elif activity == "long_break":
            print("\nTime for a long break!")
            countdown(duration, "Break")
        else:
            print("\nTime for a short break!")
            countdown(duration, "Break")

    print("\nCongratulations! You completed all Pomodoro sessions for today.")
    print(f"Total focused time: {total_focus_minutes} minutes")
    print("Daily habit status: productive and consistent.")


def main():
    """Collect the number of sessions and start the timer."""
    try:
        sessions = int(input("Enter the number of Pomodoro sessions you want to complete: "))
        if sessions <= 0:
            raise ValueError
    except ValueError:
        print("Please enter a valid positive number of sessions.")
        return

    run_tracker(sessions)


if __name__ == "__main__":
    main()

