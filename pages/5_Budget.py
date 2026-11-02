import pandas as pd
import streamlit as st
from auth import require_login
from config import BUDGET_CEILING, EXPENSE_CATEGORIES, FAMILY
from db import delete_row, insert_row, list_events, list_rows, update_row

st.set_page_config(page_title="Budget", layout="centered")
require_login()

PAYERS = FAMILY + ["Other"]
WHOLE = "Whole wedding"
events = list_events()
event_names = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
id_by_name = {name: event_id for event_id, name in event_names.items()}
event_options = [WHOLE] + list(event_names.values())


def status_of(amount, paid):
    if paid <= 0:
        return "quoted"
    if paid >= amount:
        return "settled"
    return "advance paid"


@st.dialog("Add an expense")
def add_expense_dialog():
    description = st.text_input("What for, e.g. wedding hall booking")
    category = st.selectbox("Category", EXPENSE_CATEGORIES)
    where = st.selectbox("Event", event_options)
    amount = st.number_input("Total amount (₹)", min_value=0, step=5000)
    paid = st.number_input("Paid so far (₹)", min_value=0, step=5000)
    paid_by = st.selectbox("Paid by", PAYERS)
    if st.button("Add expense", type="primary") and description:
        insert_row(
            "expenses",
            {
                "description": description,
                "category": category,
                "event_id": id_by_name.get(where),
                "amount": amount,
                "paid": paid,
                "paid_by": paid_by,
            },
        )
        st.rerun()


expenses = list_rows("expenses")
shopping = list_rows("shopping_items")

shopping_total = sum(s["price"] for s in shopping)
shopping_paid = sum(s["price"] for s in shopping if s["status"] == "bought")
committed = sum(x["amount"] for x in expenses) + shopping_total
paid_total = sum(x["paid"] for x in expenses) + shopping_paid
left = BUDGET_CEILING - committed

st.title("Budget")

if st.button("➕ Add an expense", type="primary"):
    add_expense_dialog()

col1, col2 = st.columns(2)
col1.metric("Budget ceiling", f"₹{BUDGET_CEILING:,.0f}")
col2.metric("Committed", f"₹{committed:,.0f}")
col3, col4 = st.columns(2)
col3.metric("Paid so far", f"₹{paid_total:,.0f}")
col4.metric("Left under ceiling", f"₹{left:,.0f}")

st.progress(
    min(committed / BUDGET_CEILING, 1.0),
    text=f"{committed / BUDGET_CEILING:.0%} of the ceiling committed",
)
if left < 0:
    st.error(f"Over the ceiling by ₹{-left:,.0f}")

st.header("By event")
event_rows = []
for event_id, label in [(None, WHOLE)] + [(e["id"], e["name"]) for e in events]:
    other = sum(x["amount"] for x in expenses if x["event_id"] == event_id)
    shop = sum(s["price"] for s in shopping if s["event_id"] == event_id)
    event_rows.append({"Event": label, "Shopping": shop, "Other costs": other, "Total": shop + other})
st.dataframe(
    event_rows,
    hide_index=True,
    column_config={
        "Shopping": st.column_config.NumberColumn(format="₹%.0f"),
        "Other costs": st.column_config.NumberColumn(format="₹%.0f"),
        "Total": st.column_config.NumberColumn(format="₹%.0f"),
    },
)

st.header("By category")
category_totals = {}
for x in expenses:
    category_totals[x["category"]] = category_totals.get(x["category"], 0) + x["amount"]
if shopping_total:
    category_totals["Clothing and shopping (from Shopping page)"] = shopping_total
st.dataframe(
    [{"Category": k, "Total": v} for k, v in sorted(category_totals.items(), key=lambda kv: -kv[1])],
    hide_index=True,
    column_config={"Total": st.column_config.NumberColumn(format="₹%.0f")},
)

st.header("Expenses")
if not expenses:
    st.info("No expenses yet. Shopping costs are already counted above.")
    st.stop()

df = pd.DataFrame(
    [
        {
            "id": x["id"],
            "Description": x["description"],
            "Category": x["category"],
            "Event": event_names.get(x["event_id"], WHOLE),
            "Amount": x["amount"],
            "Paid": x["paid"],
            "Paid by": x["paid_by"] or "",
            "Status": status_of(x["amount"], x["paid"]),
        }
        for x in expenses
    ]
)

st.caption("Edit any cell. To delete, select a row with the box on its left, click the bin above the table, then Save changes.")
edited = st.data_editor(
    df,
    hide_index=True,
    num_rows="delete",
    disabled=["Status"],
    column_config={
        "id": None,
        "Category": st.column_config.SelectboxColumn(options=EXPENSE_CATEGORIES),
        "Event": st.column_config.SelectboxColumn(options=event_options),
        "Amount": st.column_config.NumberColumn("Amount (₹)", min_value=0, step=5000),
        "Paid": st.column_config.NumberColumn("Paid (₹)", min_value=0, step=5000),
        "Paid by": st.column_config.SelectboxColumn(options=PAYERS),
    },
    key="expenses_editor",
)

if st.button("Save changes"):
    for row_id in set(df["id"]) - set(edited["id"]):
        delete_row("expenses", row_id)
    for index, row in edited.iterrows():
        if any(row[c] != df.loc[index, c] for c in ["Description", "Category", "Event", "Amount", "Paid", "Paid by"]):
            update_row(
                "expenses",
                row["id"],
                {
                    "description": row["Description"],
                    "category": row["Category"],
                    "event_id": id_by_name.get(row["Event"]),
                    "amount": float(row["Amount"] or 0),
                    "paid": float(row["Paid"] or 0),
                    "paid_by": row["Paid by"] or None,
                },
            )
    st.rerun()