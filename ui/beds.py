"""Beds & occupancy page: per hospital, over 100% flagged."""

import pandas as pd
import streamlit as st

from aarogya.m1_emr import clinical_store as cs
from aarogya.m14_audit.logging_setup import log_error
from aarogya.m15_dashboard.charts import format_occupancy
from aarogya.m2_his.occupancy import hospital_occupancy
from aarogya.platform import paths

PAGE_MODULE = "m15_dashboard"
OVER_CAPACITY = "⚠️ Over capacity"

conn = cs.get_connection(str(paths.DB_PATH))

try:
    st.title("Beds & occupancy")
    st.subheader("Regional Hospital Network Occupancy")
    occupancy = hospital_occupancy(conn)
    if occupancy:
        h_data = [
            {
                "Hospital ID": h["hospital_id"],
                "Hospital Name": h["name"],
                "City": h["city"],
                "Total Beds": h["total_beds"],
                "Open Stays": h["open_stays"],
                "Occupancy Rate (%)": format_occupancy(h["occupancy_pct"]),
                "Status": OVER_CAPACITY if h["over_capacity"] else "",
            }
            for h in occupancy
        ]
        st.dataframe(pd.DataFrame(h_data), use_container_width=True)
        st.caption("Occupancy = open stays ÷ total beds.")
    else:
        st.info("No hospitals in the store yet.")

except Exception as err:
    log_error(PAGE_MODULE, err)
    raise
finally:
    conn.close()
