"""PawPal+ logic layer.

All backend classes for the pet-care planner live here:

- :class:`Owner`, :class:`Pet`, :class:`Task` hold the state.
- :class:`Scheduler` reads tasks plus a day's time budget and produces a plan.

The Streamlit UI (app.py) and the tests import everything from this module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Task:
    """A single care activity, e.g. a 30-minute high-priority morning walk."""

    # Priority is a simple string; the rank below lets the scheduler order tasks.
    _RANK = {"low": 1, "medium": 2, "high": 3}

    title: str
    duration_minutes: int
    priority: str = "medium"
    category: str = "general"
    recurrence: str = "daily"  # "daily", "weekly", or "none"

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        self.priority = self.priority.strip().lower()
        if self.priority not in self._RANK:
            raise ValueError(f"priority must be one of {list(self._RANK)}")

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
        self.tasks.append(task)


@dataclass
class Owner:
    """The person using PawPal+, plus their scheduling preferences."""

    name: str
    day_start_hour: int = 8
    pets: list[Pet] = field(default_factory=list)
    # Unique identity so two owners with the same name are still distinct.
    owner_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def all_tasks(self) -> list[Task]:
        """Flatten every pet's tasks into a single list for scheduling."""
        return [task for pet in self.pets for task in pet.tasks]


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

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """High priority first; break ties with shorter duration first."""
        return sorted(
            tasks,
            key=lambda t: (-t.priority_rank(), t.duration_minutes),
        )

    def build_plan(
        self, tasks: list[Task], available_minutes: int, start_hour: int = 8
    ) -> dict:
        """Select and time-order tasks that fit within the time budget."""
        if available_minutes < 0:
            raise ValueError("available_minutes cannot be negative")
        if not 0 <= start_hour <= 23:
            raise ValueError("start_hour must be between 0 and 23")

        items: list[dict] = []
        skipped: list[Task] = []
        remaining = available_minutes
        cursor = start_hour * 60  # minutes since midnight

        for task in self.sort_tasks(tasks):
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
        minutes_since_midnight %= 24 * 60
        hours, minutes = divmod(minutes_since_midnight, 60)
        return f"{hours:02d}:{minutes:02d}"
