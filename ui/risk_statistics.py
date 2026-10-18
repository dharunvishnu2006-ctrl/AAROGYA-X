"""Risk & statistics page: cohort stats, groups and charts (B3)."""

import pandas as pd
import streamlit as st

from aarogya.m1_emr import clinical_store as cs
from aarogya.m14_audit.logging_setup import log_error
from aarogya.m15_dashboard.charts import (
    plot_age_distribution,
    plot_bmi_vs_age,
    plot_city_patient_count,
)
from aarogya.m6_risk.cohort_stats import (
    add_age_band,
    add_risk_level,
    cohort_size,
    describe_vitals,
    group_stats,
)
from aarogya.platform import paths

PAGE_MODULE = "m15_dashboard"
GROUPINGS = {
    "City": "city",
    "Age band": "age_band",
    "Risk level": "risk_level",
}


def flat_columns(table):
    """Joins grouped column levels for display."""
    out = table.copy()
    out.columns = [f"{v} {s}" for v, s in out.columns]
    return out


def show_chart(fig):
    """Draws a figure on a transparent background."""
    st.pyplot(fig, transparent=True)


conn = cs.get_connection(str(paths.DB_PATH))

try:
    st.title("Risk & statistics")
    all_records = cs.get_all_patients(conn)
    df_current = (
        pd.DataFrame(all_records) if all_records else pd.DataFrame()
    )
    if not df_current.empty:
        vitals = describe_vitals(df_current)
        df_cohort = add_age_band(add_risk_level(df_current))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Cohort Size", cohort_size(df_current))
        c2.metric(
            "Mean Systolic BP",
            f"{vitals.loc['bp_systolic', 'mean']:.1f} mmHg",
        )
        c3.metric(
            "Mean Fasting Sugar",
            f"{vitals.loc['sugar_fasting', 'mean']:.1f} mg/dL",
        )
        c4.metric("Mean BMI", f"{vitals.loc['bmi', 'mean']:.1f}")

        st.subheader("Cohort Vitals Summary")
        st.dataframe(vitals.round(2), use_container_width=True)

        st.subheader("Vitals by Group")
        group_tabs = st.tabs(list(GROUPINGS))
        for group_tab, column in zip(group_tabs, GROUPINGS.values()):
            table = group_stats(df_cohort, column)
            with group_tab:
                st.dataframe(
                    flat_columns(table).round(2),
                    use_container_width=True,
                )

        st.subheader("Cohort Charts")
        chart_left, chart_right = st.columns(2)
        with chart_left:
            show_chart(plot_age_distribution(df_cohort))
        with chart_right:
            show_chart(plot_city_patient_count(df_cohort))
        show_chart(plot_bmi_vs_age(df_cohort))
    else:
        st.info("No clinical records found in the database.")

except Exception as err:
    log_error(PAGE_MODULE, err)
    raise
finally:
    conn.close()
