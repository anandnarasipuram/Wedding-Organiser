from datetime import date

import streamlit as st
from auth import require_login
from config import FAMILY
from db import delete_row, insert_row, list_events, list_rows, update_row

st.set_page_config(page_title="To-do", layout="centered")
require_login()

PEOPLE = FAMILY + ["Other"]
events = list_events()
event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
short_names = {e["id"]: e["name"] for e in events}


def place_label(value):
    if value == "all":
        return "Everything"
    if value == "general":
        return "General (no event)"
    return event_names[value]


@st.dialog("Add a task")
def add_task_dialog():
    title = st.text_input("Task, e.g. book train tickets")
    owner = st.selectbox("Who does it", PEOPLE)
    link = st.selectbox("Belongs to", options=["general"] + list(event_names), format_func=place_label)
    due = None
    if st.checkbox("Set a deadline"):
        due = st.date_input("Deadline", value=date.today())
    if st.button("Add task", type="primary") and title:
        insert_row(
            "tasks",
            {
                "title": title,
                "owner": owner,
                "event_id": None if link == "general" else link,
                "due_date": due.isoformat() if due else None,
                "status": "open",
            },
        )
        st.rerun()


st.title("To-do list")

if st.button("➕ Add a task", type="primary"):
    add_task_dialog()

col_a, col_b = st.columns(2)
who_filter = col_a.selectbox("Show tasks for", ["Everyone"] + PEOPLE)
where_filter = col_b.selectbox("Show tasks in", ["all", "general"] + list(event_names), format_func=place_label)

tasks = list_rows("tasks")
if who_filter != "Everyone":
    tasks = [t for t in tasks if t["owner"] == who_filter]
if where_filter == "general":
    tasks = [t for t in tasks if not t["event_id"]]
elif where_filter != "all":
    tasks = [t for t in tasks if t["event_id"] == where_filter]

if not tasks:
    st.info("No tasks here yet.")
    st.stop()


def set_done(row_id, key):
    status = "done" if st.session_state[key] else "open"
    update_row("tasks", row_id, {"status": status})


def show_task(t):
    is_done = t["status"] == "done"
    key = f"task_{t['id']}_{is_done}"
    where = short_names.get(t["event_id"], "General")
    details = f":gray[{t['owner'] or 'nobody yet'} · {where}]"
    if t["due_date"]:
        due_date = date.fromisoformat(t["due_date"])
        text = due_date.strftime("%d %b")
        if not is_done and due_date < date.today():
            details += f" :red[overdue {text}]"
        else:
            details += f" :gray[· {text}]"
    label = f"~~{t['title']}~~ {details}" if is_done else f"**{t['title']}** {details}"

    with st.container(border=True):
        tick_col, bin_col = st.columns([9, 1], vertical_alignment="center")
        tick_col.checkbox(label, value=is_done, key=key, on_change=set_done, args=(t["id"], key))
        with bin_col.popover("🗑️"):
            st.button("Delete", key=f"del_task_{t['id']}", on_click=delete_row, args=("tasks", t["id"]))


open_tasks = sorted(
    [t for t in tasks if t["status"] != "done"],
    key=lambda t: (t["due_date"] is None, t["due_date"] or ""),
)
done_tasks = [t for t in tasks if t["status"] == "done"]

st.progress(len(done_tasks) / len(tasks), text=f"{len(done_tasks)} of {len(tasks)} done")

for t in open_tasks:
    show_task(t)

with st.expander(f"Completed ({len(done_tasks)})"):
    for t in done_tasks:
        show_task(t)