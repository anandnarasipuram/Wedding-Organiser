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