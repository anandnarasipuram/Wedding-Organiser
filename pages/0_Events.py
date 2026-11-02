from datetime import time
from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image

from auth import require_login
from db import (
    delete_photo,
    delete_row,
    insert_row,
    list_events,
    list_rows,
    photo_url,
    update_row,
    upload_photo,
)

st.set_page_config(page_title="Events", layout="centered")
require_login()


def clean_phone(phone):
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


def prepare_image(file):
    image = Image.open(file).convert("RGB")
    image.thumbnail((1600, 1600))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@st.dialog("Add an event")
def add_event_dialog():
    name = st.text_input("Event name")
    event_date = st.date_input("Date")
    start_time = st.time_input("Start time", value=None)
    expected = st.number_input("Expected guests", min_value=0, step=10)
    dress_code = st.text_input("Dress code (optional)")
    if st.button("Add event", type="primary") and name:
        insert_row(
            "events",
            {
                "name": name,
                "event_date": event_date.isoformat(),
                "start_time": start_time.isoformat() if start_time else None,
                "expected_guests": int(expected),
                "dress_code": dress_code or None,
            },
        )
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


@st.dialog("Add a vendor")
def add_vendor_dialog(event_id):
    name = st.text_input("Vendor name")
    role = st.text_input("What they do, e.g. caterer or photographer")
    phone = st.text_input("Phone with country code")
    if st.button("Add vendor", type="primary") and name:
        insert_row(
            "event_vendors",
            {"event_id": event_id, "name": name, "role": role or None, "phone": phone or None},
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
            "Dress code": e.get("dress_code") or "",
        }
        for e in events
    ],
    hide_index=True,
)

event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
event_id = st.selectbox("Open an event", options=list(event_names), format_func=event_names.get)
event = next(e for e in events if e["id"] == event_id)

st.header(event["name"])
details_tab, schedule_tab, vendors_tab, photos_tab = st.tabs(["Details", "Schedule", "Vendors", "Photos"])

with details_tab:
    with st.form(f"details_{event_id}"):
        dress_code = st.text_input("Dress code", value=event.get("dress_code") or "", key=f"dress_{event_id}")
        highlights = st.text_area(
            "Highlights of the event",
            value=event.get("highlights") or "",
            height=120,
            key=f"highlights_{event_id}",
        )
        notes = st.text_area(
            "Additional details",
            value=event.get("notes") or "",
            height=120,
            key=f"notes_{event_id}",
        )
        if st.form_submit_button("Save details"):
            update_row(
                "events",
                event_id,
                {
                    "dress_code": dress_code or None,
                    "highlights": highlights or None,
                    "notes": notes or None,
                },
            )
            st.rerun()

with schedule_tab:
    if st.button("➕ Add to schedule"):
        add_schedule_dialog(event_id)

    items = sorted(list_rows("schedule_items", event_id), key=lambda r: r["start_time"] or "")
    if not items:
        st.info("Nothing scheduled for this event yet.")
    else:
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
        st.caption(
            "Edit any cell. To delete, select a row with the box on its left, click the bin above the table, then Save changes."
        )
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
        if st.button("Save changes", key="save_schedule"):
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

with vendors_tab:
    if st.button("➕ Add a vendor"):
        add_vendor_dialog(event_id)

    vendors = list_rows("event_vendors", event_id)
    if not vendors:
        st.info("No vendors added yet.")
    for v in vendors:
        with st.container(border=True):
            info_col, bin_col = st.columns([9, 1], vertical_alignment="center")
            line = f"**{v['name']}**"
            if v["role"]:
                line += f" :gray[{v['role']}]"
            info_col.markdown(line)
            if v["phone"]:
                info_col.markdown(f"[📞 {v['phone']}](tel:{clean_phone(v['phone'])})")
            with bin_col.popover("🗑️"):
                st.button(
                    "Delete vendor",
                    key=f"del_vendor_{v['id']}",
                    on_click=delete_row,
                    args=("event_vendors", v["id"]),
                )

with photos_tab:
    round_no = st.session_state.get("photo_round", 0)
    st.caption("Add finalised photos from your gallery, or take a new one with the camera.")
    uploads = st.file_uploader(
        "Choose photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"upload_{event_id}_{round_no}",
    )
    with st.expander("Take a photo with the camera"):
        shot = st.camera_input("Camera", key=f"camera_{event_id}_{round_no}")
    caption = st.text_input("Caption (optional)", key=f"caption_{event_id}_{round_no}")

    if st.button("Save photos", type="primary"):
        files = list(uploads or [])
        if shot:
            files.append(shot)
        if files:
            for file in files:
                upload_photo(event_id, prepare_image(file), caption)
            st.session_state["photo_round"] = round_no + 1
            st.rerun()
        else:
            st.warning("Choose or take a photo first.")

    photos = list_rows("event_photos", event_id)
    columns = st.columns(2)
    for index, photo in enumerate(photos):
        with columns[index % 2]:
            st.image(photo_url(photo["path"]), caption=photo["caption"])
            with st.popover("🗑️"):
                st.button(
                    "Delete photo",
                    key=f"del_photo_{photo['id']}",
                    on_click=delete_photo,
                    args=(photo["id"], photo["path"]),
                )