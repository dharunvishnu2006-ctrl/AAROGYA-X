"""Patients page: the directory and the clinical risk lookup."""

import pandas as pd
import streamlit as st

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import Patient
from aarogya.m14_audit.logging_setup import log_error
from aarogya.m6_risk.analytics import score_patient_risk
from aarogya.platform import paths
from aarogya.platform.timeutil import to_ist_display

PAGE_MODULE = "m15_dashboard"
IST_LABELS = {"updated_at": "updated_at (IST)"}

conn = cs.get_connection(str(paths.DB_PATH))

try:
    st.title("Patients")
    all_records = cs.get_all_patients(conn)
    patient_id_options = [p["patient_id"] for p in all_records]
    tab_directory, tab_lookup = st.tabs(["Directory", "Risk lookup"])

    df_current = (
        pd.DataFrame(all_records) if all_records else pd.DataFrame()
    )
    # Show stored UTC times in IST
    if not df_current.empty:
        df_current["updated_at"] = df_current["updated_at"].map(
            to_ist_display
        )

    with tab_directory:
        st.subheader("Patient Clinical Profile Directory")
        if not df_current.empty:
            st.dataframe(
                df_current.rename(columns=IST_LABELS),
                use_container_width=True,
            )
        else:
            st.info("No records to display.")

    with tab_lookup:
        st.subheader("Patient Clinical Risk Lookup")
        search_id = st.selectbox(
            "Select Patient to Inspect", options=[""] + patient_id_options
        )
        if search_id:
            patient_row = cs.get_patient(conn, search_id)
            if patient_row:
                p_data = dict(patient_row)
                p_data.pop("updated_at", None)
                patient_obj = Patient(**p_data)
                risk_tier = score_patient_risk(patient_obj)

                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Name:** {patient_obj.name}")
                    st.write(
                        f"**Demographics:** {patient_obj.age} yrs | "
                        f"{patient_obj.gender} | {patient_obj.city}"
                    )
                    last_sync = to_ist_display(patient_row["updated_at"])
                    st.write(f"**Last Sync (IST):** {last_sync}")
                    st.write(
                        "**Calculated BMI Category:** "
                        f"`{patient_obj.get_bmi_category()}`"
                    )

                with c2:
                    tier_color = (
                        "🔴"
                        if risk_tier == "High"
                        else "🟡" if risk_tier == "Medium" else "🟢"
                    )
                    st.metric(
                        "Clinical Risk Tier", f"{tier_color} {risk_tier}"
                    )
                    htn = patient_obj.is_hypertensive()
                    dm = patient_obj.is_diabetic()
                    st.write(
                        "**Hypertension Check:** "
                        f"{'Positive' if htn else 'Negative'}"
                    )
                    st.write(
                        "**Diabetic Check:** "
                        f"{'Positive' if dm else 'Negative'}"
                    )

                st.json(p_data)

except Exception as err:
    log_error(PAGE_MODULE, err)
    raise
finally:
    conn.close()
