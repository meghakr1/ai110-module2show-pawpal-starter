import streamlit as st

from pawpal_system import Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.markdown("Plan your pet's day. Add care tasks, set your time budget, and let PawPal+ build a schedule.")

st.divider()

# --- Owner + pet info ---
st.subheader("Owner & Pet")
col_a, col_b, col_c = st.columns(3)
with col_a:
    owner_name = st.text_input("Owner name", value="Jordan")
with col_b:
    pet_name = st.text_input("Pet name", value="Mochi")
with col_c:
    species = st.selectbox("Species", ["dog", "cat", "other"])

st.divider()

# --- Task entry ---
st.subheader("Tasks")
st.caption("Add a few care tasks. Duration and priority feed the scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

col_add, col_clear = st.columns(2)
with col_add:
    if st.button("Add task", use_container_width=True):
        st.session_state.tasks.append(
            {"title": task_title, "duration_minutes": int(duration), "priority": priority}
        )
with col_clear:
    if st.button("Clear tasks", use_container_width=True):
        st.session_state.tasks = []

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

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
    if not st.session_state.tasks:
        st.warning("Add at least one task first.")
    else:
        tasks = [
            Task(
                title=t["title"],
                duration_minutes=t["duration_minutes"],
                priority=t["priority"],
            )
            for t in st.session_state.tasks
        ]
        scheduler = Scheduler()
        plan = scheduler.build_plan(tasks, int(available), int(start_hour))

        st.markdown(f"### Daily plan for {pet_name} ({species}) — {owner_name}")
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
