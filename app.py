"""AAROGYA X entry: config, logging, bootstrap, health, navigation.

Every feature lives on exactly one page under ui/.
"""

import streamlit as st

from aarogya.m1_emr.bootstrap import bootstrap_store
from aarogya.m14_audit import health as health_check
from aarogya.m14_audit.logging_setup import (
    configure_logging,
    log_error,
    log_event,
)
from aarogya.m15_dashboard.brand import BRAND, current_version
from aarogya.platform import paths

APP_MODULE = "app"
EMR_MODULE = "m1_emr"
INIT_STATUS_KEY = "init_status"
# List unbuilt modules without numbers
COMING_NEXT = (
    ("Laboratory", "v2"),
    ("Pharmacy", "v2"),
    ("Emergency triage", "v2"),
    ("Medical imaging", "v3-v4"),
    ("Risk prediction model", "v3-v4"),
    ("AI clinical assistant", "v5"),
    ("OPD and appointments", "v5"),
    ("Login and roles", "v5"),
    ("Billing", "v6"),
    ("Command centre", "v6"),
)

st.set_page_config(page_title=BRAND.name, layout="wide")
configure_logging(paths.LOG_FILE)


@st.cache_resource
def bootstrap_database():
    log_event("app_start", APP_MODULE)
    try:
        return bootstrap_store(
            str(paths.DB_PATH),
            str(paths.SEED_CSV),
            str(paths.HOSPITALS_CSV),
            str(paths.STAYS_CSV),
        )
    except Exception as err:
        log_error(EMR_MODULE, err)
        raise


# Share seed status with Records page
st.session_state[INIT_STATUS_KEY] = bootstrap_database()

# Check health after bootstrap, before pages
healthy = health_check.health(paths.DB_PATH)["status"] == "healthy"
system_health = st.Page(
    "ui/system_health.py",
    title="System health",
    icon=":material/monitor_heart:",
)
if healthy:
    pages = [
        st.Page(
            "ui/overview.py",
            title="Overview",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "ui/patients.py", title="Patients", icon=":material/group:"
        ),
        st.Page(
            "ui/beds.py", title="Beds & occupancy", icon=":material/bed:"
        ),
        st.Page(
            "ui/risk_statistics.py",
            title="Risk & statistics",
            icon=":material/monitoring:",
        ),
        st.Page(
            "ui/records.py", title="Records", icon=":material/folder_open:"
        ),
        system_health,
    ]
else:
    # Offer only health while store fails
    pages = [system_health]

st.navigation(pages).run()
# Show Coming next above foot
with st.sidebar.expander("Coming next - 10 modules", expanded=False):
    st.markdown(
        "\n".join(f"- {name} - arrives in {v}" for name, v in COMING_NEXT)
    )
status = "System healthy" if healthy else "System unhealthy"
st.sidebar.caption(f"{BRAND.name} {current_version()} · {status}")
