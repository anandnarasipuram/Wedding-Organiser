import pandas as pd
import streamlit as st
from auth import require_login
from db import add_guest, list_events, list_invites, update_invite

st.set_page_config(page_title="Guests", layout="centered")
require_login()

events = list_events()
if not events:
    st.info("Add your events on the home page first.")
    st.stop()

event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}

st.title("Guests")

with st.form("add_guest", clear_on_submit=True):
    name = st.text_input("Guest or family name")
    phone = st.text_input("Phone with country code")
    side = st.selectbox("Side", ["Groom's side", "Bride's side", "Common friends"])
    invited = st.multiselect("Invite to", options=list(event_names), format_func=event_names.get)
    party_size = st.number_input("Number of people", min_value=1, value=1)
    notes = st.text_input("Notes")
    if st.form_submit_button("Add guest") and name:
        add_guest(name, phone, side, notes, invited, int(party_size))
        st.rerun()

st.header("RSVPs by event")
event_id = st.selectbox("Event", options=list(event_names), format_func=event_names.get)
invites = list_invites(event_id)

if not invites:
    st.info("No guests invited to this event yet.")
    st.stop()

df = pd.DataFrame(
    [
        {
            "guest_id": i["guest_id"],
            "Name": i["guests"]["name"],
            "Side": i["guests"]["side"],
            "People": i["party_size"],
            "RSVP": i["rsvp"],
        }
        for i in invites
    ]
).sort_values("Name").reset_index(drop=True)

col1, col2, col3 = st.columns(3)
col1.metric("Invited", int(df["People"].sum()))
col2.metric("Confirmed", int(df.loc[df["RSVP"] == "yes", "People"].sum()))
col3.metric("Pending", int(df.loc[df["RSVP"] == "pending", "People"].sum()))

edited = st.data_editor(
    df,
    hide_index=True,
    disabled=["Name", "Side"],
    column_config={
        "guest_id": None,
        "People": st.column_config.NumberColumn(min_value=1, step=1),
        "RSVP": st.column_config.SelectboxColumn(options=["pending", "yes", "no"]),
    },
    key=f"editor_{event_id}",
)

if st.button("Save changes"):
    changed = edited[(edited["RSVP"] != df["RSVP"]) | (edited["People"] != df["People"])]
    for _, row in changed.iterrows():
        update_invite(row["guest_id"], event_id, row["RSVP"], int(row["People"]))
    st.rerun()
    