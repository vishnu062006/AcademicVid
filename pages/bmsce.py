"""
/bmsce : the team's admin page (open it at <app url>/bmsce). Hidden from the menu.

Same app as the main page, plus the team-only sources: handwritten notes (OCR) and
custom topics (e.g. CSE). Teachers on the main page never see these.

The password is NOT in the code. Set ADMIN_PASSWORD in:
  * Streamlit Cloud: App settings -> Secrets ->  ADMIN_PASSWORD = "..."
  * locally: the .env file  ->  ADMIN_PASSWORD=...
If it is not set, the page stays locked.
"""
import hmac
import os
import time

import streamlit as st

import app

MAX_TRIES = 5
LOCK_SECONDS = 300


def _admin_password() -> str:
    # Touching st.secrets without a secrets file makes Streamlit print a red error on the
    # page, so only read it when a file exists. (Streamlit Cloud also exports secrets as
    # environment variables, so the env fallback below works there too.)
    value = ""
    secret_files = (os.path.join(".streamlit", "secrets.toml"),
                    os.path.expanduser(os.path.join("~", ".streamlit", "secrets.toml")))
    if any(os.path.exists(p) for p in secret_files):
        try:
            value = st.secrets.get("ADMIN_PASSWORD", "")
        except Exception:
            value = ""
    return str(value or os.environ.get("ADMIN_PASSWORD", "")).strip()


def _password_gate() -> bool:
    if st.session_state.get("admin_ok"):
        return True
    expected = _admin_password()
    st.markdown("### Team admin")
    if not expected:
        st.error("This page is locked: ADMIN_PASSWORD is not set on the server.")
        return False

    locked_until = st.session_state.get("admin_locked_until", 0)
    if time.time() < locked_until:
        st.error("Too many wrong tries. Please wait a few minutes.")
        return False

    with st.form("admin_login"):
        given = st.text_input("Password", type="password")
        if st.form_submit_button("Open", type="primary"):
            if hmac.compare_digest(given.encode(), expected.encode()):
                st.session_state.admin_ok = True
                st.session_state.pop("admin_tries", None)
                st.rerun()
            tries = st.session_state.get("admin_tries", 0) + 1
            st.session_state.admin_tries = tries
            time.sleep(1)                     # slow down guessing
            if tries >= MAX_TRIES:
                st.session_state.admin_locked_until = time.time() + LOCK_SECONDS
                st.session_state.admin_tries = 0
            st.error("Wrong password.")
    return False


app.set_page_config()
if _password_gate():
    app.main(admin=True, set_config=False)
