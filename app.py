import streamlit as st
from auth import require_login

require_login()

pages = [
    st.Page("pages/0_Events.py", title="Events", default=True),
    st.Page("pages/1_Guests.py", title="Guests"),
    st.Page("pages/2_Shopping.py", title="Shopping"),
    st.Page("pages/3_Requirements.py", title="Requirements"),
    st.Page("pages/4_Todo.py", title="To-do"),
]

st.navigation(pages).run()