import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fetch_gbb_data import get_all_gbb_data
import json
import os
from datetime import datetime

# Page config
st.set_page_config(
    page_title="WA Gas Market Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
    }
    .last-updated {
        color: #666;
        font-size: 0.8rem;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def load_data():
    """Load and cache WA GBB data"""
    return get_all_gbb_data()

def get_data_freshness():
    """Check when data was last updated"""
    try:
        if os.path.exists('data/metadata.json'):
            with open('data/metadata.json', 'r') as f:
                metadata = json.load(f)
            return metadata.get('last_run', 'Unknown')
    except:
        pass
    return 'Unknown'

def main():
    # Header
    st.markdown('<h1 class="main-header">⛽ WA Gas Market Dashboard</h1>', unsafe_allow_html=True)
    
    # Data freshness indicator
    last_updated = get_data_freshness()
    if last_updated != 'Unknown':
        try:
            last_updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            last_updated_str = last_updated_dt.strftime('%Y-%m-%d %H:%M:%S AWST')
        except:
            last_updated_str = last_updated
    else:
        last_updated_str = 'Unknown'
    
    st.markdown(f'<p class="last-updated">📅 Data last updated: {last_updated_str}</p>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner('Loading WA Gas Bulletin Board data...'):
        flows_df, capacity_df, storage_df = load_data()
    
    # Sidebar
    st.sidebar.header("Dashboard Controls")
    
    # Data status
    st.sidebar.subheader("📊 Data Status")
    st.sidebar.metric("Daily Flows", f"{len(flows_df)} records")
    st.sidebar.metric("Medium Term Capacity", f"{len(capacity_df)} records")
    st.sidebar.metric("Storage Data", f"{len(storage_df)} records")
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Daily Flows", "🔧 Capacity Outlook", "🏭 Storage Data", "📋 Raw Data"])
    
    with tab1:
        st.header("Daily Facility Flows")
        
        if not flows_df.empty:
            # Create sample visualizations if data exists
            if len(flows_df.columns) > 2:
                # Try to create a chart with available data
                numeric_columns = flows_df.select_dtypes(include=['number']).columns
                if len(numeric_columns) > 0:
                    fig = px.line(flows_df.head(100), 
                                  title="Daily Gas Flows (Sample Data)",
                                  height=400)
                    st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Recent Flow Data")
            st.dataframe(flows_df.head(20), use_container_width=True)
        else:
            st.info("🔄 No daily flows data available. Data collection is in progress.")
            st.markdown("""
            **Note**: This dashboard loads data from automated scraping. If no data is visible:
            1. The GitHub Actions workflow may still be running
            2. The WA GBB website may be temporarily unavailable
            3. Data format may have changed
            """)
    
    with tab2:
        st.header("Medium Term Capacity Outlook")
        
        if not capacity_df.empty:
            st.subheader("Capacity Data")
            st.dataframe(capacity_df.head(20), use_container_width=True)
            
            # Try to create visualization if numeric data exists
            numeric_columns = capacity_df.select_dtypes(include=['number']).columns
            if len(numeric_columns) > 0:
                fig = px.bar(capacity_df.head(10), 
                             title="Medium Term Capacity Overview",
                             height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🔄 No capacity data available. Data collection is in progress.")
    
    with tab3:
        st.header("Storage Facility Data")
        
        if not storage_df.empty:
            st.subheader("Storage Information")
            st.dataframe(storage_df.head(20), use_container_width=True)
        else:
            st.info("🔄 No storage data available. Data collection is in progress.")
    
    with tab4:
        st.header("Raw Data Export")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if not flows_df.empty:
                csv_flows = flows_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Flows Data",
                    data=csv_flows,
                    file_name=f"wa_gas_flows_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if not capacity_df.empty:
                csv_capacity = capacity_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Capacity Data",
                    data=csv_capacity,
                    file_name=f"wa_gas_capacity_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col3:
            if not storage_df.empty:
                csv_storage = storage_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Storage Data",
                    data=csv_storage,
                    file_name=f"wa_gas_storage_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        # Show all raw data
        if st.checkbox("Show all raw data"):
            st.subheader("Flows Data")
            st.dataframe(flows_df)
            
            st.subheader("Capacity Data")
            st.dataframe(capacity_df)
            
            st.subheader("Storage Data")
            st.dataframe(storage_df)

if __name__ == "__main__":
    main()
