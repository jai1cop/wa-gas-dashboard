import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import requests
import math

# Page configuration
st.set_page_config(
    page_title="WA Gas Market Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for improved styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-icon {
        font-size: 24px;
        margin-right: 8px;
    }
    .linepack-healthy { color: #28a745; }
    .linepack-watch { color: #ffc107; }
    .linepack-critical { color: #dc3545; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Data fetching functions with caching
@st.cache_data(ttl=900)  # 15-minute cache
def fetch_supply_data():
    """Fetch supply data from WA Gas Bulletin Board"""
    # Simulated data structure - replace with actual API calls
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)
    
    supply_data = pd.DataFrame({
        'gasDay': dates,
        'Production_North': np.random.normal(800, 100, len(dates)),
        'Production_South': np.random.normal(600, 80, len(dates)),
        'Pipeline_Receipts': np.random.normal(200, 50, len(dates)),
        'Storage_Withdrawals': np.random.normal(100, 30, len(dates)),
        'LNG_Imports': np.random.normal(150, 40, len(dates))
    })
    
    # Ensure non-negative values
    for col in supply_data.columns[1:]:
        supply_data[col] = np.maximum(supply_data[col], 0)
    
    return supply_data

@st.cache_data(ttl=900)
def fetch_demand_data():
    """Fetch demand data"""
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(43)
    
    demand_data = pd.DataFrame({
        'gasDay': dates,
        'Total_Demand': np.random.normal(1000, 150, len(dates))
    })
    demand_data['Total_Demand'] = np.maximum(demand_data['Total_Demand'], 0)
    
    return demand_data

@st.cache_data(ttl=900)
def fetch_large_users_data():
    """Fetch all WA large users data - WESTERN AUSTRALIAN ASSETS ONLY"""
    np.random.seed(44)
    
    # Corrected list - WA gas market facilities only
    wa_facilities = [
        # LNG Export Facilities
        "Woodside Karratha Gas Plant", "Chevron Gorgon Train 1", "Chevron Gorgon Train 2", 
        "Chevron Gorgon Train 3", "Chevron Wheatstone Train 1", "Chevron Wheatstone Train 2",
        "Woodside Pluto Train 1", "Shell Prelude FLNG", "Woodside Browse (Proposed)",
        
        # Domestic Gas Production
        "Apache Varanus Island", "Woodside North Rankin Complex", "Woodside Goodwyn Alpha",
        "BHP Macedon Gas Plant", "Apache Devil Creek", "Origin Kwinana Power Station",
        "Synergy Kwinana Power Station", "Synergy Cockburn Power Station", "NewGen Kwinana",
        
        # Perth Basin Facilities  
        "AWE Waitsia/Xyris Gas Plant", "Origin Beharra Springs", "Strike Energy Perth Basin",
        "AWE Dongara Gas Plant", "Norwest Energy Arrowsmith", "Pilot Energy Cliff Head",
        "Triangle Energy Cliff Head", "Roc Oil Zhao Dong", "AWE Red Gully",
        
        # Industrial & Mining Users
        "Alcoa Kwinana Refinery", "Alcoa Pinjarra Refinery", "Alcoa Wagerup Refinery",
        "BHP Nickel West Kalgoorlie", "BHP Nickel West Kambalda", "Tianqi Lithium Kwinana",
        "CSBP Kwinana Ammonia", "Wesfarmers CSBP Chemicals", "Burrup Fertilisers Karratha",
        "Yara Pilbara Ammonia", "Rio Tinto Dampier Salt", "Fortescue Christmas Creek",
        "Fortescue Cloudbreak", "Roy Hill Iron Ore", "Mt Gibson Iron", "Mineral Resources",
        
        # Power Generation
        "Synergy Pinjar Power Station", "Alinta Pinjarra Power Station", "Alinta Wagerup Power Station",
        "ERM Power Neerabup", "Parkeston Power Station", "Geraldton Power Station",
        "Mumbida Wind Farm Gas Backup", "Alinta Newman Power Station", "Horizon Power Esperance",
        
        # Gas Storage & Infrastructure
        "APA Mondarra Gas Storage", "APA Tubridgi Gas Storage", "APA Parmelia Pipeline",
        "DBNGP Compressor Stations", "Goldfields Gas Pipeline", "Pilbara Energy Pipeline",
        
        # Other Industrial
        "CBH Group Grain Terminals", "Kleenheat Gas WA", "ATCO Gas Distribution",
        "Water Corporation Perth", "Cockburn Cement", "Adelaide Brighton Munster"
    ]
    
    large_users = pd.DataFrame({
        'facilityCode': [f'WA{i:03d}' for i in range(len(wa_facilities))],
        'facilityName': wa_facilities,
        'usageCategory': np.random.choice([
            'LNG Export', 'Power Generation', 'Industrial Processing', 
            'Mining Operations', 'Gas Production', 'Gas Infrastructure',
            'Chemicals & Fertilizers', 'Metals Processing'
        ], len(wa_facilities)),
        'consumptionTJ': np.random.lognormal(4, 1, len(wa_facilities)),
        'utilizationPct': np.random.uniform(60, 95, len(wa_facilities)),
        'region': np.random.choice([
            'North West Shelf', 'Perth Basin', 'Pilbara', 'South West', 
            'Goldfields', 'Mid West', 'Kimberley'
        ], len(wa_facilities)),
        'gasSource': np.random.choice([
            'North West Shelf', 'Perth Basin', 'Carnarvon Basin', 
            'Storage', 'Import'
        ], len(wa_facilities))
    })
    
    # Sort by consumption (highest first)
    large_users = large_users.sort_values('consumptionTJ', ascending=False).reset_index(drop=True)
    
    return large_users

@st.cache_data(ttl=900)
def fetch_linepack_data():
    """Fetch current linepack status"""
    # Simulated linepack data
    current_linepack = np.random.uniform(850, 1200)  # TJ
    target_midpoint = 1000  # TJ
    
    return {
        'current': current_linepack,
        'target': target_midpoint,
        'percentage': current_linepack / target_midpoint
    }

def get_linepack_status(linepack_pct):
    """Determine linepack status and styling"""
    if linepack_pct < 0.8 or linepack_pct > 1.2:
        return 'Critical', 'linepack-critical', '🔴'
    elif linepack_pct < 0.9 or linepack_pct > 1.1:
        return 'Watch', 'linepack-watch', '⚠️'
    else:
        return 'Healthy', 'linepack-healthy', '✅'

def create_header():
    """Create dashboard header with KPIs and linepack status"""
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.markdown("### ⚡ WA Gas Market Dashboard")
    
    with col2:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=False)
        if auto_refresh:
            st.rerun()
    
    with col3:
        # Current timestamp
        st.markdown(f"**Updated:** {datetime.now().strftime('%H:%M:%S')}")
    
    with col4:
        # Linepack status icon
        linepack_data = fetch_linepack_data()
        linepack_pct = linepack_data['percentage']
        status, css_class, icon = get_linepack_status(linepack_pct)
        
        st.markdown(f"""
        <div class="status-icon {css_class}" title="Linepack {linepack_data['current']:.0f} TJ ({linepack_pct:.1%} of target)">
            {icon} Linepack: {status}
        </div>
        """, unsafe_allow_html=True)

def create_supply_demand_chart():
    """Create stacked area chart with supply components and demand overlay"""
    supply_data = fetch_supply_data()
    demand_data = fetch_demand_data()
    
    # Merge supply and demand data
    chart_data = supply_data.merge(demand_data, on='gasDay')
    
    # Create stacked area chart
    fig = go.Figure()
    
    # Supply components (stacked areas)
    supply_columns = ['Production_North', 'Production_South', 'Pipeline_Receipts', 'Storage_Withdrawals', 'LNG_Imports']
    colors = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e']
    
    for i, col in enumerate(supply_columns):
        fig.add_trace(go.Scatter(
            x=chart_data['gasDay'],
            y=chart_data[col],
            stackgroup='supply',
            name=col.replace('_', ' '),
            mode='none',
            fill='tonexty' if i > 0 else 'tozeroy',
            fillcolor=colors[i % len(colors)],
            hovertemplate=f'<b>{col.replace("_", " ")}</b><br>' +
                         'Date: %{x}<br>' +
                         'Flow: %{y:.1f} TJ/d<extra></extra>'
        ))
    
    # Total supply calculation for validation
    chart_data['Total_Supply'] = chart_data[supply_columns].sum(axis=1)
    
    # Demand line (overlay)
    fig.add_trace(go.Scatter(
        x=chart_data['gasDay'],
        y=chart_data['Total_Demand'],
        mode='lines',
        name='Total Demand',
        line=dict(color='red', width=3, dash='solid'),
        hovertemplate='<b>Total Demand</b><br>' +
                     'Date: %{x}<br>' +
                     'Demand: %{y:.1f} TJ/d<extra></extra>'
    ))
    
    # Add supply-demand gap annotations
    deficit_periods = chart_data[chart_data['Total_Demand'] > chart_data['Total_Supply']]
    if len(deficit_periods) > 0:
        for idx, period in deficit_periods.head(3).iterrows():  # Show first 3 deficits
            fig.add_annotation(
                x=period['gasDay'],
                y=period['Total_Demand'],
                text="⚠️ Supply Deficit",
                showarrow=True,
                arrowhead=2,
                arrowcolor='red',
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='red'
            )
    
    # Layout styling
    fig.update_layout(
        title='Market Supply vs Demand Analysis',
        xaxis_title='Date',
        yaxis_title='Gas Flow (TJ/d)',
        hovermode='x unified',
        height=500,
        yaxis=dict(rangemode='tozero'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_large_users_display():
    """Create enhanced large users display with search and filtering"""
    large_users_df = fetch_large_users_data()
    
    st.subheader("🏭 Large User Consumption Analysis")
    st.markdown(f"**Total Users:** {len(large_users_df)} | **No display limits applied**")
    
    # Search and filter controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search facilities", placeholder="Enter facility name or category...")
    
    with col2:
        category_filter = st.selectbox("Filter by Category", 
                                     ['All'] + list(large_users_df['usageCategory'].unique()))
    
    with col3:
        region_filter = st.selectbox("Filter by Region", 
                                   ['All'] + list(large_users_df['region'].unique()))
    
    # Apply filters
    filtered_df = large_users_df.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['facilityName'].str.contains(search_term, case=False, na=False) |
            filtered_df['usageCategory'].str.contains(search_term, case=False, na=False)
        ]
    
    if category_filter != 'All':
        filtered_df = filtered_df[filtered_df['usageCategory'] == category_filter]
    
    if region_filter != 'All':
        filtered_df = filtered_df[filtered_df['region'] == region_filter]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Facilities Shown", len(filtered_df))
    with col2:
        st.metric("Total Consumption", f"{filtered_df['consumptionTJ'].sum():.0f} TJ")
    with col3:
        st.metric("Avg Utilization", f"{filtered_df['utilizationPct'].mean():.1f}%")
    with col4:
        st.metric("Top 10 Share", f"{filtered_df.head(10)['consumptionTJ'].sum() / filtered_df['consumptionTJ'].sum():.1%}")
    
    # Enhanced data table with formatting
    display_df = filtered_df.copy()
    display_df['consumptionTJ'] = display_df['consumptionTJ'].round(1)
    display_df['utilizationPct'] = display_df['utilizationPct'].round(1)
    
    # Scrollable dataframe
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            'facilityCode': 'Code',
            'facilityName': 'Facility Name',
            'usageCategory': 'Category',
            'consumptionTJ': st.column_config.NumberColumn('Consumption (TJ)', format="%.1f"),
            'utilizationPct': st.column_config.ProgressColumn('Utilization %', min_value=0, max_value=100),
            'region': 'Region'
        }
    )
    
    # Pareto chart
    if len(filtered_df) > 0:
        fig_pareto = create_pareto_chart(filtered_df)
        st.plotly_chart(fig_pareto, use_container_width=True)

