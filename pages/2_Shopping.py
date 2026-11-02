import pandas as pd
import streamlit as st
from auth import require_login
from config import FAMILY, SHOPPING_STATUS
from db import delete_row, insert_row, list_events, list_rows, update_row

st.set_page_config(page_title="Shopping", layout="centered")
require_login()

events = list_events()
if not events:
    st.info("Add your events on the home page first.")
    st.stop()

event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
short_names = {e["id"]: e["name"] for e in events}

st.title("Clothing and shopping")

with st.form("add_item", clear_on_submit=True):
    event_id = st.selectbox("Event", options=list(event_names), format_func=event_names.get)
    person = st.selectbox("For", FAMILY + ["Other"])
    item = st.text_input("Item, e.g. silk saree or sherwani")
    price = st.number_input("Price (₹)", min_value=0, step=500)
    status = st.selectbox("Status", SHOPPING_STATUS)
    if st.form_submit_button("Add item") and item:
        insert_row(
            "shopping_items",
            {"event_id": event_id, "person": person, "item": item, "price": price, "status": status},
        )
        st.rerun()

st.header("Items")
view = st.selectbox(
    "Show",
    options=["all"] + list(event_names),
    format_func=lambda x: "All events" if x == "all" else event_names[x],
)
items = list_rows("shopping_items", None if view == "all" else view)

if not items:
    st.info("Nothing added yet.")
    st.stop()

open_items = [i for i in items if i["status"] != "bought"]
bought_items = [i for i in items if i["status"] == "bought"]


def set_bought(row_id, key):
    status = "bought" if st.session_state[key] else "to buy"
    update_row("shopping_items", row_id, {"status": status})


def show_item(i):
    is_bought = i["status"] == "bought"
    key = f"bought_{i['id']}_{is_bought}"
    where = f" · {short_names.get(i['event_id'], '')}" if view == "all" else ""
    details = f"{i['person']} · ₹{i['price']:,.0f}{where}"
    if is_bought:
        label = f"~~{i['item']}~~ :gray[{details}]"
    else:
        label = f"**{i['item']}** :gray[{details}]"

    with st.container(border=True):
        tick_col, bin_col = st.columns([9, 1], vertical_alignment="center")
        tick_col.checkbox(label, value=is_bought, key=key, on_change=set_bought, args=(i["id"], key))
        with bin_col.popover("🗑️"):
            st.button("Delete", key=f"del_{i['id']}", on_click=delete_row, args=("shopping_items", i["id"]))


total = sum(i["price"] for i in items)
spent = sum(i["price"] for i in bought_items)

col1, col2, col3 = st.columns(3)
col1.metric("Total cost", f"₹{total:,.0f}")
col2.metric("Already bought", f"₹{spent:,.0f}")
col3.metric("Items to buy", len(open_items))

st.progress(len(bought_items) / len(items), text=f"{len(bought_items)} of {len(items)} bought")

if view != "all":
    missing = [p for p in FAMILY if p not in {i["person"] for i in items}]
    if missing:
        st.warning("No outfit yet for: " + ", ".join(missing))

for i in open_items:
    show_item(i)

with st.expander(f"Bought ({len(bought_items)})"):
    for i in bought_items:
        show_item(i)

with st.expander("Edit details"):
    df = pd.DataFrame(
        [
            {
                "id": i["id"],
                "Event": short_names.get(i["event_id"], ""),
                "Person": i["person"],
                "Item": i["item"],
                "Price": i["price"],
                "Status": i["status"],
            }
            for i in items
        ]
    )
    edited = st.data_editor(
        df,
        hide_index=True,
        disabled=["Event"],
        column_config={
            "id": None,
            "Person": st.column_config.SelectboxColumn(options=FAMILY + ["Other"]),
            "Price": st.column_config.NumberColumn("Price (₹)", min_value=0, step=500),
            "Status": st.column_config.SelectboxColumn(options=SHOPPING_STATUS),
        },
        key=f"shopping_{view}",
    )
    if st.button("Save changes"):
        for index, row in edited.iterrows():
            if any(row[c] != df.loc[index, c] for c in ["Person", "Item", "Price", "Status"]):
                update_row(
                    "shopping_items",
                    row["id"],
                    {
                        "person": row["Person"],
                        "item": row["Item"],
                        "price": float(row["Price"] or 0),
                        "status": row["Status"],
                    },
                )
        st.rerun()