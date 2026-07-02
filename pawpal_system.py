"""PawPal+ logic layer.

All backend classes for the pet-care planner live here:

- :class:`Owner`, :class:`Pet`, :class:`Task` hold the state.
- :class:`Scheduler` reads tasks plus a day's time budget and produces a plan.

The Streamlit UI (app.py) and the tests import everything from this module.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field, replace


@dataclass
class Task:
    """A single care activity, e.g. a 30-minute high-priority morning walk."""

    # Priority is a simple string; the rank below lets the scheduler order tasks.
    _RANK = {"low": 1, "medium": 2, "high": 3}
    _RECURRENCES = {"daily", "weekly", "none"}

    title: str  # description of the activity
    duration_minutes: int  # how much time it takes
    priority: str = "medium"
    category: str = "general"
    recurrence: str = "daily"  # frequency: "daily", "weekly", or "none"
    weekday: int | None = None  # for weekly tasks: 0=Mon .. 6=Sun
    time: str | None = None  # optional preferred start time, "HH:MM"
    completed: bool = False  # completion status

    def __post_init__(self) -> None:
        """Validate the fields and normalize the priority/recurrence strings."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        self.priority = self.priority.strip().lower()
        if self.priority not in self._RANK:
            raise ValueError(f"priority must be one of {list(self._RANK)}")
        self.recurrence = self.recurrence.strip().lower()
        if self.recurrence not in self._RECURRENCES:
            raise ValueError(f"recurrence must be one of {list(self._RECURRENCES)}")
        if self.weekday is not None and not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be between 0 (Mon) and 6 (Sun)")
        if self.time is not None:
            self.time = self._normalize_time(self.time)

    @staticmethod
    def _normalize_time(value: str) -> str:
        """Validate an "HH:MM" string and return it zero-padded (e.g. "8:5"->"08:05")."""
        parts = value.strip().split(":")
        if len(parts) != 2 or not (parts[0].isdigit() and parts[1].isdigit()):
            raise ValueError(f"time must look like 'HH:MM', got {value!r}")
        hours, minutes = int(parts[0]), int(parts[1])
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"time out of range: {value!r}")
        return f"{hours:02d}:{minutes:02d}"

    def mark_done(self) -> None:
        """Mark this task as completed so the scheduler skips it."""
        self.completed = True

    def next_occurrence(self) -> "Task | None":
        """Return a fresh, incomplete copy for the next occurrence.

        Daily and weekly tasks recur, so a new (uncompleted) instance is returned
        with all other attributes preserved. One-off tasks ("none") do not recur,
        so ``None`` is returned.
        """
        if self.recurrence == "none":
            return None
        return replace(self, completed=False)

    def is_due_on(self, weekday: int) -> bool:
        """True if this task should appear on the given weekday (0=Mon..6=Sun)."""
        if self.recurrence == "weekly" and self.weekday is not None:
            return self.weekday == weekday
        return True  # daily tasks, one-offs, and undated weekly tasks always apply

    def priority_rank(self) -> int:
        """Numeric importance (higher = more important) used for sorting."""
        return self._RANK[self.priority]

    def fits_within(self, minutes: int) -> bool:
        """True if this task can be completed in the remaining time budget."""
        return self.duration_minutes <= minutes


@dataclass
class Pet:
    """The animal being cared for. Owns its list of tasks."""

    name: str
    species: str = "dog"
    breed: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def complete_task(self, task: Task) -> "Task | None":
        """Mark a task complete; if it recurs, auto-add its next occurrence.

        Returns the newly created next-occurrence task (or None for one-offs).
        """
        task.mark_done()
        upcoming = task.next_occurrence()
        if upcoming is not None:
            self.add_task(upcoming)
        return upcoming


@dataclass
class Owner:
    """The person using PawPal+, plus their scheduling preferences."""

    name: str
    day_start_hour: int = 8
    pets: list[Pet] = field(default_factory=list)
    # Unique identity so two owners with the same name are still distinct.
    owner_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's list of pets."""
        self.pets.append(pet)

    def all_tasks(self) -> list[Task]:
        """Flatten every pet's tasks into a single list for scheduling."""
        return [task for pet in self.pets for task in pet.tasks]

    def tasks_for_pet(self, pet_name: str) -> list[Task]:
        """Return the tasks belonging to the pet with the given name."""
        return [
            task
            for pet in self.pets
            if pet.name.lower() == pet_name.strip().lower()
            for task in pet.tasks
        ]