def create_pareto_chart(df):
    """Create Pareto chart for large users"""
    # Sort by consumption and calculate cumulative percentage
    sorted_df = df.sort_values('consumptionTJ', ascending=False).head(20)  # Top 20 for readability
    sorted_df['cumulative_pct'] = sorted_df['consumptionTJ'].cumsum() / sorted_df['consumptionTJ'].sum() * 100
    
    # Create subplot with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Bar chart for consumption
    fig.add_trace(
        go.Bar(
            x=sorted_df['facilityName'],
            y=sorted_df['consumptionTJ'],
            name='Consumption (TJ)',
            marker_color='lightblue'
        ),
        secondary_y=False
    )
    
    # Line chart for cumulative percentage
    fig.add_trace(
        go.Scatter(
            x=sorted_df['facilityName'],
            y=sorted_df['cumulative_pct'],
            mode='lines+markers',
            name='Cumulative %',
            line=dict(color='red', width=2),
            marker=dict(size=6)
        ),
        secondary_y=True
    )
    
    # Update layout
    fig.update_xaxes(tickangle=45)
    fig.update_yaxes(title_text="Consumption (TJ)", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Percentage (%)", secondary_y=True, range=[0, 100])
    
    fig.update_layout(
        title='Large Users Pareto Analysis (Top 20)',
        height=400,
        hovermode='x unified'
    )
    
    return fig

def create_sidebar_controls():
    """Create sidebar with date range and filter controls"""
    st.sidebar.header("📊 Dashboard Controls")
    
    # Date range picker
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    
    # Quick date range buttons
    st.sidebar.markdown("**Quick Ranges:**")
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("7D"):
            start_date = datetime.now() - timedelta(days=7)
    with col2:
        if st.button("30D"):
            start_date = datetime.now() - timedelta(days=30)
    with col3:
        if st.button("90D"):
            start_date = datetime.now() - timedelta(days=90)
    
    # Unit toggle
    units = st.sidebar.radio("Display Units", ["TJ/d", "% Utilization"])
    
    # Facility multiselect
    facilities = ["All Facilities", "North Region", "South Region", "Central Region"]
    selected_facilities = st.sidebar.multiselect("Select Facilities", facilities, default=["All Facilities"])
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'units': units,
        'facilities': selected_facilities
    }

