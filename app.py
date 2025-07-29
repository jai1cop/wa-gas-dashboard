import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import json

from fetch_gbb_data import (
    get_all_current_data, 
    get_actual_flows,
    get_capacity_outlook, 
    get_medium_term_capacity,
    get_forecast_flows,
    get_end_user_consumption,
    get_large_user_consumption,
    get_linepack_adequacy,
    get_trucked_gas,
    api_client
)

# Page configuration
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
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin: 1rem 0 2rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin: 1rem 0;
        padding: 0.5rem 0;
        border-bottom: 2px solid #3498db;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .api-status {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #27ae60;
        margin: 1rem 0;
    }
    .data-timestamp {
        color: #7f8c8d;
        font-size: 0.9rem;
        font-style: italic;
        text-align: center;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def create_summary_metrics(datasets):
    """Create summary metrics from all datasets"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        flows_count = len(datasets.get('actual_flows', pd.DataFrame()))
        st.markdown(f"""
        <div class="metric-card">
            <h3>🔄 Actual Flows</h3>
            <h2>{flows_count:,}</h2>
            <p>Records Available</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        capacity_count = len(datasets.get('capacity_outlook', pd.DataFrame()))
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 Capacity Data</h3>
            <h2>{capacity_count:,}</h2>
            <p>Records Available</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        consumption_count = len(datasets.get('end_user_consumption', pd.DataFrame()))
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏭 Consumption</h3>
            <h2>{consumption_count:,}</h2>
            <p>Records Available</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_records = sum(len(df) for df in datasets.values() if not df.empty)
        st.markdown(f"""
        <div class="metric-card">
            <h3>📈 Total Data</h3>
            <h2>{total_records:,}</h2>
            <p>Total Records</p>
        </div>
        """, unsafe_allow_html=True)

def create_flow_chart(flows_df):
    """Create interactive flow visualization"""
    if flows_df.empty:
        st.warning("No flow data available for visualization")
        return
    
    # Try to identify key columns for visualization
    numeric_cols = flows_df.select_dtypes(include=['number']).columns.tolist()
    
    if not numeric_cols:
        st.warning("No numeric data found for flow visualization")
        return
    
    # Create time series if date column exists
    date_cols = [col for col in flows_df.columns if 'date' in col.lower() or 'time' in col.lower()]
    
    if date_cols and len(numeric_cols) > 0:
        try:
            # Convert date column to datetime
            flows_df[date_cols[0]] = pd.to_datetime(flows_df[date_cols[0]], errors='coerce')
            
            # Create line chart
            fig = px.line(
                flows_df.head(100),  # Limit to first 100 records for performance
                x=date_cols[0],
                y=numeric_cols[0],
                title="Gas Flow Trends Over Time",
                labels={date_cols[0]: "Date", numeric_cols[0]: "Flow Value"}
            )
            
            fig.update_layout(
                height=400,
                xaxis_title="Time Period",
                yaxis_title="Flow Value",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error creating flow chart: {e}")
    
    else:
        # Create bar
