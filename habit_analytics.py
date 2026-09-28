"""Pure analytics for daily and weekly habit completion history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from habit_tracker import Habit, HabitPeriod


@dataclass(frozen=True)
class HabitAnalytics:
    habit_name: str
    period: HabitPeriod
    window_start: date
    window_end: date
    completed_periods: int
    total_periods: int
    completion_rate: float
    current_streak: int
    longest_streak: int


def period_start(day: date, period: HabitPeriod) -> date:
    """Return the calendar date anchoring the daily or Monday-based weekly period."""
    if period == "daily":
        return day
    if period == "weekly":
        return day - timedelta(days=day.weekday())
    raise ValueError("Habit period must be 'daily' or 'weekly'.")


def analyze_habit(
    habit: Habit,
    completion_dates: Iterable[date],
    *,
    today: date | None = None,
    days: int = 28,
) -> HabitAnalytics:
    """Summarize completion rate and streaks in a trailing date window.

    Weekly habits use Monday-through-Sunday calendar weeks. A partial week at
    either edge of the requested date window counts as one weekly period.
    """
    if days < 1:
        raise ValueError("Analysis window must contain at least one day.")

    today = today or date.today()
    window_start = today - timedelta(days=days - 1)
    first_period = period_start(window_start, habit.period)
    last_period = period_start(today, habit.period)
    step = timedelta(days=1 if habit.period == "daily" else 7)

    periods: list[date] = []
    current_period = first_period
    while current_period <= last_period:
        periods.append(current_period)
        current_period += step

    completed = {
        period_start(completed_on, habit.period)
        for completed_on in completion_dates
    }
    completed_count = sum(period in completed for period in periods)

    current_streak = 0
    for period in reversed(periods):
        if period not in completed:
            break
        current_streak += 1

    longest_streak = 0
    running_streak = 0
    for period in periods:
        if period in completed:
            running_streak += 1
            longest_streak = max(longest_streak, running_streak)
        else:
            running_streak = 0

    return HabitAnalytics(
        habit_name=habit.name,
        period=habit.period,
        window_start=window_start,
        window_end=today,
        completed_periods=completed_count,
        total_periods=len(periods),
        completion_rate=completed_count / len(periods) * 100,
        current_streak=current_streak,
        longest_streak=longest_streak,
    )