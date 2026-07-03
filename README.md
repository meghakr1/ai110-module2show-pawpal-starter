# 🐾 PawPal+

**PawPal+** is a pet-care planning assistant. It helps a busy pet owner stay consistent with
their pets' care by turning a list of tasks into a prioritized daily schedule — and explaining
why it chose that plan.

It ships with both a **Streamlit web app** and a **command-line demo**, backed by a small,
fully tested Python logic layer.

---

## Overview

Give PawPal+ your pets and their care tasks (walks, feeding, meds, grooming, enrichment…),
tell it how much time you have today, and it will:

- **Prioritize** — schedule high-priority tasks first, using shorter tasks as a tie-breaker so
  a tight day fills with quick wins.
- **Fit the budget** — pack tasks back-to-back from your start hour and skip what doesn't fit.
- **Warn about clashes** — flag over-budget days, duplicate tasks, and time conflicts.
- **Handle recurring tasks** — daily / weekly tasks regenerate automatically when completed.
- **Explain itself** — every plan comes with a plain-language rationale.

---

## Features

| Area | What it does |
|------|--------------|
| Owners & pets | One owner manages multiple pets; each pet owns its own tasks. |
| Tasks | Title, duration, priority, category, recurrence, optional `HH:MM` time, completion status. |
| Sorting | By priority (then duration), or chronologically by time. |
| Filtering | By completion status, or by pet. |
| Conflict detection | Over-budget, duplicate titles, and same-time clashes — as friendly warnings, never crashes. |
| Recurring tasks | `daily` / `weekly` / one-off; completing a recurring task auto-creates its next occurrence. |
| Scheduling | Builds a time-ordered, non-overlapping plan within a time budget, with skipped-task reporting. |

