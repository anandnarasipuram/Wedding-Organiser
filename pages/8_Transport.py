from datetime import date

import streamlit as st
from auth import require_login
from db import delete_row, insert_row, list_rows, update_row

st.set_page_config(page_title="Transport", layout="centered")
require_login()


def to_date(value):
    return date.fromisoformat(value) if value else None


def day_text(value):
    return date.fromisoformat(value).strftime("%d %b") if value else ""


def clean_phone(phone):
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


def available_text(v):
    start, end = day_text(v["available_from"]), day_text(v["available_to"])
    if start and end:
        return f"{start} to {end}"
    return start or end


def fields(prefix, v=None):
    v = v or {}
    return {
        "vehicle_name": st.text_input(
            "Vehicle, e.g. Innova or tempo traveller",
            value=v.get("vehicle_name") or "",
            key=f"{prefix}_name",
        ),
        "vehicle_number": st.text_input(
            "Vehicle number", value=v.get("vehicle_number") or "", key=f"{prefix}_number"
        ),
        "seats": st.number_input(
            "Seats", min_value=0, step=1, value=v.get("seats") or 0, key=f"{prefix}_seats"
        ),
        "driver_name": st.text_input(
            "Driver name", value=v.get("driver_name") or "", key=f"{prefix}_driver"
        ),
        "driver_phone": st.text_input(
            "Driver phone with country code", value=v.get("driver_phone") or "", key=f"{prefix}_phone"
        ),
        "available_from": st.date_input(
            "Available from", value=to_date(v.get("available_from")), key=f"{prefix}_from"
        ),
        "available_to": st.date_input(
            "Available until", value=to_date(v.get("available_to")), key=f"{prefix}_to"
        ),
        "notes": st.text_input(
            "Notes, e.g. pickup point", value=v.get("notes") or "", key=f"{prefix}_notes"
        ),
    }


def to_payload(values):
    return {
        "vehicle_name": values["vehicle_name"],
        "vehicle_number": values["vehicle_number"] or None,
        "seats": int(values["seats"]) or None,
        "driver_name": values["driver_name"] or None,
        "driver_phone": values["driver_phone"] or None,
        "available_from": values["available_from"].isoformat() if values["available_from"] else None,
        "available_to": values["available_to"].isoformat() if values["available_to"] else None,
        "notes": values["notes"] or None,
    }


@st.dialog("Add a vehicle")
def add_vehicle_dialog():
    values = fields("new")
    if st.button("Add vehicle", type="primary") and values["vehicle_name"]:
        insert_row("vehicles", to_payload(values))
        st.rerun()


vehicles = sorted(list_rows("vehicles"), key=lambda v: v["available_from"] or "9999")

st.title("Transportation")

if st.button("➕ Add a vehicle", type="primary"):
    add_vehicle_dialog()

col1, col2 = st.columns(2)
col1.metric("Vehicles", len(vehicles))
col2.metric("Total seats", sum(v["seats"] or 0 for v in vehicles))

if not vehicles:
    st.info("No vehicles added yet. Add the first one with the button above.")
    st.stop()

for v in vehicles:
    with st.container(border=True):
        head_col, bin_col = st.columns([9, 1], vertical_alignment="center")
        title = f"**{v['vehicle_name']}**"
        if v["vehicle_number"]:
            title += f" · {v['vehicle_number']}"
        head_col.markdown(title)
        with bin_col.popover("🗑️"):
            st.button(
                "Delete vehicle",
                key=f"del_vehicle_{v['id']}",
                on_click=delete_row,
                args=("vehicles", v["id"]),
            )

        if v["driver_name"] or v["driver_phone"]:
            driver = f"Driver: {v['driver_name'] or 'not set'}"
            if v["driver_phone"]:
                driver += f" · [📞 {v['driver_phone']}](tel:{clean_phone(v['driver_phone'])})"
            st.markdown(driver)
        when = available_text(v)
        details = []
        if when:
            details.append(f"Available: {when}")
        if v["seats"]:
            details.append(f"{v['seats']} seats")
        if details:
            st.caption(" · ".join(details))
        if v["notes"]:
            st.caption(v["notes"])

        with st.expander("Edit details"):
            with st.form(f"edit_form_{v['id']}"):
                values = fields(f"edit_{v['id']}", v)
                if st.form_submit_button("Save details") and values["vehicle_name"]:
                    update_row("vehicles", v["id"], to_payload(values))
                    st.rerun()

st.header("Message to share")
st.caption("Tap the copy icon at the top right of the box and paste it into WhatsApp.")
lines = ["🚗 Transport during the wedding", ""]
for v in vehicles:
    lines.append(f"{v['vehicle_name']} · {v['vehicle_number'] or 'number to follow'}")
    driver_line = f"Driver: {v['driver_name'] or 'to follow'}"
    if v["driver_phone"]:
        driver_line += f" {v['driver_phone']}"
    lines.append(driver_line)
    when = available_text(v)
    if when:
        lines.append(f"Available: {when}")
    if v["notes"]:
        lines.append(v["notes"])
    lines.append("")
st.code("\n".join(lines).strip(), language=None)