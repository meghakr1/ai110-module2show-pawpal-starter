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