class Scheduler:
    """The scheduling engine.

    ``build_plan`` returns a plain dict::

        {
            "items":   [ {"time": "HH:MM", "task": Task, "reason": str}, ... ],
            "skipped": [ Task, ... ],
            "total_minutes": int,
        }

    Strategy, in order:

    1. Sort tasks by priority (high first), then shorter tasks first as a
       tie-breaker so the day fills with more quick wins.
    2. Walk the sorted list, placing each task back-to-back from the start hour,
       as long as it fits in the remaining budget.
    3. Any task that no longer fits is recorded as skipped (never overlapped).
    """

    def plan_for_owner(
        self,
        owner: "Owner",
        available_minutes: int,
        start_hour: int = 8,
        day: int | None = None,
    ) -> dict:
        """Retrieve every task across the owner's pets and build a plan.

        This is how the Scheduler "talks" to an Owner: it calls the owner's
        ``all_tasks()`` accessor rather than reaching into ``owner.pets[i].tasks``
        itself, so the Scheduler stays decoupled from how the Owner stores pets.
        """
        return self.build_plan(owner.all_tasks(), available_minutes, start_hour, day)

    def find_conflicts(self, tasks: list[Task], available_minutes: int) -> list[str]:
        """Detect basic scheduling conflicts before building a plan."""
        conflicts: list[str] = []
        active = self.filter_by_status(tasks, completed=False)

        # 1. Over-budget: the active tasks together need more time than available.
        needed = sum(t.duration_minutes for t in active)
        if needed > available_minutes:
            conflicts.append(
                f"Over budget: tasks need {needed} min but only "
                f"{available_minutes} min are available ({needed - available_minutes} min over)."
            )

        # 2. Duplicates: the same task title added more than once.
        counts = Counter(task.title.strip().lower() for task in active)
        for title, count in counts.items():
            if count > 1:
                conflicts.append(f"Duplicate task '{title}' appears {count} times.")

        # 3. Time clashes: two or more tasks want the same "HH:MM" start time.
        by_time: dict[str, list[str]] = {}
        for task in active:
            if task.time is not None:
                by_time.setdefault(task.time, []).append(task.title)
        for time in sorted(by_time):
            titles = by_time[time]
            if len(titles) > 1:
                conflicts.append(
                    f"Time conflict at {time}: {', '.join(titles)} "
                    f"are scheduled at the same time."
                )

        return conflicts

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """High priority first; break ties with shorter duration first."""
        return sorted(
            tasks,
            key=lambda t: (-t.priority_rank(), t.duration_minutes),
        )

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks chronologically by their "HH:MM" time attribute.

        Because times are zero-padded 24-hour strings, comparing them as plain
        strings already orders them chronologically ("08:15" < "09:00"). Tasks
        with no time set are sent to the end via the "99:99" fallback.
        """
        return sorted(tasks, key=lambda t: t.time or "99:99")

    def filter_by_status(self, tasks: list[Task], completed: bool = False) -> list[Task]:
        """Return only the tasks whose completion status matches ``completed``."""
        return [task for task in tasks if task.completed == completed]

    def build_plan(
        self,
        tasks: list[Task],
        available_minutes: int,
        start_hour: int = 8,
        day: int | None = None,
    ) -> dict:
        """Select and time-order tasks that fit within the time budget.

        Completed tasks are ignored. When ``day`` (a weekday 0=Mon..6=Sun) is
        given, tasks not due that day (e.g. weekly tasks on the wrong day) are
        filtered out too.
        """
        if available_minutes < 0:
            raise ValueError("available_minutes cannot be negative")
        if not 0 <= start_hour <= 23:
            raise ValueError("start_hour must be between 0 and 23")

        items: list[dict] = []
        skipped: list[Task] = []
        remaining = available_minutes
        cursor = start_hour * 60  # minutes since midnight

        active_tasks = [
            task
            for task in tasks
            if not task.completed and (day is None or task.is_due_on(day))
        ]
        for task in self.sort_tasks(active_tasks):
            if task.fits_within(remaining):
                items.append(
                    {
                        "time": self._format_time(cursor),
                        "task": task,
                        "reason": (
                            f"{task.priority} priority; fits in the remaining "
                            f"{remaining} min budget"
                        ),
                    }
                )
                cursor += task.duration_minutes
                remaining -= task.duration_minutes
            else:
                skipped.append(task)

        return {
            "items": items,
            "skipped": skipped,
            "total_minutes": available_minutes - remaining,
        }

    def explain(self, plan: dict) -> str:
        """Human-readable summary of a plan and the reasoning behind it."""
        lines: list[str] = []
        for item in plan["items"]:
            task = item["task"]
            lines.append(
                f"{item['time']} — {task.title} ({task.duration_minutes} min) "
                f"[priority: {task.priority}] — {item['reason']}"
            )
        if plan["skipped"]:
            lines.append("")
            lines.append("Skipped (not enough time):")
            for task in plan["skipped"]:
                lines.append(
                    f"  - {task.title} ({task.duration_minutes} min) "
                    f"[priority: {task.priority}]"
                )
        return "\n".join(lines) if lines else "Nothing scheduled."

    @staticmethod
    def _format_time(minutes_since_midnight: int) -> str:
        """Convert minutes-since-midnight into an "HH:MM" string."""
        minutes_since_midnight %= 24 * 60
        hours, minutes = divmod(minutes_since_midnight, 60)
        return f"{hours:02d}:{minutes:02d}"
