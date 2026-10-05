import pandas as pd
import streamlit as st

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.bootstrap import bootstrap_store
from aarogya.m1_emr.ingest import ingest_dataframe, read_patient_csv
from aarogya.m1_emr.models import Patient
from aarogya.m14_audit.health import health
from aarogya.m14_audit.logging_setup import (
    configure_logging,
    log_error,
    log_event,
)
from aarogya.m2_his.hospitals import HOSPITAL_NETWORK
from aarogya.m6_risk.analytics import score_patient_risk
from aarogya.platform import paths
from aarogya.platform.timeutil import to_ist_display

DB_PATH = str(paths.DB_PATH)
SEED_CSV = str(paths.SEED_CSV)
APP_MODULE = "app"
LAST_INGEST_KEY = "last_ingest"
EMR_MODULE = "m1_emr"

st.set_page_config(
    page_title="AAROGYA Clinical Decision Support", layout="wide"
)
configure_logging(paths.LOG_FILE)


@st.cache_resource
def bootstrap_database():
    log_event("app_start", APP_MODULE)
    try:
        return bootstrap_store(DB_PATH, SEED_CSV)
    except Exception as err:
        log_error(EMR_MODULE, err)
        raise


init_status = bootstrap_database()

# Check health after bootstrap, before connecting
store_health = health(DB_PATH)
st.sidebar.subheader("System Health")
if store_health["status"] != "healthy":
    st.sidebar.error("Unhealthy: data store cannot be opened or queried.")
    st.sidebar.caption("Store reachable: no")
    st.stop()
st.sidebar.success(
    f"Healthy · {store_health['patient_count']} patients in store"
)
last_upload = to_ist_display(store_health["last_upload_utc"]) or "none yet"
st.sidebar.caption(f"Last upload (IST): {last_upload}")
st.sidebar.divider()

conn = cs.get_connection(DB_PATH)

