from datetime import date
from urllib.parse import quote

import streamlit as st
from auth import require_login
from config import DEFAULT_COUNTRY_CODE
from db import delete_row, fetch_all, insert_row, list_events, list_guests, list_invites, list_rows

st.set_page_config(page_title="WhatsApp", layout="centered")
require_login()

DEFAULT_INVITE = """Namaste {name} 🙏
You are warmly invited to the {event} on {date} {time}.
{dress}
{details}
We would love to have you with us!"""

DEFAULT_STAY = """Hello {name} 🙏
Here are your stay details for the wedding:
🏨 {place}
📍 {map}
Address: {address}
Check-in: {checkin}
Check-out: {checkout}
Contact: {contact}"""

DEFAULT_TRANSPORT = """Hello {name} 🙏
Vehicles available during the wedding:
{vehicles}
Please contact the driver directly for pickups."""


def fill(template, values):
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return "\n".join(line for line in template.splitlines() if line.strip())


def wa_link(phone, message):
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 10:
        digits = DEFAULT_COUNTRY_CODE + digits
    return f"https://wa.me/{digits}?text={quote(message)}"


def day_text(value):
    return date.fromisoformat(value).strftime("%d %b") if value else ""


def when_text(day, hour):
    return " ".join(part for part in [day_text(day), (hour or "")[:5]] if part) or "not set"


def maps_link(a):
    if a["maps_url"]:
        return a["maps_url"]
    if a["address"]:
        return "https://www.google.com/maps/search/?api=1&query=" + quote(a["address"])
    return "not set"


def vehicles_text(vehicles):
    lines = []
    for v in vehicles:
        line = f"• {v['vehicle_name']}"
        if v["vehicle_number"]:
            line += f" ({v['vehicle_number']})"
        if v["driver_name"] or v["driver_phone"]:
            line += f" · Driver: {v['driver_name'] or ''} {v['driver_phone'] or ''}".rstrip()
        start, end = day_text(v["available_from"]), day_text(v["available_to"])
        if start and end:
            line += f" · {start} to {end}"
        elif start or end:
            line += f" · {start or end}"
        lines.append(line)
    return "\n".join(lines)


log = {(r["guest_id"], r["kind"]): r["id"] for r in fetch_all("share_log")}


def toggle_sent(guest_id, kind, key, row_id):
    if st.session_state[key]:
        insert_row("share_log", {"guest_id": guest_id, "kind": kind})
    elif row_id:
        delete_row("share_log", row_id)


def guest_row(guest, kind, message):
    sent_id = log.get((guest["id"], kind))
    name_col, button_col, sent_col = st.columns([5, 3, 2], vertical_alignment="center")
    name_col.markdown(f"**{guest['name']}** :gray[{guest.get('extra', '')}]")
    if guest.get("phone"):
        button_col.link_button("💬 WhatsApp", wa_link(guest["phone"], message))
    else:
        button_col.caption("no phone")
    key = f"sent_{guest['id']}_{kind}"
    sent_col.checkbox(
        "Sent",
        value=bool(sent_id),
        key=key,
        on_change=toggle_sent,
        args=(guest["id"], kind, key, sent_id),
    )


