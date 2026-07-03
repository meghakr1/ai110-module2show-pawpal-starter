import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.markdown("Add your pets and their care tasks, set a time budget, and let PawPal+ build a schedule.")

# --- Session "vault": create the Owner ONCE and reuse it across reruns. ---
# Streamlit re-runs this whole script on every interaction, so if we created
# the Owner unconditionally it would be reborn empty each click. Storing it in
# st.session_state keeps the same Owner (and its pets/tasks) for the session.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
owner = st.session_state.owner
scheduler = Scheduler()  # stateless engine; cheap to create each run

WEEKDAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}

# Show a one-off success message that was set just before a st.rerun().
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

st.divider()

# --- Owner ---
st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)

st.divider()

# --- Add a pet ---
# Submitting this form calls Owner.add_pet(); the rerun then re-renders the list.
st.subheader("Pets")
with st.form("add_pet_form", clear_on_submit=True):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        new_pet_name = st.text_input("Pet name", value="Mochi")
    with col_b:
        new_species = st.selectbox("Species", ["dog", "cat", "other"])
    with col_c:
        new_breed = st.text_input("Breed", value="")
    if st.form_submit_button("Add pet"):
        if new_pet_name.strip():
            owner.add_pet(Pet(name=new_pet_name, species=new_species, breed=new_breed))
            st.success(f"Added {new_pet_name}.")
        else:
            st.warning("Please enter a pet name.")

if owner.pets:
    st.write("Current pets:")
    for pet in owner.pets:
        st.write(f"- **{pet.name}** ({pet.species}) — {len(pet.tasks)} task(s)")
else:
    st.info("No pets yet. Add one above.")

st.divider()

if not owner.pets:
    st.info("Add a pet before creating tasks and a schedule.")
    st.stop()

# --- Add a task to a pet ---
# Submitting this form calls Pet.add_task() on the chosen pet.
st.subheader("Add a Task")
with st.form("add_task_form", clear_on_submit=True):
    pet_index = st.selectbox(
        "Which pet?",
        options=list(range(len(owner.pets))),
        format_func=lambda i: owner.pets[i].name,
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    col4, col5 = st.columns(2)
    with col4:
        task_time = st.text_input("Time (HH:MM, optional)", value="")
    with col5:
        recurrence = st.selectbox("Recurrence", ["daily", "weekly", "none"])
    if st.form_submit_button("Add task"):
        try:
            new_task = Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                recurrence=recurrence,
                time=task_time.strip() or None,
            )
        except ValueError as exc:
            # Task validates its own fields — surface the message, don't crash.
            st.error(f"Couldn't add task: {exc}")
        else:
            owner.pets[pet_index].add_task(new_task)
            st.success(f"Added '{task_title}' to {owner.pets[pet_index].name}.")

st.divider()

# --- Task list: filter (pet / status) + sort by time, shown as a clean table ---
st.subheader("Tasks")
col_pf, col_sf = st.columns(2)
with col_pf:
    pet_filter = st.selectbox("Filter by pet", ["All pets"] + [p.name for p in owner.pets])
with col_sf:
    status_filter = st.selectbox("Show", ["All", "Pending", "Completed"])

# Build the filtered + time-sorted rows for a professional st.table, and collect
# the still-pending tasks for the "mark done" control below.
table_rows = []
pending = []  # list of (label, pet, task)
for pet in owner.pets:
    if pet_filter != "All pets" and pet.name != pet_filter:
        continue

    pet_tasks = scheduler.sort_by_time(pet.tasks)  # chronological
    if status_filter == "Pending":
        pet_tasks = scheduler.filter_by_status(pet_tasks, completed=False)
    elif status_filter == "Completed":
        pet_tasks = scheduler.filter_by_status(pet_tasks, completed=True)

    for task in pet_tasks:
        table_rows.append(
            {
                "Time": task.time or "—",
                "Pet": pet.name,
                "Task": task.title,
                "Min": task.duration_minutes,
                "Priority": task.priority.capitalize(),
                "Repeat": task.recurrence,
                "Status": "✅ Done" if task.completed else "⏳ Pending",
            }
        )
        if not task.completed:
            pending.append((f"{pet.name} · {task.time or '--:--'} · {task.title}", pet, task))

if table_rows:
    st.table(table_rows)
else:
    st.info("No tasks match the current filter.")

# Mark-done control kept separate from the table so the table stays clean.
if pending:
    col_md1, col_md2 = st.columns([4, 1])
    with col_md1:
        choice = st.selectbox(
            "Mark a task complete",
            options=list(range(len(pending))),
            format_func=lambda i: pending[i][0],
        )
    with col_md2:
        st.write("")  # vertical spacer to align the button with the selectbox
        if st.button("Mark done", use_container_width=True):
            _, chosen_pet, chosen_task = pending[choice]
            # Pet.complete_task() marks it done AND auto-adds the next occurrence
            # for daily/weekly tasks.
            upcoming = chosen_pet.complete_task(chosen_task)
            msg = f"Marked '{chosen_task.title}' done."
            if upcoming is not None:
                msg += f" Added the next {chosen_task.recurrence} occurrence."
            st.session_state.flash = msg
            st.rerun()

st.divider()

# --- Build schedule ---
st.subheader("Build Schedule")
col_time, col_start, col_day = st.columns(3)
with col_time:
    available = st.number_input(
        "Time available today (minutes)", min_value=0, max_value=1440, value=120
    )
with col_start:
    start_hour = st.number_input("Day starts at (hour)", min_value=0, max_value=23, value=8)
with col_day:
    day_label = st.selectbox("Plan for", ["Any day"] + list(WEEKDAYS))

# Scheduler.find_conflicts() — one consolidated, owner-friendly warning (never crashes).
conflicts = scheduler.find_conflicts(owner.all_tasks(), int(available))
if conflicts:
    bullet_list = "\n".join(f"- {c}" for c in conflicts)
    st.warning(
        "**Heads up — some tasks may clash:**\n\n"
        f"{bullet_list}\n\n"
        "You can still generate a schedule — PawPal+ places tasks back-to-back "
        "to avoid overlaps, but you may want to adjust the times above."
    )

if st.button("Generate schedule", type="primary"):
    day = WEEKDAYS.get(day_label)  # None for "Any day" -> no recurrence filtering
    plan = scheduler.plan_for_owner(owner, int(available), int(start_hour), day)

    st.markdown(f"### Daily plan for {owner.name}")
    if plan["items"]:
        st.success(
            f"Scheduled {len(plan['items'])} task(s) — "
            f"{plan['total_minutes']} of {int(available)} min used."
        )
        st.table(
            [
                {
                    "Time": item["time"],
                    "Task": item["task"].title,
                    "Duration (min)": item["task"].duration_minutes,
                    "Priority": item["task"].priority.capitalize(),
                }
                for item in plan["items"]
            ]
        )
    else:
        st.info("Nothing fit within the available time.")

    if plan["skipped"]:
        st.warning(
            "Skipped (not enough time): "
            + ", ".join(f"{t.title} ({t.duration_minutes} min)" for t in plan["skipped"])
        )

    with st.expander("Why this plan?"):
        st.text(scheduler.explain(plan))
