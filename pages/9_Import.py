import pandas as pd
import streamlit as st
from auth import require_login
from db import import_guests, list_events, list_guests

st.set_page_config(page_title="Import guests", layout="centered")
require_login()

TEMPLATE = """Name,Phone,Side,People,Events,Notes
Sharma family,+919876543210,Groom's side,4,"Haldi, Reception",Close relatives
"""


def digits(phone):
    return "".join(ch for ch in str(phone) if ch.isdigit())[-10:]


def parse_vcf(text):
    people, current = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.upper() == "BEGIN:VCARD":
            current = {"Name": "", "Phone": ""}
        elif line.upper() == "END:VCARD":
            if current and current["Name"]:
                people.append(current)
            current = None
        elif current is not None and ":" in line:
            key = line.upper()
            if key.startswith("FN") and not current["Name"]:
                current["Name"] = line.split(":", 1)[1].strip()
            elif key.startswith("TEL") and not current["Phone"]:
                current["Phone"] = line.split(":", 1)[1].strip()
    return people


events = list_events()
event_labels = {e["id"]: f'{e["event_date"]} · {e["name"]}' for e in events}
event_ids_by_name = {e["name"].strip().lower(): e["id"] for e in events}

st.title("Import guests")
st.write("Upload a CSV file from Excel or Google Sheets, or a contacts file (.vcf) from your phone or iCloud.")
st.download_button("Download CSV template", TEMPLATE, file_name="guest_template.csv", mime="text/csv")

uploaded = st.file_uploader("Guest file", type=["csv", "vcf"])
if not uploaded:
    st.stop()

is_contacts = uploaded.name.lower().endswith(".vcf")
if is_contacts:
    table = pd.DataFrame(parse_vcf(uploaded.getvalue().decode("utf-8", errors="ignore")))
else:
    table = pd.read_csv(uploaded, dtype=str, keep_default_na=False)

table.columns = [str(c).strip().lower() for c in table.columns]
if table.empty or "name" not in table.columns:
    st.error("No names found. The file needs a Name column.")
    st.stop()

for column in ["phone", "side", "people", "events", "notes"]:
    if column not in table.columns:
        table[column] = ""

default_events = st.multiselect(
    "Invite everyone you import to these events",
    options=list(event_labels),
    format_func=event_labels.get,
)
default_side = st.selectbox("Side for rows without one", ["Groom's side", "Bride's side", "Common friends"])
default_people = st.number_input("People per row when the file has no number", min_value=1, value=1)

existing = list_guests()
known_phones = {digits(g["phone"]) for g in existing if g["phone"]}
known_names = {g["name"].strip().lower() for g in existing}

preview = pd.DataFrame(
    {
        "Name": table["name"].str.strip(),
        "Phone": table["phone"].str.strip(),
        "Side": table["side"].str.strip().replace("", default_side),
        "People": pd.to_numeric(table["people"], errors="coerce").fillna(default_people).clip(lower=1).astype(int),
        "Events": table["events"].str.strip(),
        "Notes": table["notes"].str.strip(),
    }
)
preview = preview[preview["Name"] != ""].reset_index(drop=True)
preview["Already in list"] = [
    (bool(digits(phone)) and digits(phone) in known_phones) or name.lower() in known_names
    for name, phone in zip(preview["Name"], preview["Phone"])
]

select_all = st.checkbox("Select all new guests", value=not is_contacts)
preview.insert(0, "Import", [select_all and not dup for dup in preview["Already in list"]])

st.caption("Tick the rows to import. Use the search icon above the table to find people in a long list.")
edited = st.data_editor(
    preview,
    hide_index=True,
    disabled=["Already in list"],
    column_config={
        "Import": st.column_config.CheckboxColumn(),
        "People": st.column_config.NumberColumn(min_value=1, step=1),
    },
    key=f"import_{uploaded.name}_{select_all}",
)

selected = edited[edited["Import"]]
st.caption(f"{len(selected)} of {len(edited)} rows selected.")

if st.button(f"Import {len(selected)} guests", type="primary") and len(selected):
    rows, unknown = [], set()
    for _, row in selected.iterrows():
        event_ids = set(default_events)
        for name in str(row["Events"]).split(","):
            name = name.strip()
            if not name:
                continue
            event_id = event_ids_by_name.get(name.lower())
            if event_id:
                event_ids.add(event_id)
            else:
                unknown.add(name)
        rows.append(
            {
                "name": row["Name"],
                "phone": row["Phone"],
                "side": row["Side"],
                "notes": row["Notes"],
                "people": int(row["People"]),
                "event_ids": event_ids,
            }
        )
    import_guests(rows)
    st.success(f"Imported {len(rows)} guests.")
    if unknown:
        st.warning("These event names were not found and were skipped: " + ", ".join(sorted(unknown)))