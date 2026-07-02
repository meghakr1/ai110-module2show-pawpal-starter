"""Tests for PawPal+ scheduling behavior."""

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


@pytest.fixture
def scheduler():
    return Scheduler()


def test_mark_done_changes_completion_status():
    task = Task("Walk", duration_minutes=20)
    assert task.completed is False  # starts incomplete
    task.mark_done()
    assert task.completed is True  # calling mark_done() flips the status


def test_adding_task_increases_pet_task_count():
    pet = Pet("Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Feeding", duration_minutes=10))
    assert len(pet.tasks) == 1  # one task added
    pet.add_task(Task("Walk", duration_minutes=20))
    assert len(pet.tasks) == 2  # count grows with each task


def test_task_rejects_nonpositive_duration():
    with pytest.raises(ValueError):
        Task("Bad", duration_minutes=0)


def test_task_normalizes_priority_and_rejects_unknown():
    assert Task("Walk", 20, priority="HIGH").priority == "high"
    with pytest.raises(ValueError):
        Task("Walk", 20, priority="urgent")


def test_priority_rank_orders_high_above_low():
    assert Task("a", 5, "high").priority_rank() > Task("b", 5, "low").priority_rank()


def test_task_rejects_unknown_recurrence():
    with pytest.raises(ValueError):
        Task("Walk", 20, recurrence="hourly")


def test_weekly_task_is_due_only_on_its_weekday():
    grooming = Task("Grooming", 45, recurrence="weekly", weekday=5)  # Saturday
    assert grooming.is_due_on(5) is True
    assert grooming.is_due_on(2) is False
    # Daily tasks are due every day.
    assert Task("Walk", 20, recurrence="daily").is_due_on(2) is True


def test_build_plan_filters_out_tasks_not_due_that_day(scheduler):
    daily = Task("Walk", 20, "high", recurrence="daily")
    weekly = Task("Bath", 30, "high", recurrence="weekly", weekday=6)  # Sunday
    plan = scheduler.build_plan([daily, weekly], available_minutes=120, day=2)  # Wed

    titles = [item["task"].title for item in plan["items"]]
    assert "Walk" in titles
    assert "Bath" not in titles  # weekly-Sunday task not due on Wednesday


def test_find_conflicts_flags_over_budget(scheduler):
    tasks = [Task("Walk", 60, "high"), Task("Vet", 90, "high")]
    conflicts = scheduler.find_conflicts(tasks, available_minutes=100)
    assert any("Over budget" in c for c in conflicts)


def test_find_conflicts_flags_duplicates(scheduler):
    tasks = [Task("Feeding", 10, "high"), Task("feeding", 10, "high")]
    conflicts = scheduler.find_conflicts(tasks, available_minutes=120)
    assert any("Duplicate" in c for c in conflicts)


def test_find_conflicts_empty_when_all_good(scheduler):
    tasks = [Task("Walk", 20, "high", time="08:00"), Task("Feeding", 10, "high", time="09:00")]
    assert scheduler.find_conflicts(tasks, available_minutes=120) == []


def test_find_conflicts_flags_same_time_slot(scheduler):
    tasks = [
        Task("Morning walk", 30, "high", time="08:00"),
        Task("Vet call", 15, "medium", time="08:00"),  # same time slot
        Task("Lunch", 10, "low", time="12:00"),
    ]
    conflicts = scheduler.find_conflicts(tasks, available_minutes=300)
    time_conflicts = [c for c in conflicts if "Time conflict at 08:00" in c]
    assert len(time_conflicts) == 1
    assert "Morning walk" in time_conflicts[0]
    assert "Vet call" in time_conflicts[0]


def test_find_conflicts_ignores_untimed_tasks(scheduler):
    tasks = [Task("A", 10), Task("B", 10)]  # no time set on either
    assert not any("Time conflict" in c for c in scheduler.find_conflicts(tasks, 120))


def test_task_normalizes_and_validates_time():
    assert Task("Walk", 20, time="8:5").time == "08:05"  # zero-padded
    with pytest.raises(ValueError):
        Task("Walk", 20, time="25:00")


def test_sort_by_time_orders_chronologically(scheduler):
    tasks = [
        Task("Evening", 10, time="18:00"),
        Task("Morning", 10, time="08:00"),
        Task("Noon", 10, time="12:30"),
    ]
    ordered = [t.title for t in scheduler.sort_by_time(tasks)]
    assert ordered == ["Morning", "Noon", "Evening"]


def test_sort_by_time_sends_untimed_tasks_last(scheduler):
    tasks = [Task("Untimed", 10), Task("Timed", 10, time="09:00")]
    ordered = [t.title for t in scheduler.sort_by_time(tasks)]
    assert ordered == ["Timed", "Untimed"]


def test_filter_by_status_splits_done_and_pending(scheduler):
    done = Task("Done", 10)
    done.mark_done()
    pending = Task("Pending", 10)
    tasks = [done, pending]

    assert scheduler.filter_by_status(tasks, completed=False) == [pending]
    assert scheduler.filter_by_status(tasks, completed=True) == [done]


def test_next_occurrence_for_daily_is_fresh_copy():
    task = Task("Walk", 30, "high", recurrence="daily", time="08:00")
    task.mark_done()
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.completed is False       # the new one is not done
    assert nxt.title == "Walk"          # attributes preserved
    assert nxt.time == "08:00"
    assert nxt is not task              # a distinct instance


