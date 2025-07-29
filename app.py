import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import json

def create_advanced_header():
    """Create a professional header with navigation"""
    
    # Top banner
    st.markdown("""
    <div style="background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 1rem 0; margin: -1rem -1rem 2rem -1rem;">
        <div style="max-width: 1200px; margin: 0 auto; padding: 0 1rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center;">
                    <div style="font-size: 2.5rem; margin-right: 1rem;">⛽</div>
                    <div>
                        <h1 style="color: white; margin: 0; font-size: 2rem; font-weight: 600;">WA Gas Market Dashboard</h1>
                        <p style="color: #b3d9ff; margin: 0; font-size: 1rem;">Real-time Gas Bulletin Board Analytics</p>
                    </div>
                </div>
                <div style="text-align: right; color: white;">
                    <div style="font-size: 0.9rem; opacity: 0.8;">Data Source</div>
                    <div style="font-weight: 600;">AEMO WA GBB API</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation breadcrumb
    st.markdown("""
    <div style="margin-bottom: 1.5rem; padding: 0.5rem 0; border-bottom: 1px solid #e0e0e0;">
        <span style="color: #666; font-size: 0.9rem;">
            🏠 Home → 📊 Analytics → ⛽ WA Gas Market
        </span>
    </div>
    """, unsafe_allow_html=True)


def has_data(obj):
    """Helper function to safely check if pandas objects have data"""
    if hasattr(obj, '__len__'):
        return len(obj) > 0
    return bool(obj)

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
    
    if len(numeric_cols) == 0:
        st.warning("No numeric data found for flow visualization")
        return
    
    # Create time series if date column exists
    date_cols = [col for col in flows_df.columns if 'date' in col.lower() or 'time' in col.lower()]
    
    if len(date_cols) > 0 and len(numeric_cols) > 0:
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
        # Create bar chart with available numeric data
        if len(flows_df) > 0:
            fig = px.bar(
                flows_df.head(20),
                y=numeric_cols[0] if numeric_cols else flows_df.columns[0],
                title="Gas Flow Data (Recent Records)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

def main():
    # Header
    st.markdown('<h1 class="main-header">⛽ WA Gas Market Dashboard</h1>', unsafe_allow_html=True)
    
    # API Status
    st.markdown("""
    <div class="api-status">
        <strong>🔗 Live API Connection:</strong> This dashboard uses the official WA Gas Bulletin Board API 
        for real-time data access. No web scraping required!
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar controls
    st.sidebar.header("🎛️ Dashboard Controls")
    
    # Date selector
    st.sidebar.subheader("📅 Data Selection")
    use_current = st.sidebar.checkbox("Use Current/Latest Data", value=True)
    
    selected_date = None
    if not use_current:
        selected_date = st.sidebar.date_input(
            "Select Gas Date",
            value=date.today() - timedelta(days=1),
            max_value=date.today()
        ).strftime('%Y-%m-%d')
    
    # Data refresh
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data
    with st.spinner('🚀 Loading data from WA GBB API...'):
        if use_current:
            datasets = get_all_current_data()
        else:
            datasets = {
                'actual_flows': get_actual_flows(selected_date),
                'capacity_outlook': get_capacity_outlook(selected_date),
                'medium_term_capacity': get_medium_term_capacity(selected_date),
                'forecast_flows': get_forecast_flows(selected_date),
                'end_user_consumption': get_end_user_consumption(selected_date),
                'large_user_consumption': get_large_user_consumption(selected_date),
                'linepack_adequacy': get_linepack_adequacy(selected_date),
                'trucked_gas': get_trucked_gas(selected_date)
            }
    
    # Summary metrics
    create_summary_metrics(datasets)
    
    # Data freshness indicator
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S AWST')
    st.markdown(f'<p class="data-timestamp">📅 Dashboard updated: {current_time}</p>', 
                unsafe_allow_html=True)
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Flow Analysis", "🔧 Capacity & Constraints", "🏭 Consumption Data", 
        "📈 Forecasts", "🚛 Transportation", "📋 Raw Data"
    ])
    
    with tab1:
        st.markdown('<h2 class="sub-header">Gas Flow Analysis</h2>', unsafe_allow_html=True)
        
        flows_df = datasets.get('actual_flows', pd.DataFrame())
        
        if not flows_df.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                create_flow_chart(flows_df)
            
            with col2:
                st.subheader("📊 Flow Statistics")
                numeric_cols = flows_df.select_dtypes(include=['number']).columns
                
                if len(numeric_cols) > 0:
                    for col in numeric_cols[:3]:  # Show top 3 numeric columns
                        if flows_df[col].notna().sum() > 0:
                            st.metric(
                                label=col.replace('_', ' ').title(),
                                value=f"{flows_df[col].sum():.2f}",
                                delta=f"{flows_df[col].mean():.2f} avg"
                            )
            
            st.subheader("🔍 Recent Flow Data")
            st.dataframe(flows_df.head(50), use_container_width=True)
            
        else:
            st.info("🔄 No actual flow data available for the selected period.")
    
    with tab2:
        st.markdown('<h2 class="sub-header">Capacity & Constraints</h2>', unsafe_allow_html=True)
        
        capacity_df = datasets.get('capacity_outlook', pd.DataFrame())
        constraints_df = datasets.get('medium_term_capacity', pd.DataFrame())
        linepack_df = datasets.get('linepack_adequacy', pd.DataFrame())
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Capacity Outlook")
            if not capacity_df.empty:
                st.dataframe(capacity_df.head(20), use_container_width=True)
                
                # Try to create capacity visualization
                numeric_cols = capacity_df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    fig = px.bar(
                        capacity_df.head(10),
                        y=numeric_cols[0],
                        title="Capacity Overview",
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No capacity outlook data available")
        
        with col2:
            st.subheader("⚠️ Medium Term Constraints")
            if not constraints_df.empty:
                st.dataframe(constraints_df.head(20), use_container_width=True)
            else:
                st.info("No medium term constraint data available")
        
        if not linepack_df.empty:
            st.subheader("🔧 Linepack Adequacy")
            st.dataframe(linepack_df.head(20), use_container_width=True)
    
    with tab3:
        st.markdown('<h2 class="sub-header">Gas Consumption Data</h2>', unsafe_allow_html=True)
        
        end_user_df = datasets.get('end_user_consumption', pd.DataFrame())
        large_user_df = datasets.get('large_user_consumption', pd.DataFrame())
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏠 End User Consumption")
            if not end_user_df.empty:
                st.dataframe(end_user_df.head(20), use_container_width=True)
                
                # Create consumption chart if numeric data available
                numeric_cols = end_user_df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    fig = px.pie(
                        end_user_df.head(10),
                        values=numeric_cols[0],
                        title="End User Consumption Distribution",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No end user consumption data available")
        
        with col2:
            st.subheader("🏭 Large User Consumption")
            if not large_user_df.empty:
                st.dataframe(large_user_df.head(20), use_container_width=True)
            else:
                st.info("No large user consumption data available")
    
    with tab4:
        st.markdown('<h2 class="sub-header">Forecast Data</h2>', unsafe_allow_html=True)
        
        forecast_df = datasets.get('forecast_flows', pd.DataFrame())
        
        if not forecast_df.empty:
            st.subheader("📊 Flow Forecasts")
            st.dataframe(forecast_df.head(30), use_container_width=True)
            
            # Create forecast visualization
            numeric_cols = forecast_df.select_dtypes(include=['number']).columns
            date_cols = [col for col in forecast_df.columns if 'date' in col.lower()]
            
            if len(numeric_cols) > 0 and len(date_cols) > 0:
                try:
                    forecast_df[date_cols[0]] = pd.to_datetime(forecast_df[date_cols[0]], errors='coerce')
                    
                    fig = px.line(
                        forecast_df.head(50),
                        x=date_cols[0],
                        y=numeric_cols[0],
                        title="Gas Flow Forecasts",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating forecast chart: {e}")
        else:
            st.info("🔄 No forecast data available for the selected period.")
    
    with tab5:
        st.markdown('<h2 class="sub-header">Transportation Data</h2>', unsafe_allow_html=True)
        
        trucked_df = datasets.get('trucked_gas', pd.DataFrame())
        
        if not trucked_df.empty:
            st.subheader("🚛 Trucked Gas Data")
            st.dataframe(trucked_df.head(30), use_container_width=True)
            
            # Create trucked gas visualization
            numeric_cols = trucked_df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                fig = px.bar(
                    trucked_df.head(15),
                    y=numeric_cols[0],
                    title="Trucked Gas Volumes",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🔄 No trucked gas data available for the selected period.")
    
    with tab6:
        st.markdown('<h2 class="sub-header">Raw Data Export</h2>', unsafe_allow_html=True)
        
        # Dataset selector
        dataset_names = [name for name, df in datasets.items() if not df.empty]
        
        if dataset_names:
            selected_dataset = st.selectbox(
                "Select dataset to view/download:",
                dataset_names,
                format_func=lambda x: x.replace('_', ' ').title()
            )
            
            selected_df = datasets[selected_dataset]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(f"📊 {selected_dataset.replace('_', ' ').title()} Data")
                st.dataframe(selected_df, use_container_width=True)
            
            with col2:
                st.subheader("📥 Download Options")
                
                # CSV download
                csv_data = selected_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download as CSV",
                    data=csv_data,
                    file_name=f"wa_gas_{selected_dataset}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
                # JSON download
                json_data = selected_df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📄 Download as JSON",
                    data=json_data,
                    file_name=f"wa_gas_{selected_dataset}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
                
                # Show data info
                st.info(f"""
                **Dataset Info:**
                - Records: {len(selected_df):,}
                - Columns: {len(selected_df.columns)}
                - Size: {len(csv_data)/1024:.1f} KB
                """)
        else:
            st.warning("⚠️ No data available for download. Please check your API connection.")
    
    # Sidebar data status
    st.sidebar.subheader("📊 Data Status")
    for name, df in datasets.items():
        status = "✅" if not df.empty else "⚠️"
        count = len(df) if not df.empty else 0
        st.sidebar.write(f"{status} {name.replace('_', ' ').title()}: {count:,} records")
    
    # API endpoints info
    with st.sidebar.expander("🔗 API Endpoints Used"):
        st.write("**Base URL:** https://gbbwa.aemo.com.au/api/v1/report/")
        st.write("**Reports:**")
        for report in api_client.REPORTS.values():
            st.write(f"- {report}/current.csv")

if __name__ == "__main__":
    main()
