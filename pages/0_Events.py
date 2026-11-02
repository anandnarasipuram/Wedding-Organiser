from datetime import time

import pandas as pd
import streamlit as st
from auth import require_login
from db import add_event, delete_row, insert_row, list_events, list_rows, update_row

st.set_page_config(page_title="Events", layout="centered")
require_login()


@st.dialog("Add an event")
def add_event_dialog():
    name = st.text_input("Event name")
    event_date = st.date_input("Date")
    start_time = st.time_input("Start time", value=None)
    expected = st.number_input("Expected guests", min_value=0, step=10)
    if st.button("Add event", type="primary") and name:
        add_event(name, event_date, start_time, int(expected))
        st.rerun()


@st.dialog("Add to schedule")
def add_schedule_dialog(event_id):
    start = st.time_input("Start time", value=time(9, 0))
    activity = st.text_input("What happens, e.g. puja begins")
    who = st.text_input("Who is in charge (optional)")
    notes = st.text_input("Notes (optional)")
    if st.button("Add", type="primary") and activity:
        insert_row(
            "schedule_items",
            {
                "event_id": event_id,
                "start_time": start.isoformat(),
                "activity": activity,
                "who": who or None,
                "notes": notes or None,
            },
        )
        st.rerun()


st.title("Events")

if st.button("➕ Add an event", type="primary"):
    add_event_dialog()

events = list_events()
if not events:
    st.info("No events yet. Add your first one with the button above.")
    st.stop()

st.dataframe(
    [
        {
            "Date": e["event_date"],
            "Event": e["name"],
            "Time": (e["start_time"] or "")[:5],
            "Expected guests": e["expected_guests"],
        }
        for e in events
    ],
    hide_index=True,
)

st.header("Schedule")
event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
event_id = st.selectbox("Event", options=list(event_names), format_func=event_names.get)

if st.button("➕ Add to schedule"):
    add_schedule_dialog(event_id)

items = sorted(list_rows("schedule_items", event_id), key=lambda r: r["start_time"] or "")

if not items:
    st.info("Nothing scheduled for this event yet.")
    st.stop()

df = pd.DataFrame(
    [
        {
            "id": i["id"],
            "Time": time.fromisoformat(i["start_time"]) if i["start_time"] else None,
            "Activity": i["activity"],
            "Who": i["who"] or "",
            "Notes": i["notes"] or "",
        }
        for i in items
    ]
)

st.caption("Edit any cell. To delete, select a row with the box on its left, click the bin above the table, then Save changes.")
edited = st.data_editor(
    df,
    hide_index=True,
    num_rows="delete",
    column_config={
        "id": None,
        "Time": st.column_config.TimeColumn("Time", format="HH:mm"),
    },
    key=f"schedule_{event_id}",
)

if st.button("Save changes"):
    for row_id in set(df["id"]) - set(edited["id"]):
        delete_row("schedule_items", row_id)
    for index, row in edited.iterrows():
        if any(row[c] != df.loc[index, c] for c in ["Time", "Activity", "Who", "Notes"]):
            update_row(
                "schedule_items",
                row["id"],
                {
                    "start_time": row["Time"].isoformat() if pd.notna(row["Time"]) else None,
                    "activity": row["Activity"],
                    "who": row["Who"] or None,
                    "notes": row["Notes"] or None,
                },
            )
    st.rerun()