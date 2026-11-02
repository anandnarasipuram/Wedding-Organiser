from uuid import uuid4

import streamlit as st
from supabase import create_client

PHOTO_BUCKET = "event-photos"


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


def list_rows(table, event_id=None):
    query = get_client().table(table).select("*")
    if event_id:
        query = query.eq("event_id", event_id)
    return query.order("created_at").execute().data


def insert_row(table, values):
    get_client().table(table).insert(values).execute()


def update_row(table, row_id, values):
    get_client().table(table).update(values).eq("id", row_id).execute()


def delete_row(table, row_id):
    get_client().table(table).delete().eq("id", row_id).execute()


def upload_photo(event_id, data, caption):
    path = f"{event_id}/{uuid4().hex}.jpg"
    client = get_client()
    client.storage.from_(PHOTO_BUCKET).upload(path, data, {"content-type": "image/jpeg"})
    client.table("event_photos").insert(
        {"event_id": event_id, "path": path, "caption": caption or None}
    ).execute()


@st.cache_data(ttl=3000)
def photo_url(path):
    result = get_client().storage.from_(PHOTO_BUCKET).create_signed_url(path, 3600)
    return result.get("signedURL") or result.get("signedUrl")


def delete_photo(photo_id, path):
    client = get_client()
    client.storage.from_(PHOTO_BUCKET).remove([path])
    client.table("event_photos").delete().eq("id", photo_id).execute()


def fetch_all(table, columns="*", order=None):
    rows, start = [], 0
    while True:
        query = get_client().table(table).select(columns)
        if order:
            query = query.order(order)
        batch = query.range(start, start + 999).execute().data
        rows += batch
        if len(batch) < 1000:
            return rows
        start += 1000


def list_guests():
    return fetch_all("guests", order="name")


@st.cache_data(ttl=60)
def guest_party_sizes():
    sizes = {}
    for row in fetch_all("guest_events", "guest_id, party_size"):
        sizes[row["guest_id"]] = max(sizes.get(row["guest_id"], 1), row["party_size"])
    return sizes


def import_guests(rows):
    client = get_client()
    for start in range(0, len(rows), 200):
        chunk = rows[start : start + 200]
        created = (
            client.table("guests")
            .insert(
                [
                    {
                        "name": r["name"],
                        "phone": r["phone"] or None,
                        "side": r["side"],
                        "notes": r["notes"] or None,
                    }
                    for r in chunk
                ]
            )
            .execute()
            .data
        )
        invites = []
        for r, guest in zip(chunk, created):
            for event_id in r["event_ids"]:
                invites.append({"guest_id": guest["id"], "event_id": event_id, "party_size": r["people"]})
        if invites:
            client.table("guest_events").insert(invites).execute()