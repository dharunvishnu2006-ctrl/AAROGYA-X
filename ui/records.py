"""Records page: upload, record correction and correction history."""

import pandas as pd
import streamlit as st

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import ingest_dataframe, read_patient_csv
from aarogya.m14_audit.logging_setup import log_error, log_event
from aarogya.platform import paths
from aarogya.platform.timeutil import to_ist_display

EMR_MODULE = "m1_emr"
LAST_INGEST_KEY = "last_ingest"
INIT_STATUS_KEY = "init_status"
IST_LABELS = {"recorded_at": "recorded_at (IST)"}

conn = cs.get_connection(str(paths.DB_PATH))

try:
    st.title("Records")
    init_status = st.session_state.get(INIT_STATUS_KEY, {})
    if init_status.get("quarantined"):
        with st.expander(
            "⚠️ Seed Ingestion Quarantine Alert", expanded=False
        ):
            st.warning(
                f"Quarantined {len(init_status['quarantined'])} "
                "malformed rows during seed."
            )
            st.dataframe(pd.DataFrame(init_status["quarantined"]))

    col_upload, col_correct = st.columns(2, gap="large")

    with col_upload:
        st.subheader("Upload patients")
        uploaded_file = st.file_uploader(
            "Batch Ingest Patients (CSV)", type=["csv"]
        )
        if uploaded_file is not None:
            if st.button("Run Ingestion"):
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
            st.caption("Last ingestion result")
            st.success(f"Ingested {last_ingest.accepted} new patients.")
            if last_ingest.skipped > 0:
                st.info(
                    f"Skipped {last_ingest.skipped} existing patients "
                    "(duplicate IDs)."
                )
            if last_ingest.quarantine:
                st.error(
                    f"Quarantined {len(last_ingest.quarantine)} "
                    "invalid rows."
                )
                st.dataframe(
                    pd.DataFrame(last_ingest.quarantine),
                    hide_index=True,
                )

    all_records = cs.get_all_patients(conn)
    patient_id_options = [p["patient_id"] for p in all_records]

    with col_correct:
        st.subheader("Record Correction")
        if patient_id_options:
            target_pid = st.selectbox(
                "Patient ID", options=patient_id_options
            )
            field = st.selectbox(
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
            new_val_str = st.text_input("New Value")
            reason_str = st.text_input("Clinical Justification")

            if st.button("Commit Correction"):
                if not new_val_str or not reason_str:
                    st.error(
                        "Value and clinical justification are both "
                        "required."
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
                        st.success(f"Updated {field} for {target_pid}.")
                        st.rerun()
                    except (ValueError, TypeError, KeyError) as err:
                        log_error(EMR_MODULE, err)
                        st.error(f"Correction rejected: {err}")

    st.divider()
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
            df_audit.rename(columns=IST_LABELS),
            use_container_width=True,
        )
    else:
        st.info("No clinical adjustments recorded in audit ledger.")

except Exception as err:
    log_error(EMR_MODULE, err)
    raise
finally:
    conn.close()
