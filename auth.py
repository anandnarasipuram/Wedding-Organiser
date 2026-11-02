import streamlit as st


def require_login():
    if st.session_state.get("authed"):
        return
    password = st.text_input("Family password", type="password")
    if password and password == st.secrets["app_password"]:
        st.session_state["authed"] = True
        st.rerun()
    if password:
        st.error("Wrong password")
    st.stop()