try:
    if init_status.get("quarantined"):
        with st.expander(
            "⚠️ Seed Ingestion Quarantine Alert", expanded=False
        ):
            st.warning(
                f"Quarantined {len(init_status['quarantined'])} "
                "malformed rows during seed."
            )
            st.dataframe(pd.DataFrame(init_status["quarantined"]))

    st.sidebar.header("Clinical Actions")

    uploaded_file = st.sidebar.file_uploader(
        "Batch Ingest Patients (CSV)", type=["csv"]
    )
    if uploaded_file is not None:
        if st.sidebar.button("Run Ingestion"):
            upload_df = read_patient_csv(uploaded_file)
            result = ingest_dataframe(conn, upload_df)
            cs.record_ingest(
                conn, result.rows_read, result.accepted, result.rejected
            )
            log_event(
                "upload",
                EMR_MODULE,
                rows_read=result.rows_read,
                accepted=result.accepted,
                rejected=result.rejected,
            )
            # Keep result so rerun shows it
            st.session_state[LAST_INGEST_KEY] = result
            st.rerun()

    last_ingest = st.session_state.get(LAST_INGEST_KEY)
    if last_ingest is not None:
        st.sidebar.caption("Last ingestion result")
        st.sidebar.success(f"Ingested {last_ingest.accepted} new patients.")
        if last_ingest.skipped > 0:
            st.sidebar.info(
                f"Skipped {last_ingest.skipped} existing patients "
                "(duplicate IDs)."
            )
        if last_ingest.quarantine:
            st.sidebar.error(
                f"Quarantined {len(last_ingest.quarantine)} invalid rows."
            )
            st.sidebar.dataframe(
                pd.DataFrame(last_ingest.quarantine),
                hide_index=True,
            )

    st.sidebar.divider()

    st.sidebar.subheader("Record Correction")
    all_records = cs.get_all_patients(conn)
    patient_id_options = [p["patient_id"] for p in all_records]

    if patient_id_options:
        target_pid = st.sidebar.selectbox(
            "Patient ID", options=patient_id_options
        )
        field = st.sidebar.selectbox(
            "Vital Field",
            options=[
                "bmi",
                "bp_systolic",
                "bp_diastolic",
                "sugar_fasting",
                "age",
                "city",
            ],
        )
        new_val_str = st.sidebar.text_input("New Value")
        reason_str = st.sidebar.text_input("Clinical Justification")

        if st.sidebar.button("Commit Correction"):
            if not new_val_str or not reason_str:
                st.sidebar.error(
                    "Value and clinical justification are both required."
                )
            else:
                try:
                    typed_val = (
                        int(new_val_str)
                        if field == "age"
                        else (
                            float(new_val_str)
                            if field
                            in {
                                "bmi",
                                "bp_systolic",
                                "bp_diastolic",
                                "sugar_fasting",
                            }
                            else new_val_str.strip()
                        )
                    )
                    cs.correct_patient_vital(
                        conn,
                        target_pid,
                        field,
                        typed_val,
                        reason_str.strip(),
                    )
                    log_event("correction_saved", EMR_MODULE)
                    st.sidebar.success(f"Updated {field} for {target_pid}.")
                    st.rerun()
                except (ValueError, TypeError, KeyError) as err:
                    log_error(EMR_MODULE, err)
                    st.sidebar.error(f"Correction rejected: {err}")

    st.title("AAROGYA Clinical Decision Support System")

    tab_dashboard, tab_directory, tab_lookup, tab_hospitals, tab_audit = (
        st.tabs(
            [
                "Dashboard Metrics",
                "Patient Directory",
                "Risk Lookup",
                "Hospital Network",
                "Audit Log",
            ]
        )
    )

    df_current = (
        pd.DataFrame(all_records) if all_records else pd.DataFrame()
    )
    # Show stored UTC times in IST
    if not df_current.empty:
        df_current["updated_at"] = df_current["updated_at"].map(
            to_ist_display
        )
    ist_labels = {
        "updated_at": "updated_at (IST)",
        "recorded_at": "recorded_at (IST)",
    }

    with tab_dashboard:
        if not df_current.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Active Cohort Size", len(df_current))
            c2.metric(
                "Mean Systolic BP",
                f"{df_current['bp_systolic'].mean():.1f} mmHg",
            )
            c3.metric(
                "Mean Fasting Sugar",
                f"{df_current['sugar_fasting'].mean():.1f} mg/dL",
            )
            c4.metric("Mean BMI", f"{df_current['bmi'].mean():.1f}")

            st.subheader("Cohort Vitals Overview")
            st.dataframe(
                df_current[
                    [
                        "patient_id",
                        "name",
                        "age",
                        "gender",
                        "bmi",
                        "bp_systolic",
                        "bp_diastolic",
                        "sugar_fasting",
                        "city",
                        "updated_at",
                    ]
                ].rename(columns=ist_labels),
                use_container_width=True,
            )
        else:
            st.info("No clinical records found in the database.")

    with tab_directory:
        st.subheader("Patient Clinical Profile Directory")
        if not df_current.empty:
            st.dataframe(
                df_current.rename(columns=ist_labels),
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

    with tab_hospitals:
        st.subheader("Regional Hospital Network Occupancy")
        if not df_current.empty:
            norm_counts = (
                df_current["city"]
                .astype(str)
                .str.strip()
                .str.lower()
                .value_counts()
                .to_dict()
            )
            h_data = []
            for h in HOSPITAL_NETWORK:
                admissions = norm_counts.get(h.city.strip().lower(), 0)
                rate = h.occupancy_rate(admissions)
                h_data.append(
                    {
                        "Hospital ID": h.hospital_id,
                        "Hospital Name": h.name,
                        "City": h.city,
                        "Total Capacity": h.total_beds,
                        "Active Cohort Admissions": admissions,
                        "Occupancy Rate (%)": f"{rate:.1f}%",
                        "Status": (
                            "⚠️ High Load" if rate >= 80.0 else "Normal"
                        ),
                    }
                )
            st.dataframe(pd.DataFrame(h_data), use_container_width=True)
        else:
            st.info(
                "No cohort data available to compute hospital occupancies."
            )

    with tab_audit:
        st.subheader("Immutable Correction History")
        audit_target = st.selectbox(
            "Filter Audit Trail",
            options=["All Patients"] + patient_id_options,
        )
        audit_records = (
            cs.get_all_history(conn)
            if audit_target == "All Patients"
            else cs.get_patient_history(conn, audit_target)
        )
        if audit_records:
            df_audit = pd.DataFrame(audit_records)
            df_audit["recorded_at"] = df_audit["recorded_at"].map(
                to_ist_display
            )
            st.dataframe(
                df_audit.rename(columns=ist_labels),
                use_container_width=True,
            )
        else:
            st.info("No clinical adjustments recorded in audit ledger.")

except Exception as err:
    log_error(APP_MODULE, err)
    raise
finally:
    conn.close()