def test_next_occurrence_for_weekly_preserves_weekday():
    task = Task("Bath", 45, recurrence="weekly", weekday=6)
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.recurrence == "weekly"
    assert nxt.weekday == 6


def test_next_occurrence_for_one_off_is_none():
    task = Task("Vet visit", 60, recurrence="none")
    assert task.next_occurrence() is None


def test_complete_task_auto_adds_next_occurrence_for_recurring():
    pet = Pet("Mochi", "dog")
    walk = Task("Walk", 30, recurrence="daily")
    pet.add_task(walk)
    assert len(pet.tasks) == 1

    upcoming = pet.complete_task(walk)

    assert walk.completed is True           # original marked done
    assert upcoming in pet.tasks            # next occurrence auto-added
    assert upcoming.completed is False
    assert len(pet.tasks) == 2


def test_complete_task_does_not_recur_for_one_off():
    pet = Pet("Mochi", "dog")
    vet = Task("Vet visit", 60, recurrence="none")
    pet.add_task(vet)

    upcoming = pet.complete_task(vet)

    assert upcoming is None
    assert vet.completed is True
    assert len(pet.tasks) == 1              # no new task added


def test_tasks_for_pet_returns_only_that_pets_tasks():
    owner = Owner("Jordan")
    dog = Pet("Mochi", "dog")
    dog.add_task(Task("Walk", 20))
    cat = Pet("Simba", "cat")
    cat.add_task(Task("Litter", 5))
    owner.add_pet(dog)
    owner.add_pet(cat)

    titles = [t.title for t in owner.tasks_for_pet("mochi")]  # case-insensitive
    assert titles == ["Walk"]


def test_sort_orders_by_priority_then_duration(scheduler):
    low = Task("Enrichment", 10, "low")
    high_long = Task("Long walk", 45, "high")
    high_short = Task("Meds", 5, "high")

    ordered = scheduler.sort_tasks([low, high_long, high_short])

    assert ordered == [high_short, high_long, low]


def test_high_priority_scheduled_before_low_when_time_is_tight(scheduler):
    walk = Task("Walk", 30, "high")
    play = Task("Play", 30, "low")
    plan = scheduler.build_plan([play, walk], available_minutes=30)

    assert [item["task"] for item in plan["items"]] == [walk]
    assert play in plan["skipped"]


def test_tasks_are_placed_back_to_back_without_overlap(scheduler):
    plan = scheduler.build_plan(
        [Task("A", 30, "high"), Task("B", 15, "high")],
        available_minutes=120,
        start_hour=8,
    )
    # Sorted by shorter-first on tie: B (15) at 08:00, then A (30) at 08:15.
    assert [(item["time"], item["task"].title) for item in plan["items"]] == [
        ("08:00", "B"),
        ("08:15", "A"),
    ]


def test_tasks_that_do_not_fit_are_skipped(scheduler):
    plan = scheduler.build_plan(
        [Task("Short", 20, "medium"), Task("Long", 90, "medium")],
        available_minutes=30,
    )
    assert [item["task"].title for item in plan["items"]] == ["Short"]
    assert [t.title for t in plan["skipped"]] == ["Long"]
    assert plan["total_minutes"] == 20


def test_empty_task_list_produces_empty_plan(scheduler):
    plan = scheduler.build_plan([], available_minutes=60)
    assert plan["items"] == []
    assert plan["skipped"] == []
    assert scheduler.explain(plan) == "Nothing scheduled."


def test_explain_includes_time_title_and_skipped_section(scheduler):
    plan = scheduler.build_plan(
        [Task("Walk", 30, "high"), Task("Spa", 90, "low")],
        available_minutes=45,
        start_hour=8,
    )
    text = scheduler.explain(plan)
    assert "08:00 — Walk" in text
    assert "Skipped" in text
    assert "Spa" in text


def test_build_plan_validates_start_hour(scheduler):
    with pytest.raises(ValueError):
        scheduler.build_plan([], available_minutes=60, start_hour=25)


def test_completed_tasks_are_not_scheduled(scheduler):
    done = Task("Fed already", 10, "high")
    done.mark_done()
    todo = Task("Walk", 20, "high")

    plan = scheduler.build_plan([done, todo], available_minutes=120)

    scheduled = [item["task"] for item in plan["items"]]
    assert todo in scheduled
    assert done not in scheduled
    assert done not in plan["skipped"]  # completed != skipped-for-time


def test_scheduler_retrieves_tasks_from_owner(scheduler):
    owner = Owner("Jordan")
    dog = Pet("Mochi", "dog")
    dog.add_task(Task("Walk", 30, "high"))
    cat = Pet("Biscuit", "cat")
    cat.add_task(Task("Litter", 5, "medium"))
    owner.add_pet(dog)
    owner.add_pet(cat)

    plan = scheduler.plan_for_owner(owner, available_minutes=120)

    titles = {item["task"].title for item in plan["items"]}
    assert titles == {"Walk", "Litter"}


def test_owners_with_same_name_are_distinct():
    a = Owner("Jordan")
    b = Owner("Jordan")
    assert a.owner_id != b.owner_id
    assert a != b


def test_owner_all_tasks_flattens_across_pets():
    owner = Owner("Jordan")
    dog = Pet("Mochi", "dog")
    dog.add_task(Task("Walk", 30))
    cat = Pet("Biscuit", "cat")
    cat.add_task(Task("Litter", 5))
    owner.add_pet(dog)
    owner.add_pet(cat)

    assert [t.title for t in owner.all_tasks()] == ["Walk", "Litter"]
