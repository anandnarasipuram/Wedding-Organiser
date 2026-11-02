import math
from datetime import time

import streamlit as st
from auth import require_login
from config import DISH_TYPES, FOOD_BUFFER, MEAL_NAMES
from db import delete_row, insert_row, list_events, list_invites, list_rows

st.set_page_config(page_title="Food", layout="centered")
require_login()

events = list_events()
if not events:
    st.info("Add your events on the Events page first.")
    st.stop()

event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}


@st.dialog("Add a meal")
def add_meal_dialog(event_id):
    name = st.selectbox("Meal", MEAL_NAMES)
    custom = st.text_input("Or type your own name (optional)")
    start = st.time_input("Time", value=None)
    diet = st.text_input("Diet notes, e.g. pure vegetarian, no onion or garlic")
    count = st.number_input("Guests for this meal (0 = use the number on the page)", min_value=0, step=10)
    if st.button("Add meal", type="primary"):
        insert_row(
            "meals",
            {
                "event_id": event_id,
                "name": custom or name,
                "meal_time": start.isoformat() if start else None,
                "diet_notes": diet or None,
                "headcount": int(count) or None,
            },
        )
        st.rerun()


st.title("Food and menus")
event_id = st.selectbox("Event", options=list(event_names), format_func=event_names.get)
event = next(e for e in events if e["id"] == event_id)

invites = list_invites(event_id)
confirmed = sum(i["party_size"] for i in invites if i["rsvp"] == "yes")
pending = sum(i["party_size"] for i in invites if i["rsvp"] == "pending")

if invites:
    base = confirmed + pending
    source = "confirmed and pending guests from the Guests page"
else:
    base = event["expected_guests"] or 0
    source = "the expected guests of this event, because nobody is invited yet"
plan_for = math.ceil(base * (1 + FOOD_BUFFER))

col1, col2, col3 = st.columns(3)
col1.metric("Confirmed", confirmed)
col2.metric("Pending", pending)
col3.metric("Plan food for", plan_for)
st.caption(f"Based on {source}, plus a {FOOD_BUFFER:.0%} buffer.")

if st.button("➕ Add a meal", type="primary"):
    add_meal_dialog(event_id)

meals = sorted(list_rows("meals", event_id), key=lambda m: m["meal_time"] or "99")
if not meals:
    st.info("No meals yet for this event. Add one with the button above.")
    st.stop()

all_dishes = list_rows("dishes")

for meal in meals:
    dishes = [d for d in all_dishes if d["meal_id"] == meal["id"]]
    guests = meal["headcount"] or plan_for
    when = f" · {meal['meal_time'][:5]}" if meal["meal_time"] else ""

    with st.container(border=True):
        head_col, bin_col = st.columns([9, 1], vertical_alignment="center")
        head_col.markdown(f"**{meal['name']}**{when} · for {guests:,} guests")
        if meal["diet_notes"]:
            head_col.caption(meal["diet_notes"])
        with bin_col.popover("🗑️"):
            st.button(
                "Delete meal and its dishes",
                key=f"del_meal_{meal['id']}",
                on_click=delete_row,
                args=("meals", meal["id"]),
            )

        for d in dishes:
            dish_col, dish_bin = st.columns([9, 1], vertical_alignment="center")
            dish_col.markdown(f"{d['name']} :gray[{d['dish_type'] or ''}]")
            with dish_bin.popover("🗑️"):
                st.button(
                    "Delete dish",
                    key=f"del_dish_{d['id']}",
                    on_click=delete_row,
                    args=("dishes", d["id"]),
                )

        with st.popover("➕ Add dishes"):
            with st.form(f"dishes_form_{meal['id']}", clear_on_submit=True):
                names = st.text_area("Dishes, one per line")
                dish_type = st.selectbox("Type", DISH_TYPES)
                if st.form_submit_button("Add"):
                    lines = [line.strip() for line in names.splitlines() if line.strip()]
                    if lines:
                        insert_row(
                            "dishes",
                            [{"meal_id": meal["id"], "name": line, "dish_type": dish_type} for line in lines],
                        )
                        st.rerun()
                        