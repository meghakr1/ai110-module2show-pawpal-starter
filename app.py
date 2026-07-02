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

# --- Add a task to a pet ---
# Submitting this form calls Pet.add_task() on the chosen pet.
if owner.pets:
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
        if st.form_submit_button("Add task"):
            owner.pets[pet_index].add_task(
                Task(title=task_title, duration_minutes=int(duration), priority=priority)
            )
            st.success(f"Added '{task_title}' to {owner.pets[pet_index].name}.")

    # Show every task across all pets so the user sees what will be scheduled.
    all_tasks = owner.all_tasks()
    if all_tasks:
        st.write("All tasks:")
        st.table(
            [
                {
                    "Task": t.title,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority,
                    "Done": "✅" if t.completed else "",
                }
                for t in all_tasks
            ]
        )

    st.divider()

    # --- Build schedule ---
    st.subheader("Build Schedule")
    col_time, col_start = st.columns(2)
    with col_time:
        available = st.number_input(
            "Time available today (minutes)", min_value=0, max_value=1440, value=120
        )
    with col_start:
        start_hour = st.number_input("Day starts at (hour)", min_value=0, max_value=23, value=8)

    if st.button("Generate schedule", type="primary"):
        scheduler = Scheduler()
        # The Scheduler pulls tasks straight from the Owner via all_tasks().
        plan = scheduler.plan_for_owner(owner, int(available), int(start_hour))

        st.markdown(f"### Daily plan for {owner.name}")
        if plan["items"]:
            st.table(
                [
                    {
                        "Time": item["time"],
                        "Task": item["task"].title,
                        "Duration (min)": item["task"].duration_minutes,
                        "Priority": item["task"].priority,
                    }
                    for item in plan["items"]
                ]
            )
            st.caption(
                f"Total scheduled: {plan['total_minutes']} min of {int(available)} available."
            )
        else:
            st.info("Nothing fit within the available time.")

        if plan["skipped"]:
            st.warning(
                "Skipped (not enough time): "
                + ", ".join(
                    f"{t.title} ({t.duration_minutes} min)" for t in plan["skipped"]
                )
            )

        with st.expander("Why this plan?"):
            st.text(scheduler.explain(plan))
else:
    st.info("Add a pet before creating tasks and a schedule.")
