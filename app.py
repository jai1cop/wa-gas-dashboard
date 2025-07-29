import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from fetch_gbb_data import get_all_gbb_data
from data_fetcher import validate_dataframe

st.set_page_config(page_title="WA Gas Market Dashboard", page_icon="⛽", layout="wide")

@st.cache_data(ttl=1800, show_spinner=True)  # Cache data for 30 minutes
def load_data():
    return get_all_gbb_data()

def main():
    st.title("⛽ Western Australia Gas Market Dashboard")
    st.markdown("**Real-time data scraped from WA Gas Bulletin Board using Playwright**")

    st.sidebar.header("Dashboard Controls")

    yara_value = st.sidebar.slider(
        "Yara Pilbara Fertilisers Gas Consumption (TJ/day)",
        min_value=0, max_value=100, value=80, step=1,
        help="Adjust Yara's gas consumption and see market impacts"
    )

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.experimental_rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Sources:**")
    st.sidebar.markdown("• [WA GBB Flows](https://gbbwa.aemo.com.au/#flows)")
    st.sidebar.markdown("• [Medium Term Capacity Constraints](https://gbbwa.aemo.com.au/#reports/mediumTermCapacity)")
    st.sidebar.markdown("• [Storage Data](https://gbbwa.aemo.com.au/#reports/actualFlow)")

    with st.spinner("Scraping live data (may take 20-30 seconds)..."):
        flows, constraints, storage = load_data()

    flows_valid = validate_dataframe(flows, "Flows")
    constraints_valid = validate_dataframe(constraints, "Medium Term Capacity")
    storage_valid = validate_dataframe(storage, "Storage")

    st.subheader("📊 Data Loading Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        if flows_valid:
            st.success(f"✅ Flows Data: {len(flows)} records")
        else:
            st.error("❌ Flows data failed to load")

    with col2:
        if constraints_valid:
            st.success(f"✅ Capacity Constraints: {len(constraints)} records")
        else:
            st.error("❌ Capacity Constraints data failed")

    with col3:
        if storage_valid:
            st.success(f"✅ Storage Data: {len(storage)} records")
        else:
            st.error("❌ Storage data failed")

    if not (flows_valid or constraints_valid or storage_valid):
        st.error("No data available to display. Please check your network or AEMO GBB site.")
        return

    st.divider()
    show_dashboard(flows, constraints, storage, yara_value)

def show_dashboard(flows, constraints, storage, yara_value):
    """Display main dashboard content"""

    st.subheader("Recent Facility Flows Data")
    if not flows.empty:
        st.dataframe(flows.head(20), use_container_width=True)
    else:
        st.warning("No flows data available.")

    st.subheader("Medium Term Capacity Constraints")
    if not constraints.empty:
        st.dataframe(constraints.head(20), use_container_width=True)
    else:
        st.warning("No capacity constraint data available.")

    st.subheader("Storage Data")
    if not storage.empty:
        st.dataframe(storage.head(20), use_container_width=True)
        numeric_cols = storage.select_dtypes(include=[np.number]).columns
        if numeric_cols.any():
            st.subheader("Storage Trends")
            for col in numeric_cols[:3]:  # Display up to 3 numeric columns
                st.line_chart(storage[col], use_container_width=True)
    else:
        st.warning("No storage data available.")

    st.divider()
    st.subheader("Yara Pilbara Fertilisers Impact")

    base_yara = 80
    yara_delta = yara_value - base_yara

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Yara Consumption (TJ/day)", yara_value)
    with col2:
        st.metric("Change from Baseline", yara_delta, delta=yara_delta)
    with col3:
        impact = "Higher market tightness" if yara_delta > 0 else "Lower market tightness" if yara_delta < 0 else "Neutral"
        st.metric("Market Impact", impact)

    st.divider()
    st.subheader("🔽 Export Data")

    col1, col2, col3 = st.columns(3)
    with col1:
        if not flows.empty:
            st.download_button(
                label="Download Flows CSV",
                data=flows.to_csv(index=False).encode(),
                file_name=f"wa_flows_{time.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
    with col2:
        if not constraints.empty:
            st.download_button(
                label="Download Capacity Constraints CSV",
                data=constraints.to_csv(index=False).encode(),
                file_name=f"wa_capacity_{time.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
    with col3:
        if not storage.empty:
            st.download_button(
                label="Download Storage CSV",
                data=storage.to_csv(index=False).encode(),
                file_name=f"wa_storage_{time.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