def main():
    """Main dashboard application"""
    # Create header
    create_header()
    
    # Create sidebar controls
    sidebar_params = create_sidebar_controls()
    
    # Main dashboard tabs
    tabs = st.tabs([
        "📈 Overview", 
        "⚡ Supply & Flows", 
        "🏭 Large Users", 
        "📊 Capacity & Constraints", 
        "🔮 Forecasts", 
        "📋 Raw Data"
    ])
    
    with tabs[0]:  # Overview
        st.header("Market Overview")
        
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Market Balance", "Supply > Demand", delta="50 TJ/d surplus")
        with col2:
            st.metric("Peak Utilization", "87%", delta="-3% vs yesterday")
        with col3:
            st.metric("Active Facilities", "156", delta="2 new connections")
        with col4:
            st.metric("System Pressure", "Normal", delta="Within bands")
        
        # Supply vs Demand Chart
        supply_demand_fig = create_supply_demand_chart()
        st.plotly_chart(supply_demand_fig, use_container_width=True)
    
    with tabs[1]:  # Supply & Flows
        st.header("Supply Sources & Pipeline Flows")
        
        # Supply breakdown pie chart
        supply_data = fetch_supply_data()
        latest_supply = supply_data.iloc[-1]
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Production North', 'Production South', 'Pipeline Receipts', 'Storage', 'LNG Imports'],
            values=[latest_supply['Production_North'], latest_supply['Production_South'], 
                   latest_supply['Pipeline_Receipts'], latest_supply['Storage_Withdrawals'], 
                   latest_supply['LNG_Imports']],
            hole=0.3
        )])
        fig_pie.update_layout(title="Current Supply Mix")
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Flow utilization gauge
            utilization = np.random.uniform(70, 95)
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = utilization,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Pipeline Utilization %"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)
    
    with tabs[2]:  # Large Users
        create_large_users_display()
    
    with tabs[3]:  # Capacity & Constraints
        st.header("Capacity Analysis & System Constraints")
        st.info("📊 Capacity utilization tracking and constraint identification coming soon...")
        
        # Placeholder capacity chart
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        capacity_data = pd.DataFrame({
            'Date': dates,
            'Available_Capacity': np.random.normal(1500, 100, len(dates)),
            'Utilized_Capacity': np.random.normal(1200, 150, len(dates))
        })
        
        fig_capacity = go.Figure()
        fig_capacity.add_trace(go.Scatter(x=capacity_data['Date'], y=capacity_data['Available_Capacity'], 
                                        name='Available Capacity', fill='tozeroy'))
        fig_capacity.add_trace(go.Scatter(x=capacity_data['Date'], y=capacity_data['Utilized_Capacity'], 
                                        name='Utilized Capacity', fill='tozeroy'))
        fig_capacity.update_layout(title='System Capacity Utilization Over Time')
        
        st.plotly_chart(fig_capacity, use_container_width=True)
    
    with tabs[4]:  # Forecasts
        st.header("Demand & Supply Forecasts")
        st.info("🔮 Advanced forecasting models and scenario analysis coming soon...")
        
        # Placeholder forecast chart
        future_dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
        forecast_data = pd.DataFrame({
            'Date': future_dates,
            'Forecast_Demand': np.random.normal(1100, 100, len(future_dates)),
            'Forecast_Supply': np.random.normal(1150, 120, len(future_dates))
        })
        
        fig_forecast = go.Figure()
        fig_forecast.add_trace(go.Scatter(x=forecast_data['Date'], y=forecast_data['Forecast_Supply'], 
                                        name='Supply Forecast', line=dict(dash='dash')))
        fig_forecast.add_trace(go.Scatter(x=forecast_data['Date'], y=forecast_data['Forecast_Demand'], 
                                        name='Demand Forecast', line=dict(dash='dot')))
        fig_forecast.update_layout(title='2025 Supply & Demand Forecasts')
        
        st.plotly_chart(fig_forecast, use_container_width=True)
    
    with tabs[5]:  # Raw Data
        st.header("Raw Data Downloads")
        
        with st.expander("📥 Data Export Options"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Export Supply Data"):
                    supply_data = fetch_supply_data()
                    st.download_button(
                        label="Download CSV",
                        data=supply_data.to_csv(index=False),
                        file_name=f"supply_data_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("🏭 Export Large Users"):
                    large_users = fetch_large_users_data()
                    st.download_button(
                        label="Download CSV",
                        data=large_users.to_csv(index=False),
                        file_name=f"large_users_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                if st.button("📈 Export All Data"):
                    st.info("Preparing comprehensive data export...")

if __name__ == "__main__":
    main()
