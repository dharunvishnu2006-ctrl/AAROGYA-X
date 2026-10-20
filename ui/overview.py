"""Overview page: three rows, every number counted from the store."""

import pandas as pd
import streamlit as st

from aarogya.m1_emr import clinical_store as cs
from aarogya.m14_audit.logging_setup import log_error
from aarogya.m15_dashboard import kpis
from aarogya.m15_dashboard.charts import (
    donut_width_px,
    plot_occupancy_donut,
)
from aarogya.m15_dashboard.brand import (
    BRAND,
    current_version,
    today_line,
)
from aarogya.m2_his.hospitals import get_hospitals
from aarogya.platform import paths

PAGE_MODULE = "m15_dashboard"
ALL_HOSPITALS = "All hospitals"
NOT_FOUND = "Patient not found."
NETWORK_WIDE = "Network-wide"
FLOW_HEIGHT_PX = 220
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
RECENT_TABS = {
    "All": "all",
    "Inpatients": "open",
    "Discharged": "discharged",
}


def show_search(conn, text):
    """Shows one patient card, or why not."""
    try:
        card = kpis.find_patient(conn, text)
    except ValueError as err:
        st.error(str(err))
        return
    if card is None:
        st.warning(NOT_FOUND)
        return
    st.info(
        f"**{card['patient_id']} · {card['name']}** — "
        f"age {card['age_band']} · {card['city']} · "
        f"risk {card['risk']} · {card['stay']}"
    )


conn = cs.get_connection(str(paths.DB_PATH))

try:
    hospitals = {h.hospital_id: h.name for h in get_hospitals(conn)}

    # Show name, Vision, Today lines
    st.title(BRAND.name)
    st.caption(f"Vision: {BRAND.vision}")
    st.markdown(f":green[**{today_line(current_version())}**]")
    pick, find = st.columns(2, vertical_alignment="bottom")
    hospital_id = pick.selectbox(
        "Hospital",
        options=[None, *hospitals],
        format_func=lambda hid: (
            ALL_HOSPITALS if hid is None else hospitals[hid]
        ),
        key="overview_hospital",
    )
    search = find.text_input(
        "Find patient by ID", placeholder="P007", key="overview_search"
    )
    if search.strip():
        show_search(conn, search)
    st.caption("Synthetic data - not for clinical use")

    k = kpis.overview_kpis(conn, hospital_id)
    cards = st.columns(5, gap="medium")
    with cards[0]:
        st.metric("Patients", k["patients"])
        st.caption(NETWORK_WIDE)
    with cards[1]:
        st.metric("Inpatients", k["inpatients"])
    with cards[2]:
        st.metric("High-risk", k["high_risk"])
        st.caption(NETWORK_WIDE)
    with cards[3]:
        st.metric("Beds occupied", k["beds_occupied"])
        st.caption(f"of {k['beds_total']} beds")
    with cards[4]:
        st.metric("Beds available", k["beds_available"])

    st.write("")
    # Show occupancy donut and flow
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Bed occupancy")
        fig = plot_occupancy_donut(
            k["beds_occupied"], k["beds_available"], k["occupancy_pct"]
        )
        # Draw at natural size, never stretched
        st.pyplot(fig, transparent=True, width=donut_width_px(fig))
        if k["over_capacity"]:
            st.warning(
                "Over 100% of beds: " + ", ".join(k["over_capacity"])
            )
    with right:
        st.subheader("Patient flow")
        flow = kpis.patient_flow(conn, hospital_id)
        if flow.empty:
            st.info("No stays recorded yet.")
        else:
            first, last = flow.index.min(), flow.index.max()
            chart = flow.copy()
            chart.index = pd.to_datetime(chart.index)
            # Fix height to keep Row 2 compact
            st.line_chart(chart, height=FLOW_HEIGHT_PX)
            st.caption(
                f"Admissions and discharges per day (IST), "
                f"{first} to {last}"
            )

    st.write("")
    # Show recent patients and attention
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Recent patients")
        for tab, status in zip(
            st.tabs(list(RECENT_TABS)), RECENT_TABS.values()
        ):
            rows = kpis.recent_patients(conn, hospital_id, status=status)
            with tab:
                st.dataframe(
                    pd.DataFrame(rows, columns=kpis.RECENT_COLUMNS),
                    hide_index=True,
                    use_container_width=True,
                )
    with right:
        st.subheader("Needs attention")
        attention = kpis.needs_attention(conn, hospital_id)
        st.caption("Rule-based thresholds - not a prediction model")
        if attention["high_risk"]:
            st.markdown(
                "\n".join(f"- {line}" for line in attention["high_risk"])
            )
            shown = len(attention["high_risk"])
            if attention["high_risk_total"] > shown:
                st.caption(
                    f"Showing {shown} of {attention['high_risk_total']} "
                    "high-risk patients."
                )
        else:
            st.caption("No high-risk patients.")
        for name in attention["over_capacity"]:
            st.warning(f"{name} is over 100% of beds.")

    with st.expander("Coming next - 10 modules", expanded=False):
        st.markdown(
            "\n".join(
                f"- {name} - arrives in {v}" for name, v in COMING_NEXT
            )
        )
    st.caption("Decision support only - the clinician decides.")

except Exception as err:
    log_error(PAGE_MODULE, err)
    raise
finally:
    conn.close()
