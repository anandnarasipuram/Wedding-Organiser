import pandas as pd
import streamlit as st
from auth import require_login
from config import CATEGORIES, FAMILY, REQUIREMENT_STATUS
from db import delete_row, insert_row, list_events, list_rows, update_row

st.set_page_config(page_title="Requirements", layout="centered")
require_login()

events = list_events()
if not events:
    st.info("Add your events on the home page first.")
    st.stop()

event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
short_names = {e["id"]: e["name"] for e in events}

st.title("Requirements")

with st.form("add_requirement", clear_on_submit=True):
    event_id = st.selectbox("Event", options=list(event_names), format_func=event_names.get)
    category = st.selectbox("Category", CATEGORIES)
    item = st.text_input("Item, e.g. marigold garlands")
    quantity = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
    unit = st.text_input("Unit, e.g. kg or pieces")
    assigned_to = st.selectbox("Who arranges it", FAMILY + ["Other"])
    status = st.selectbox("Status", REQUIREMENT_STATUS)
    if st.form_submit_button("Add requirement") and item:
        insert_row(
            "requirements",
            {
                "event_id": event_id,
                "category": category,
                "item": item,
                "quantity": quantity,
                "unit": unit or None,
                "assigned_to": assigned_to,
                "status": status,
            },
        )
        st.rerun()

rows = list_rows("requirements")
if not rows:
    st.info("Nothing added yet.")
    st.stop()

df_all = pd.DataFrame(
    [
        {
            "id": r["id"],
            "event_id": r["event_id"],
            "Event": short_names.get(r["event_id"], ""),
            "Category": r["category"],
            "Item": r["item"],
            "Quantity": r["quantity"],
            "Unit": r["unit"] or "",
            "Who": r["assigned_to"] or "",
            "Status": r["status"],
        }
        for r in rows
    ]
)


def set_done(row_id, key):
    status = "done" if st.session_state[key] else "needed"
    update_row("requirements", row_id, {"status": status})


def show_item(r):
    is_done = r["status"] == "done"
    key = f"done_{r['id']}_{is_done}"
    amount = f"{r['quantity']:g} {r['unit'] or ''}".strip()
    who = r["assigned_to"] or "nobody yet"
    if is_done:
        label = f"~~{r['item']}~~ :gray[{amount} · {who}]"
    else:
        label = f"**{r['item']}** :gray[{amount} · {who}]"

    with st.container(border=True):
        tick_col, bin_col = st.columns([9, 1], vertical_alignment="center")
        tick_col.checkbox(label, value=is_done, key=key, on_change=set_done, args=(r["id"], key))
        with bin_col.popover("🗑️"):
            st.button("Delete", key=f"del_{r['id']}", on_click=delete_row, args=("requirements", r["id"]))


by_event, combined = st.tabs(["By event", "Buy once, use many"])

with by_event:
    view = st.selectbox("Event", options=list(event_names), format_func=event_names.get, key="req_view")
    event_rows = [r for r in rows if r["event_id"] == view]
    open_rows = [r for r in event_rows if r["status"] != "done"]
    done_rows = [r for r in event_rows if r["status"] == "done"]

    if not event_rows:
        st.info("No requirements for this event yet.")
    else:
        st.progress(len(done_rows) / len(event_rows), text=f"{len(done_rows)} of {len(event_rows)} done")

        for r in open_rows:
            show_item(r)

        with st.expander(f"Completed ({len(done_rows)})"):
            for r in done_rows:
                show_item(r)

        with st.expander("Edit details"):
            df = df_all[df_all["event_id"] == view][
                ["id", "Category", "Item", "Quantity", "Unit", "Who", "Status"]
            ].reset_index(drop=True)
            edited = st.data_editor(
                df,
                hide_index=True,
                column_config={
                    "id": None,
                    "Category": st.column_config.SelectboxColumn(options=CATEGORIES),
                    "Quantity": st.column_config.NumberColumn(min_value=0, step=1),
                    "Who": st.column_config.SelectboxColumn(options=FAMILY + ["Other"]),
                    "Status": st.column_config.SelectboxColumn(options=REQUIREMENT_STATUS),
                },
                key=f"requirements_{view}",
            )
            if st.button("Save changes"):
                for index, row in edited.iterrows():
                    if any(
                        row[c] != df.loc[index, c]
                        for c in ["Category", "Item", "Quantity", "Unit", "Who", "Status"]
                    ):
                        update_row(
                            "requirements",
                            row["id"],
                            {
                                "category": row["Category"],
                                "item": row["Item"],
                                "quantity": float(row["Quantity"] or 0),
                                "unit": row["Unit"] or None,
                                "assigned_to": row["Who"] or None,
                                "status": row["Status"],
                            },
                        )
                st.rerun()

with combined:
    st.caption("Items needed in more than one event are listed first, so you can buy them once.")
    work = df_all.copy()
    work["Item"] = work["Item"].str.strip().str.title()
    summary = (
        work.groupby(["Category", "Item", "Unit"], as_index=False)
        .agg(
            Total=("Quantity", "sum"),
            Events=("Event", lambda s: ", ".join(sorted(set(s)))),
            Count=("Event", "nunique"),
        )
        .sort_values(["Count", "Category"], ascending=[False, True])
        .rename(columns={"Count": "No. of events"})
    )
    st.dataframe(summary, hide_index=True)