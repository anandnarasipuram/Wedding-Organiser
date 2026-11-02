import streamlit as st
from db import add_event, list_events

st.set_page_config(page_title="Wedding Planner", layout="centered")


def check_password():
    if st.session_state.get("authed"):
        return True
    password = st.text_input("Family password", type="password")
    if password and password == st.secrets["app_password"]:
        st.session_state["authed"] = True
        st.rerun()
    elif password:
        st.error("Wrong password")
    return False


if not check_password():
    st.stop()

st.title("Wedding Planner")
st.header("Events")

events = list_events()
rows = [
    {
        "Date": e["event_date"],
        "Event": e["name"],
        "Time": (e["start_time"] or "")[:5],
        "Expected guests": e["expected_guests"],
    }
    for e in events
]
st.dataframe(rows, hide_index=True)

st.subheader("Add an event")
with st.form("add_event", clear_on_submit=True):
    name = st.text_input("Event name")
    event_date = st.date_input("Date")
    start_time = st.time_input("Start time", value=None)
    expected = st.number_input("Expected guests", min_value=0, step=10)
    if st.form_submit_button("Add event") and name:
        add_event(name, event_date, start_time, int(expected))
        st.rerun()