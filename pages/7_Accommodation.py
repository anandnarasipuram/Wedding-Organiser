from datetime import date, time
from urllib.parse import quote_plus

import streamlit as st
from auth import require_login
from db import (
    delete_row,
    guest_party_sizes,
    insert_row,
    list_guests,
    list_rows,
    update_row,
)

st.set_page_config(page_title="Accommodation", layout="centered")
require_login()


def to_date(value):
    return date.fromisoformat(value) if value else None


def to_time(value):
    return time.fromisoformat(value) if value else None


def when_text(day, hour):
    parts = []
    if day:
        parts.append(date.fromisoformat(day).strftime("%d %b"))
    if hour:
        parts.append(hour[:5])
    return " ".join(parts) or "not set"


def maps_link(a):
    if a["maps_url"]:
        return a["maps_url"]
    if a["address"]:
        return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(a["address"])
    return None


def clean_phone(phone):
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


def fields(prefix, a=None):
    a = a or {}
    return {
        "name": st.text_input("Name of the place", value=a.get("name") or "", key=f"{prefix}_name"),
        "address": st.text_input("Address", value=a.get("address") or "", key=f"{prefix}_address"),
        "maps_url": st.text_input(
            "Google Maps link (optional)", value=a.get("maps_url") or "", key=f"{prefix}_maps"
        ),
        "rooms": st.number_input(
            "Number of rooms", min_value=0, step=1, value=a.get("rooms") or 0, key=f"{prefix}_rooms"
        ),
        "checkin_date": st.date_input(
            "Check-in date", value=to_date(a.get("checkin_date")), key=f"{prefix}_in_date"
        ),
        "checkin_time": st.time_input(
            "Check-in time", value=to_time(a.get("checkin_time")), key=f"{prefix}_in_time"
        ),
        "checkout_date": st.date_input(
            "Check-out date", value=to_date(a.get("checkout_date")), key=f"{prefix}_out_date"
        ),
        "checkout_time": st.time_input(
            "Check-out time", value=to_time(a.get("checkout_time")), key=f"{prefix}_out_time"
        ),
        "contact_name": st.text_input(
            "Contact person", value=a.get("contact_name") or "", key=f"{prefix}_contact"
        ),
        "contact_phone": st.text_input(
            "Contact phone with country code", value=a.get("contact_phone") or "", key=f"{prefix}_phone"
        ),
    }


def to_payload(v):
    return {
        "name": v["name"],
        "address": v["address"] or None,
        "maps_url": v["maps_url"] or None,
        "rooms": int(v["rooms"]) or None,
        "checkin_date": v["checkin_date"].isoformat() if v["checkin_date"] else None,
        "checkin_time": v["checkin_time"].isoformat() if v["checkin_time"] else None,
        "checkout_date": v["checkout_date"].isoformat() if v["checkout_date"] else None,
        "checkout_time": v["checkout_time"].isoformat() if v["checkout_time"] else None,
        "contact_name": v["contact_name"] or None,
        "contact_phone": v["contact_phone"] or None,
    }


@st.dialog("Add accommodation")
def add_accommodation_dialog():
    values = fields("new")
    if st.button("Add accommodation", type="primary") and values["name"]:
        insert_row("accommodations", to_payload(values))
        st.rerun()


@st.dialog("Add guests")
def add_guests_dialog(accommodation_id, available, sizes):
    labels = {g["id"]: f'{g["name"]} · {g["side"] or ""}' for g in available}
    plain = {g["id"]: g["name"] for g in available}
    chosen = st.multiselect("Guests not placed yet", options=list(labels), format_func=labels.get)
    counts = {}
    for guest_id in chosen:
        counts[guest_id] = st.number_input(
            f"People in {plain[guest_id]}",
            min_value=1,
            value=sizes.get(guest_id, 1),
            key=f"people_{accommodation_id}_{guest_id}",
        )
    if st.button("Add", type="primary") and chosen:
        insert_row(
            "accommodation_guests",
            [
                {"accommodation_id": accommodation_id, "guest_id": guest_id, "people": int(counts[guest_id])}
                for guest_id in chosen
            ],
        )
        st.rerun()


accommodations = list_rows("accommodations")
guests = list_guests()
guest_by_id = {g["id"]: g for g in guests}
placements = list_rows("accommodation_guests")
placed_ids = {p["guest_id"] for p in placements}
available = [g for g in guests if g["id"] not in placed_ids]
sizes = guest_party_sizes()

st.title("Accommodation")

if st.button("➕ Add accommodation", type="primary"):
    add_accommodation_dialog()

col1, col2, col3 = st.columns(3)
col1.metric("Places", len(accommodations))
col2.metric("People placed", sum(p["people"] for p in placements))
col3.metric("Guests without a place", len(available))

if not accommodations:
    st.info("No accommodation added yet. Add the first one with the button above.")

for a in accommodations:
    stay = [p for p in placements if p["accommodation_id"] == a["id"]]
    people = sum(p["people"] for p in stay)

    with st.container(border=True):
        head_col, bin_col = st.columns([9, 1], vertical_alignment="center")
        head_col.markdown(f"### {a['name']}")
        with bin_col.popover("🗑️"):
            st.button(
                "Delete this place and its guest list",
                key=f"del_acc_{a['id']}",
                on_click=delete_row,
                args=("accommodations", a["id"]),
            )

        if a["address"]:
            st.caption(a["address"])
        link = maps_link(a)
        if link:
            st.markdown(f"[📍 Open in Google Maps]({link})")
        st.markdown(f"🛏️ {a['rooms'] or 0} rooms · 👥 {people} people staying")
        st.markdown(
            f"Check-in: **{when_text(a['checkin_date'], a['checkin_time'])}** · "
            f"Check-out: **{when_text(a['checkout_date'], a['checkout_time'])}**"
        )
        if a["contact_name"] or a["contact_phone"]:
            contact = a["contact_name"] or "Contact"
            if a["contact_phone"]:
                contact += f" · [📞 {a['contact_phone']}](tel:{clean_phone(a['contact_phone'])})"
            st.markdown(contact)

        st.markdown("**Guests staying here**")
        if not stay:
            st.caption("Nobody added yet.")
        for p in stay:
            guest = guest_by_id.get(p["guest_id"], {"name": "Unknown guest"})
            guest_col, remove_col = st.columns([9, 1], vertical_alignment="center")
            guest_col.markdown(f"{guest['name']} :gray[{p['people']} people]")
            with remove_col.popover("🗑️"):
                st.button(
                    "Remove from here",
                    key=f"remove_{p['id']}",
                    on_click=delete_row,
                    args=("accommodation_guests", p["id"]),
                )

        if st.button("➕ Add guests", key=f"add_guests_{a['id']}"):
            add_guests_dialog(a["id"], available, sizes)

        with st.expander("Edit details"):
            with st.form(f"edit_form_{a['id']}"):
                values = fields(f"edit_{a['id']}", a)
                if st.form_submit_button("Save details") and values["name"]:
                    update_row("accommodations", a["id"], to_payload(values))
                    st.rerun()