See [**Scheduling features**](#-scheduling-features) below for the exact methods behind each.

---

## Architecture

The logic layer ([`pawpal_system.py`](pawpal_system.py)) is built from four classes:

| Class | Responsibility |
|-------|----------------|
| `Owner` | Holds owner info + preferences; manages pets; aggregates tasks across pets. |
| `Pet` | Stores pet details and its list of tasks; completes tasks (with recurrence). |
| `Task` | A single care activity; knows its priority rank, due-day, and next occurrence. |
| `Scheduler` | Stateless engine — sorts, filters, detects conflicts, and builds/explains plans. |

Data and behavior are deliberately separated: `Owner`/`Pet`/`Task` are dataclasses that hold
state, while `Scheduler` contains the algorithms. `build_plan()` returns a plain dictionary
(no wrapper classes). The full class diagram lives in [`diagrams/uml.mmd`](diagrams/uml.mmd)
(rendered: [`diagrams/uml.png`](diagrams/uml.png)).

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Requires Python 3.10+ (uses `X | None` type hints).

---

## Usage

### Web app

```bash
streamlit run app.py
```

Then follow the [Demo Walkthrough](#-demo-walkthrough) below. The app persists your owner,
pets, and tasks in Streamlit session state, so they survive across interactions.

### Terminal demo

```bash
python main.py
```

Builds a sample owner, pets, and tasks, then prints the sorting, filtering, conflict check,
and generated schedule to the terminal (see [Sample Output](#-sample-output)).

### As a library

```python
from pawpal_system import Owner, Pet, Scheduler, Task

owner = Owner("Jordan")
dog = Pet("Mochi", "dog")
dog.add_task(Task("Morning walk", 30, "high", time="08:00"))
owner.add_pet(dog)

plan = Scheduler().plan_for_owner(owner, available_minutes=90)
print(Scheduler().explain(plan))
```

---

## 🖥️ Sample Output

Running the terminal demo (`python main.py`) produces a schedule like this. It creates an owner
with two pets, adds several tasks, and lets the `Scheduler` plan the day within a 90-minute budget:

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

This demonstrates the scheduler ordering tasks by priority (with shorter tasks first on ties),
packing the day within the time budget, and skipping lower-priority tasks once time runs out.

---

## 📐 Scheduling features

Each "smart" behavior is a small, tested algorithm in [`pawpal_system.py`](pawpal_system.py).

### Sorting

- **`Scheduler.sort_tasks(tasks)`** — the ordering used when building a plan. Sorts by
  priority (high → low), then by shorter duration first as a tie-breaker.
  Key: `lambda t: (-t.priority_rank(), t.duration_minutes)`.
- **`Scheduler.sort_by_time(tasks)`** — orders tasks chronologically by their `HH:MM`
  `time` attribute using `sorted()` with a lambda key (`t.time or "99:99"`). Because times
  are zero-padded 24-hour strings, plain string comparison is already chronological; untimed
  tasks fall to the end.

### Filtering

- **`Scheduler.filter_by_status(tasks, completed=False)`** — returns only the tasks whose
  completion status matches, so you can list pending vs. done tasks separately.
- **`Owner.tasks_for_pet(pet_name)`** — returns just the tasks belonging to a named pet
  (case-insensitive).
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

---

## 🧪 Testing

```bash
pytest            # run the full suite
pytest --cov      # run with coverage
```

Current status:

```
collected 34 items

tests/test_pawpal.py ..................................                  [100%]

============================== 34 passed in 0.02s ==============================
```

The suite in [`tests/test_pawpal.py`](tests/test_pawpal.py) covers task validation, priority
ranking, sorting (by priority and by time), filtering, conflict detection, recurring-task
generation, and the end-to-end plan output.

---

## 🚶 Demo Walkthrough

Launch the app with `streamlit run app.py` (opens at http://localhost:8501).

### Main UI features & actions

The single-page app is organized top to bottom, and everything persists in your session:

- **Owner** — set the owner's name.
- **Pets** — add pets (name, species, breed) via the *Add pet* form; the list shows each pet
  with a live task count.
- **Add a Task** — pick a pet and enter a title, duration, priority (low/medium/high), an
  optional `HH:MM` start time, and a recurrence (`daily` / `weekly` / `none`). Invalid input
  (e.g. a time of `25:00`) is reported as an error rather than crashing.
- **Tasks** — a table of all tasks, sorted by time, with *Filter by pet* and
  *Show: All / Pending / Completed* controls. A *Mark a task complete* control lets you tick a
  task off.
- **Build Schedule** — set the available minutes, start hour, and (optionally) a weekday to plan
  for; a conflict warning appears here if relevant, and *Generate schedule* produces the plan
  plus a *Why this plan?* explanation.

### Example workflow

1. In **Owner**, keep or change the owner name (e.g. "Jordan").
2. In **Pets**, add **Mochi** (dog) and **Simba** (cat).
3. In **Add a Task**, add a few tasks — e.g. Mochi's *Morning walk* (30 min, high, `08:00`),
   *Lunch feeding* (10 min, medium, `12:30`), and Simba's *Litter box* (5 min, high, `07:30`).
4. Add a clashing task — Simba's *Vet phone call* (15 min, medium, also `08:00`).
5. In **Tasks**, watch the list appear **sorted by time** (07:30 → 08:00 → 12:30…); try the
   pet and status filters.
6. In **Build Schedule**, note the ⚠️ **conflict warning** about the two `08:00` tasks, set the
   time budget to `90` minutes, and click **Generate schedule** to see today's plan and its
   explanation.

### Key Scheduler behaviors shown

- **Priority sorting** — high-priority tasks are scheduled first; ties break toward shorter
  tasks (`Scheduler.sort_tasks`).
- **Chronological sorting** — the task list is ordered by `HH:MM` time (`Scheduler.sort_by_time`).
- **Filtering** — by completion status (`Scheduler.filter_by_status`) and by pet
  (`Owner.tasks_for_pet`).
- **Conflict warnings** — over-budget days, duplicate titles, and same-time clashes are flagged
  as friendly warnings (`Scheduler.find_conflicts`).
- **Budget packing & skipping** — tasks are placed back-to-back from the start hour; anything
  that doesn't fit is listed as skipped (`Scheduler.build_plan`).
- **Recurring tasks** — completing a daily/weekly task auto-creates its next occurrence
  (`Pet.complete_task` → `Task.next_occurrence`).

### Sample CLI output (`python main.py`)

The terminal demo exercises the same logic layer end to end — sorting, filtering, a conflict
check, and the final schedule:

```
=== Conflict check ===
  ⚠️  Time conflict at 08:00: Morning walk, Vet phone call are scheduled at the same time.

=== All tasks, sorted by time ===
  07:30  Litter box (5 min)
  08:00  Morning walk (30 min)
  08:00  Vet phone call (15 min)
  12:30  Lunch feeding (10 min)
  15:00  Grooming (45 min)
  18:00  Evening walk (30 min)

=== Pending tasks (5) ===
  07:30  Litter box
  08:00  Morning walk
  08:00  Vet phone call
  12:30  Lunch feeding
  18:00  Evening walk

=== Completed tasks (1) ===
  15:00  Grooming

=== Mochi's tasks ===
  08:00  Morning walk
  12:30  Lunch feeding
  18:00  Evening walk

==============================================
  Today's Schedule for Jordan
  Pets: Mochi, Simba   |   Time budget: 90 min
==============================================
  TIME    TASK             MINS  PRIORITY
  ------  --------------  -----  --------
  08:00   Litter box          5  HIGH
  08:05   Evening walk       30  HIGH
  08:35   Morning walk       30  HIGH
  09:05   Lunch feeding      10  MEDIUM
  09:15   Vet phone call     15  MEDIUM
----------------------------------------------
  Scheduled 90 of 90 min   |   5 task(s) planned, 0 skipped
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

---

## Project structure

```
pawpal_system.py       Logic layer — Owner, Pet, Task, Scheduler (all backend classes)
app.py                 Streamlit web UI
main.py                Terminal demo / testing ground
tests/test_pawpal.py   Pytest suite (34 tests)
diagrams/uml.mmd       UML class diagram (source) + rendered uml.png / uml.svg
requirements.txt       Dependencies (streamlit, pytest)
```
