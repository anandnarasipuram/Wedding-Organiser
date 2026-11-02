import streamlit as st
from supabase import create_client


@st.cache_resource
def get_client():
    return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])


def list_events():
    return (
        get_client()
        .table("events")
        .select("*")
        .order("event_date")
        .order("start_time")
        .execute()
        .data
    )


def add_event(name, event_date, start_time, expected_guests):
    get_client().table("events").insert(
        {
            "name": name,
            "event_date": event_date.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "expected_guests": expected_guests,
        }
    ).execute()

def add_guest(name, phone, side, notes, event_ids, party_size):
    client = get_client()
    guest = (
        client.table("guests")
        .insert({"name": name, "phone": phone or None, "side": side, "notes": notes or None})
        .execute()
        .data[0]
    )
    if event_ids:
        client.table("guest_events").insert(
            [{"guest_id": guest["id"], "event_id": eid, "party_size": party_size} for eid in event_ids]
        ).execute()


def list_invites(event_id):
    return (
        get_client()
        .table("guest_events")
        .select("guest_id, rsvp, party_size, guests(name, phone, side)")
        .eq("event_id", event_id)
        .execute()
        .data
    )


def update_invite(guest_id, event_id, rsvp, party_size):
    (
        get_client()
        .table("guest_events")
        .update({"rsvp": rsvp, "party_size": party_size})
        .eq("guest_id", guest_id)
        .eq("event_id", event_id)
        .execute()
    )