def show_list(items, kind, message_for, prefix):
    if not items:
        st.info("No guests to show here yet.")
        return
    search = st.text_input("Search name", key=f"{prefix}_search").strip().lower()
    only_unsent = st.checkbox("Only guests not sent yet", key=f"{prefix}_unsent")
    sent_count = sum(1 for g in items if (g["id"], kind) in log)
    st.progress(sent_count / len(items), text=f"{sent_count} of {len(items)} sent")

    shown = [
        g
        for g in items
        if search in g["name"].lower() and not (only_unsent and (g["id"], kind) in log)
    ]
    size = 20
    pages = max(1, -(-len(shown) // size))
    page = 1
    if pages > 1:
        page = st.number_input("Page", min_value=1, max_value=pages, value=1, key=f"{prefix}_page")
    st.caption(f"{len(shown)} guests · page {page} of {pages}")
    for g in shown[(page - 1) * size : page * size]:
        guest_row(g, kind, message_for(g))


events = list_events()
guests = list_guests()
guest_by_id = {g["id"]: g for g in guests}
accommodations = list_rows("accommodations")
placements = list_rows("accommodation_guests")
vehicles = sorted(list_rows("vehicles"), key=lambda v: v["available_from"] or "9999")

st.title("Share on WhatsApp")
st.caption("Each button opens WhatsApp with a ready message. You press send yourself. Tick Sent to keep track.")

invites_tab, stay_tab, transport_tab = st.tabs(["Invitations", "Stay", "Transport"])

with invites_tab:
    if not events:
        st.info("Add your events first.")
    else:
        event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
        event_id = st.selectbox("Event", options=list(event_names), format_func=event_names.get, key="share_event")
        event = next(e for e in events if e["id"] == event_id)

        with st.expander("Edit message text"):
            template = st.text_area("Message", value=DEFAULT_INVITE, height=200, key="invite_template")
            st.caption("Placeholders: {name} {event} {date} {time} {dress} {details}")

        statuses = st.multiselect(
            "RSVP status", ["pending", "yes", "no"], default=["pending", "yes"], key="invite_status"
        )
        values = {
            "event": event["name"],
            "date": date.fromisoformat(event["event_date"]).strftime("%A, %d %B %Y"),
            "time": f"at {event['start_time'][:5]}" if event["start_time"] else "",
            "dress": f"Dress code: {event['dress_code']}" if event.get("dress_code") else "",
            "details": event.get("notes") or "",
        }
        items = sorted(
            [
                {
                    "id": i["guest_id"],
                    "name": i["guests"]["name"],
                    "phone": i["guests"]["phone"],
                    "extra": f"{i['party_size']} people · {i['rsvp']}",
                }
                for i in list_invites(event_id)
                if i["rsvp"] in statuses
            ],
            key=lambda g: g["name"],
        )
        show_list(
            items,
            f"invite:{event_id}",
            lambda g: fill(template, {**values, "name": g["name"]}),
            "invite",
        )

with stay_tab:
    if not accommodations:
        st.info("Add accommodation first.")
    else:
        names = {a["id"]: a["name"] for a in accommodations}
        acc_id = st.selectbox("Accommodation", options=list(names), format_func=names.get, key="share_stay")
        a = next(x for x in accommodations if x["id"] == acc_id)

        with st.expander("Edit message text"):
            stay_template = st.text_area("Message", value=DEFAULT_STAY, height=240, key="stay_template")
            st.caption("Placeholders: {name} {place} {map} {address} {checkin} {checkout} {contact}")

        contact = " ".join(part for part in [a["contact_name"], a["contact_phone"]] if part) or "not set"
        values = {
            "place": a["name"],
            "map": maps_link(a),
            "address": a["address"] or "not set",
            "checkin": when_text(a["checkin_date"], a["checkin_time"]),
            "checkout": when_text(a["checkout_date"], a["checkout_time"]),
            "contact": contact,
        }
        items = sorted(
            [
                {**guest_by_id[p["guest_id"]], "extra": f"{p['people']} people"}
                for p in placements
                if p["accommodation_id"] == acc_id and p["guest_id"] in guest_by_id
            ],
            key=lambda g: g["name"],
        )
        show_list(items, "stay", lambda g: fill(stay_template, {**values, "name": g["name"]}), "stay")

with transport_tab:
    if not vehicles:
        st.info("Add vehicles on the Transport page first.")
    else:
        with st.expander("Edit message text"):
            transport_template = st.text_area("Message", value=DEFAULT_TRANSPORT, height=200, key="transport_template")
            st.caption("Placeholders: {name} {vehicles}")

        options = ["all"] + [a["id"] for a in accommodations]
        audience = st.selectbox(
            "Send to",
            options=options,
            format_func=lambda x: "All guests who have a place to stay"
            if x == "all"
            else f"Guests at {next(a['name'] for a in accommodations if a['id'] == x)}",
            key="share_transport",
        )
        items = sorted(
            [
                {**guest_by_id[p["guest_id"]], "extra": f"{p['people']} people"}
                for p in placements
                if (audience == "all" or p["accommodation_id"] == audience) and p["guest_id"] in guest_by_id
            ],
            key=lambda g: g["name"],
        )
        text = vehicles_text(vehicles)
        show_list(
            items,
            "transport",
            lambda g: fill(transport_template, {"name": g["name"], "vehicles": text}),
            "transport",
        )