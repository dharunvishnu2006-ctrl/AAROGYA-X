"""System health page: the B1 health result in full."""

import streamlit as st

from aarogya.m14_audit.health import health
from aarogya.platform import paths
from aarogya.platform.timeutil import to_ist_display

st.title("System health")
report = health(paths.DB_PATH)
if report["status"] == "healthy":
    st.success(f"Healthy · {report['patient_count']} patients in store")
    st.caption("Store reachable: yes")
else:
    st.error("Unhealthy: data store cannot be opened or queried.")
    st.caption("Store reachable: no")
last_upload = to_ist_display(report["last_upload_utc"]) or "none yet"
st.caption(f"Last upload (IST): {last_upload}")
st.json(report)
