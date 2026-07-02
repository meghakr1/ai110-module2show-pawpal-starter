# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Running the terminal demo (`python main.py`) produces the following schedule. It
creates an owner with two pets, adds several tasks, and lets the `Scheduler` plan
the day within a 90-minute budget:

```
===============================================
  Today's Schedule for Jordan
  Pets: Mochi, Simba   |   Time budget: 90 min
===============================================
  TIME    TASK                MINS  PRIORITY
  ------  -----------------  -----  --------
  08:00   Litter box             5  HIGH
  08:05   Feeding               10  HIGH
  08:15   Morning walk          30  HIGH
  08:45   Grooming              45  MEDIUM

  Skipped (not enough time):
    - Enrichment puzzle (20 min, low)
-----------------------------------------------
  Scheduled 90 of 90 min   |   4 task(s) planned, 1 skipped
```

This demonstrates the scheduler ordering tasks by priority (with shorter tasks
first on ties), packing the day within the time budget, and skipping lower-priority
tasks once time runs out.

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

Beyond building a basic plan, PawPal+ adds four "smart" behaviors. Each is a small,
tested algorithm in `pawpal_system.py`.

### Sorting

- **`Scheduler.sort_tasks(tasks)`** — the ordering used when building a plan. Sorts by
  priority (high → low), then by shorter duration first as a tie-breaker, so a tight day
  fills up with quick wins instead of one long task crowding others out.
  Key: `lambda t: (-t.priority_rank(), t.duration_minutes)`.
- **`Scheduler.sort_by_time(tasks)`** — orders tasks chronologically by their `HH:MM`
  `time` attribute using `sorted()` with a lambda key (`t.time or "99:99"`). Because times
  are zero-padded 24-hour strings, plain string comparison is already chronological; untimed
  tasks fall to the end.

### Filtering

- **`Scheduler.filter_by_status(tasks, completed=False)`** — returns only the tasks whose
  completion status matches, so you can list pending vs. done tasks separately.
- **`Owner.tasks_for_pet(pet_name)`** — returns just the tasks belonging to a named pet
  (case-insensitive), for filtering the view by pet.
- **`Scheduler.build_plan(...)`** also filters implicitly: it drops completed tasks and any
  task that no longer fits the remaining time budget (those go under `skipped`).

### Conflict detection

- **`Scheduler.find_conflicts(tasks, available_minutes)`** — a lightweight check that returns
  a list of human-readable **warning strings** (never raises). It flags:
  1. **Over-budget** — the active tasks together need more time than is available.
  2. **Duplicates** — the same task title added more than once (via `collections.Counter`).
  3. **Time clashes** — two or more tasks share the same `HH:MM` start time, across any pet.
- **`Scheduler.build_plan(...)`** avoids overlaps in its own output by placing tasks
  back-to-back from the start hour.

### Recurring tasks

- **`Task.recurrence`** (`"daily"` / `"weekly"` / `"none"`) plus an optional **`Task.weekday`**
  (0=Mon..6=Sun) describe how often a task repeats.
- **`Task.is_due_on(weekday)`** answers whether a task applies on a given day; passing
  **`Scheduler.build_plan(..., day=<weekday>)`** filters out tasks not due that day.
- **`Task.next_occurrence()`** returns a fresh, incomplete copy of a recurring task (or `None`
  for one-offs), and **`Pet.complete_task(task)`** uses it to auto-add the next occurrence
  when a recurring task is marked complete.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
