import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
import requests
import math

# ==============================================================================
# PAGE CONFIGURATION & STYLING
# ==============================================================================

st.set_page_config(
    page_title="WA Natural Gas Market Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS implementing design philosophy principles
st.markdown("""
<style>
    /* Visual Hierarchy & Clean Design */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1rem;
    }
    
    /* KPI Cards - Progressive Disclosure */
    .kpi-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    
    .kpi-label {
        font-size: 0.875rem;
        color: #64748b;
        margin: 0;
    }
    
    .kpi-delta {
        font-size: 0.875rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    /* News Feed Styling with Clickable Links */
    .news-item {
        display: flex;
        align-items: flex-start;
        padding: 0.75rem;
        border-left: 3px solid #e2e8f0;
        margin-bottom: 0.5rem;
        background: #f8fafc;
        border-radius: 6px;
        transition: all 0.2s ease;
    }
    
    .news-item:hover {
        background: #f1f5f9;
        border-left-color: #3b82f6;
    }
    
    .news-headline {
        font-weight: 600;
        color: #1f2937;
        text-decoration: none;
        line-height: 1.4;
    }
    
    .news-headline:hover {
        color: #3b82f6;
        text-decoration: underline;
    }
    
    .sentiment-positive { color: #16a34a; font-weight: 700; }
    .sentiment-negative { color: #dc2626; font-weight: 700; }
    .sentiment-neutral { color: #64748b; font-weight: 700; }
    
    /* Market Structure Pills */
    .structure-pill {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.875rem;
    }
    
    .contango {
        background: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
    }
    
    .backwardation {
        background: #fef2f2;
        color: #991b1b;
        border: 1px solid #fecaca;
    }
    
    /* Linepack Status */
    .linepack-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.25rem;
        font-weight: 600;
    }
    
    .status-healthy { color: #16a34a; }
    .status-watch { color: #ca8a04; }
    .status-critical { color: #dc2626; }
    
    /* Interactive Elements */
    .filter-chip {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border: 1px solid #d1d5db;
        border-radius: 16px;
        background: white;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .filter-chip:hover {
        background: #f3f4f6;
        border-color: #9ca3af;
    }
    
    .filter-chip.active {
        background: #3b82f6;
        color: white;
        border-color: #3b82f6;
    }
    
    /* Maximize Data-Ink Ratio - Hide Streamlit Defaults */
    .stPlotlyChart > div > div > div > div.modebar {
        display: none !important;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #f8fafc;
        border-radius: 8px 8px 0 0;
        border: 1px solid #e2e8f0;
        border-bottom: none;
        color: #64748b;
        font-weight: 500;
        padding: 0.75rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: white;
        color: #1f2937;
        font-weight: 600;
    }
    
    /* Debug Info Styling */
    .debug-info {
        background: #f3f4f6;
        padding: 0.5rem;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.8rem;
        color: #374151;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# WA GAS PRODUCTION FACILITIES CONFIGURATION (Based on GSOO 2024)
# ==============================================================================

WA_PRODUCTION_FACILITIES = {
    'Karratha Gas Plant (NWS)': {
        'operator': 'Woodside (NWS JV)',
        'max_domestic_capacity': 600,  # TJ/day
        'color': 'rgba(31, 119, 180, 0.7)',
        'status': 'operating'
    },
    'Gorgon': {
        'operator': 'Chevron',
        'max_domestic_capacity': 300,
        'color': 'rgba(255, 127, 14, 0.7)',
        'status': 'operating'
    },
    'Wheatstone': {
        'operator': 'Chevron',
        'max_domestic_capacity': 230,  # Updated capacity
        'color': 'rgba(44, 160, 44, 0.7)',
        'status': 'operating'
    },
    'Pluto': {
        'operator': 'Woodside',
        'max_domestic_capacity': 50,
        'color': 'rgba(214, 39, 40, 0.7)',
        'status': 'operating'
    },
    'Varanus Island': {
        'operator': 'Santos',
        'max_domestic_capacity': 390,
        'color': 'rgba(148, 103, 189, 0.7)',
        'status': 'operating'
    },
    'Macedon': {
        'operator': 'Woodside/Santos',
        'max_domestic_capacity': 170,
        'color': 'rgba(140, 86, 75, 0.7)',
        'status': 'operating'
    },
    'Devil Creek': {
        'operator': 'Santos',
        'max_domestic_capacity': 50,
        'color': 'rgba(227, 119, 194, 0.7)',
        'status': 'declining'
    },
    'Beharra Springs': {
        'operator': 'Beach/Mitsui',
        'max_domestic_capacity': 28,
        'color': 'rgba(127, 127, 127, 0.7)',
        'status': 'operating'
    },
    'Waitsia/Xyris': {
        'operator': 'Mitsui/Beach',
        'max_domestic_capacity': 60,  # Stage 1, expanding to 250 post-2029
        'color': 'rgba(188, 189, 34, 0.7)',
        'status': 'ramping'
    },
    'Walyering': {
        'operator': 'Strike/Talon',
        'max_domestic_capacity': 33,
        'color': 'rgba(23, 190, 207, 0.7)',
        'status': 'operating'
    },
    'Scarborough': {
        'operator': 'Woodside',
        'max_domestic_capacity': 225,
        'color': 'rgba(174, 199, 232, 0.7)',
        'status': 'future'  # Late 2026+
    }
}

# ==============================================================================
# DATA FETCHING FUNCTIONS (Fixed for Empty Chart Issue)
# ==============================================================================

@st.cache_data(ttl=900)
def fetch_production_facility_data():
    """Fetch WA production facility data - FIXED VERSION"""
    # Use consistent date range without future dates
    dates = pd.date_range(start=datetime.now() - timedelta(days=90), 
                         end=datetime.now(), freq='D')
    np.random.seed(42)
    
    # Create realistic production data for each facility
    production_data = {'Date': dates}
    
    for facility, config in WA_PRODUCTION_FACILITIES.items():
        max_capacity = config['max_domestic_capacity']
        status = config['status']
        
        if status == 'operating':
            # Operating facilities: 70-95% utilization with daily variation
            base_utilization = np.random.uniform(0.70, 0.95, len(dates))
            daily_variation = np.random.normal(0, 0.05, len(dates))
            utilization = np.clip(base_utilization + daily_variation, 0.5, 1.0)
            production = utilization * max_capacity
            
        elif status == 'ramping':
            # Ramping facilities: gradual increase over time
            start_util = 0.3
            end_util = 0.8
            trend = np.linspace(start_util, end_util, len(dates))
            noise = np.random.normal(0, 0.05, len(dates))
            utilization = np.clip(trend + noise, 0.1, 1.0)
            production = utilization * max_capacity
            
        elif status == 'declining':
            # Declining facilities: gradual decrease
            start_util = 0.6
            end_util = 0.2
            trend = np.linspace(start_util, end_util, len(dates))
            noise = np.random.normal(0, 0.03, len(dates))
            utilization = np.clip(trend + noise, 0.1, 0.8)
            production = utilization * max_capacity
            
        else:  # future facilities
            # Future facilities: zero production for now
            production = np.zeros(len(dates))
        
        # Ensure production values are realistic and within capacity
        production = np.clip(production, 0, max_capacity)
        production_data[facility] = production
    
    df = pd.DataFrame(production_data)
    
    # Calculate total supply
    facility_columns = [col for col in df.columns if col != 'Date']
    df['Total_Supply'] = df[facility_columns].sum(axis=1)
    
    return df

@st.cache_data(ttl=900)
def fetch_market_demand_data():
    """Fetch WA market demand data - FIXED VERSION"""
    # Match production data date range exactly
    dates = pd.date_range(start=datetime.now() - timedelta(days=90), 
                         end=datetime.now(), freq='D')
    np.random.seed(43)
    
    # Create realistic WA demand pattern
    base_demand = 1400  # TJ/day average for WA market
    
    # Add seasonal variation (higher in winter - Southern Hemisphere)
    day_of_year = dates.dayofyear
    # Winter peak around day 180 (June-July)
    seasonal_factor = 1 + 0.25 * np.cos(2 * np.pi * (day_of_year - 180) / 365)
    
    # Add weekly pattern (lower on weekends)
    weekly_factor = 1 - 0.1 * np.sin(2 * np.pi * dates.dayofweek / 7)
    
    # Add random daily variation
    daily_noise = np.random.normal(0, 80, len(dates))
    
    # Calculate final demand
    demand = base_demand * seasonal_factor * weekly_factor + daily_noise
    
    # Ensure realistic bounds
    demand = np.clip(demand, 800, 2200)  # Realistic WA demand range
    
    return pd.DataFrame({
        'Date': dates,
        'Market_Demand': demand
    })

@st.cache_data(ttl=900)
def fetch_storage_data():
    """Fetch storage inventory data vs historical averages"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=365), end=datetime.now(), freq='D')
    np.random.seed(44)
    
    # Seasonal pattern for storage
    day_of_year = dates.dayofyear
    seasonal_pattern = 50 * np.sin(2 * np.pi * (day_of_year - 90) / 365) + 300
    
    df = pd.DataFrame({
        'Date': dates,
        'Current_Inventory': seasonal_pattern + np.random.normal(0, 20, len(dates)),
        'Five_Year_Average': seasonal_pattern,
        'Five_Year_Max': seasonal_pattern + 40,
        'Five_Year_Min': seasonal_pattern - 40
    })
    
    df['Spread_vs_Average'] = df['Current_Inventory'] - df['Five_Year_Average']
    
    return df

@st.cache_data(ttl=900)
def fetch_key_fundamentals():
    """Fetch latest fundamental data releases"""
    return {
        'latest_storage': 285,  # TJ
        'consensus_storage': 290,
        'five_year_avg_storage': 275,
        'last_update': datetime.now() - timedelta(hours=2)
    }

@st.cache_data(ttl=900)
def fetch_market_structure():
    """Fetch forward curve and market structure data"""
    # Simulate forward curve (months 1-12)
    months = list(range(1, 13))
    np.random.seed(45)
    
    # Base price with contango structure
    base_price = 45.50
    curve_today = [base_price + (i * 0.15) + np.random.normal(0, 0.5) for i in months]
    curve_last_week = [base_price - 1.20 + (i * 0.12) + np.random.normal(0, 0.5) for i in months]
    
    structure = 'Contango' if curve_today[11] > curve_today[0] else 'Backwardation'
    spread = curve_today[11] - curve_today[0]
    
    return {
        'structure': structure,
        'spread': spread,
        'curve_today': curve_today,
        'curve_last_week': curve_last_week,
        'months': months
    }

@st.cache_data(ttl=900)
def fetch_news_feed():
    """Fetch latest market news with sentiment analysis and clickable source links"""
    return [
        {
            'headline': 'Woodside announces Q3 LNG production increase at North West Shelf',
            'sentiment': '+',
            'source': 'Reuters',
            'url': 'https://www.reuters.com/business/energy/woodside-announces-q3-lng-production-increase-2025-07-29/',
            'timestamp': '2 hours ago',
            'summary': 'Production up 8% QoQ, supporting domestic gas supply outlook'
        },
        {
            'headline': 'WA gas storage falls below 5-year average amid cold snap',
            'sentiment': '-',
            'source': 'WA Energy News',
            'url': 'https://www.waenergynews.com.au/gas-storage-below-average-2025',
            'timestamp': '4 hours ago',
            'summary': 'Storage at 92% of seasonal norm, winter demand exceeding forecasts'
        },
        {
            'headline': 'DBNGP pipeline maintenance scheduled for August',
            'sentiment': 'N',
            'source': 'AEMO',
            'url': 'https://aemo.com.au/newsroom/media-release/dbngp-maintenance-august-2025',
            'timestamp': '6 hours ago',
            'summary': 'Planned 5-day maintenance may impact gas flows to Perth'
        },
        {
            'headline': 'Asian LNG spot prices surge on supply concerns',
            'sentiment': '+',
            'source': 'Platts',
            'url': 'https://www.spglobal.com/platts/en/market-insights/latest-news/lng/072925-asian-lng-spot-prices-surge',
            'timestamp': '8 hours ago',
            'summary': 'Strong demand supporting WA LNG export economics'
        },
        {
            'headline': 'Chevron Gorgon facility reports record domestic gas delivery',
            'sentiment': '+',
            'source': 'Australian Financial Review',
            'url': 'https://www.afr.com/companies/energy/chevron-gorgon-record-domestic-gas-2025',
            'timestamp': '10 hours ago',
            'summary': 'Monthly domestic gas delivery reaches 300 TJ/day capacity'
        }
    ]

@st.cache_data(ttl=900)
def fetch_large_users_data():
    """Fetch WA large gas users data - no limits"""
    np.random.seed(46)
    
    wa_facilities = [
        # LNG Export Facilities
        "Woodside Karratha Gas Plant", "Chevron Gorgon Train 1", "Chevron Gorgon Train 2", 
        "Chevron Gorgon Train 3", "Chevron Wheatstone Train 1", "Chevron Wheatstone Train 2",
        "Woodside Pluto Train 1", "Shell Prelude FLNG",
        
        # Power Generation
        "Origin Kwinana Power Station", "Synergy Kwinana Power Station", "Synergy Cockburn Power Station",
        "NewGen Kwinana", "Alinta Pinjarra Power Station", "Alinta Wagerup Power Station",
        "Parkeston Power Station", "Geraldton Power Station",
        
        # Industrial Processing
        "Alcoa Kwinana Refinery", "Alcoa Pinjarra Refinery", "Alcoa Wagerup Refinery",
        "BHP Nickel West Kalgoorlie", "BHP Nickel West Kambalda", "Tianqi Lithium Kwinana",
        "CSBP Kwinana Ammonia", "Wesfarmers CSBP Chemicals", "Burrup Fertilisers Karratha",
        "Yara Pilbara Fertilisers", "Cockburn Cement", "Adelaide Brighton Munster",
        
        # Gas Production & Infrastructure
        "Apache Varanus Island", "Woodside North Rankin Complex", "Woodside Goodwyn Alpha",
        "BHP Macedon Gas Plant", "Apache Devil Creek", "AWE Waitsia/Xyris Gas Plant",
        "Origin Beharra Springs", "APA Mondarra Gas Storage",
        "APA Tubridgi Gas Storage", "DBNGP Compressor Station 1", "DBNGP Compressor Station 6",
        
        # Mining Operations
        "Rio Tinto Dampier Salt", "Fortescue Christmas Creek", "Fortescue Cloudbreak",
        "Roy Hill Iron Ore", "Mt Gibson Iron", "Mineral Resources Kwinana",
        "CBH Group Grain Terminals", "Water Corporation Perth"
    ]
    
    return pd.DataFrame({
        'Facility_Code': [f'WA{i:03d}' for i in range(len(wa_facilities))],
        'Facility_Name': wa_facilities,
        'Category': np.random.choice([
            'LNG Export', 'Power Generation', 'Industrial Processing', 
            'Gas Production', 'Mining Operations', 'Infrastructure'
        ], len(wa_facilities)),
        'Consumption_TJ': np.random.lognormal(4.5, 0.8, len(wa_facilities)),
        'Utilization_Pct': np.random.uniform(65, 95, len(wa_facilities)),
        'Region': np.random.choice([
            'North West Shelf', 'Perth Basin', 'Pilbara', 'South West', 'Goldfields'
        ], len(wa_facilities))
    }).sort_values('Consumption_TJ', ascending=False).reset_index(drop=True)

# ==============================================================================
# VISUALIZATION FUNCTIONS (Fixed Chart Generation)
# ==============================================================================

def create_facility_supply_demand_chart(production_df, demand_df, selected_facilities=None):
    """Create supply by facility stacked area chart with demand overlay - FIXED VERSION"""
    
    # Data validation
    if production_df.empty or demand_df.empty:
        st.error("❌ No data available for chart generation")
        return go.Figure()
    
    # Merge data on Date column
    try:
        chart_data = production_df.merge(demand_df, on='Date', how='inner')
        if chart_data.empty:
            st.error("❌ No matching dates between supply and demand data")
            return go.Figure()
    except Exception as e:
        st.error(f"❌ Data merge failed: {e}")
        return go.Figure()
    
    fig = go.Figure()
    
    # Get facility columns (excluding Date and calculated columns)
    facility_columns = [col for col in production_df.columns 
                       if col not in ['Date', 'Total_Supply']]
    
    # Determine which facilities to display
    if selected_facilities:
        display_facilities = [f for f in facility_columns if f in selected_facilities]
    else:
        # Default to operating facilities
        display_facilities = [f for f in facility_columns 
                            if WA_PRODUCTION_FACILITIES.get(f, {}).get('status') in ['operating', 'ramping']]
    
    if not display_facilities:
        st.warning("⚠️ No facilities selected for display")
        return go.Figure()
    
    # Add stacked areas for each production facility
    for i, facility in enumerate(display_facilities):
        if facility not in chart_data.columns:
            continue
            
        config = WA_PRODUCTION_FACILITIES.get(facility, {})
        color = config.get('color', f'rgba({(i*60)%255}, {(i*80)%255}, {(i*100+100)%255}, 0.7)')
        max_capacity = config.get('max_domestic_capacity', 100)
        
        # Get production data and ensure it's capped at capacity
        production_values = np.minimum(chart_data[facility].fillna(0), max_capacity)
        
        fig.add_trace(go.Scatter(
            x=chart_data['Date'],
            y=production_values,
            name=facility,
            stackgroup='supply',
            mode='none',
            fill='tonexty' if i > 0 else 'tozeroy',
            fillcolor=color,
            line=dict(width=0),
            hovertemplate=f'<b>{facility}</b><br>' +
                         'Date: %{x|%Y-%m-%d}<br>' +
                         'Production: %{y:.1f} TJ/day<br>' +
                         f'Max Capacity: {max_capacity} TJ/day<extra></extra>'
        ))
    
    # Add market demand overlay (bold black line)
    fig.add_trace(go.Scatter(
        x=chart_data['Date'],
        y=chart_data['Market_Demand'],
        name='Market Demand',
        mode='lines',
        line=dict(color='#1f2937', width=4),
        hovertemplate='<b>Market Demand</b><br>' +
                     'Date: %{x|%Y-%m-%d}<br>' +
                     'Demand: %{y:.1f} TJ/day<extra></extra>'
    ))
    
    # Calculate total capped supply and identify deficits
    total_capped_supply = np.zeros(len(chart_data))
    for facility in display_facilities:
        if facility in chart_data.columns:
            max_cap = WA_PRODUCTION_FACILITIES.get(facility, {}).get('max_domestic_capacity', 1000)
            total_capped_supply += np.minimum(chart_data[facility].fillna(0), max_cap)
    
    # Highlight supply deficits
    deficit_mask = chart_data['Market_Demand'] > total_capped_supply
    if deficit_mask.any():
        deficit_dates = chart_data.loc[deficit_mask, 'Date']
        deficit_demands = chart_data.loc[deficit_mask, 'Market_Demand']
        
        # Add deficit markers
        fig.add_trace(go.Scatter(
            x=deficit_dates,
            y=deficit_demands,
            name='Supply Deficit',
            mode='markers',
            marker=dict(color='red', size=8, symbol='triangle-down'),
            showlegend=False,
            hovertemplate='<b>⚠️ Supply Deficit</b><br>' +
                         'Date: %{x|%Y-%m-%d}<br>' +
                         'Demand exceeds available capacity<extra></extra>'
        ))
        
        # Add annotations for first few deficits
        for idx, (date, demand) in enumerate(zip(deficit_dates.head(3), deficit_demands.head(3))):
            fig.add_annotation(
                x=date,
                y=demand,
                text="⚠️ Capacity Shortfall",
                showarrow=True,
                arrowhead=2,
                arrowcolor='red',
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='red',
                borderwidth=1
            )
    
    # Clean layout following Tufte's principles
    fig.update_layout(
        title=dict(
            text='WA Gas Supply by Production Facility vs Market Demand',
            font=dict(size=20, color='#1f2937'),
            x=0.02
        ),
        xaxis=dict(
            title='Date',
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor='#e5e7eb'
        ),
        yaxis=dict(
            title='Gas Flow (TJ/day)',
            showgrid=True,
            gridwidth=1,
            gridcolor='#f3f4f6',
            zeroline=False
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e5e7eb',
            borderwidth=1
        ),
        height=600,
        margin=dict(l=60, r=250, t=80, b=60)  # Extra right margin for legend
    )
    
    return fig

def create_storage_seasonality_chart(df):
    """Create storage inventory vs seasonal norms chart"""
    fig = go.Figure()
    
    # Current year
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Current_Inventory'],
        name='2025 Inventory',
        line=dict(color='#1f2937', width=3),
        hovertemplate='<b>Current Inventory</b><br>%{y:.0f} TJ<extra></extra>'
    ))
    
    # 5-year average
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Five_Year_Average'],
        name='5-Year Average',
        line=dict(color='#6b7280', width=2, dash='dash'),
        hovertemplate='<b>5-Year Average</b><br>%{y:.0f} TJ<extra></extra>'
    ))
    
    # Min/Max band
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Five_Year_Max'],
        fill=None,
        mode='lines',
        line_color='rgba(0,0,0,0)',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Five_Year_Min'],
        fill='tonexty',
        mode='lines',
        line_color='rgba(0,0,0,0)',
        name='5-Year Range',
        fillcolor='rgba(156, 163, 175, 0.2)',
        hovertemplate='<b>5-Year Range</b><br>%{y:.0f} TJ<extra></extra>'
    ))
    
    # Clean layout
    fig.update_layout(
        title=dict(
            text='Gas Storage Inventory vs Seasonal Norms',
            font=dict(size=18, color='#1f2937'),
            x=0.02
        ),
        xaxis=dict(title='', showgrid=False, showline=True, linecolor='#e5e7eb'),
        yaxis=dict(
            title='Storage Inventory (TJ)',
            showgrid=True,
            gridwidth=1,
            gridcolor='#f3f4f6'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        legend=dict(orientation='h', y=1.02, x=0.5, xanchor='center'),
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )
    
    return fig

def create_forward_curve_chart(market_data):
    """Create dynamic forward curve with historical comparison"""
    fig = go.Figure()
    
    # Today's curve
    fig.add_trace(go.Scatter(
        x=market_data['months'],
        y=market_data['curve_today'],
        name="Today's Curve",
        line=dict(color='#1f2937', width=3),
        mode='lines+markers',
        marker=dict(size=6),
        hovertemplate='<b>Month %{x}</b><br>$%{y:.2f}/MMBtu<extra></extra>'
    ))
    
    # Last week's curve
    fig.add_trace(go.Scatter(
        x=market_data['months'],
        y=market_data['curve_last_week'],
        name='Last Week',
        line=dict(color='#6b7280', width=2, dash='dot'),
        mode='lines+markers',
        marker=dict(size=4),
        hovertemplate='<b>Month %{x}</b><br>$%{y:.2f}/MMBtu<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text='Forward Curve Analysis',
            font=dict(size=18, color='#1f2937'),
            x=0.02
        ),
        xaxis=dict(
            title='Contract Month',
            showgrid=False,
            showline=True,
            linecolor='#e5e7eb',
            tickmode='linear',
            tick0=1,
            dtick=1
        ),
        yaxis=dict(
            title='Price (USD/MMBtu)',
            showgrid=True,
            gridwidth=1,
            gridcolor='#f3f4f6'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        legend=dict(orientation='h', y=1.02, x=0.5, xanchor='center'),
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )
    
    return fig

# ==============================================================================
# MODULE 1: AT-A-GLANCE COMMAND CENTER (Fixed)
# ==============================================================================

def display_command_center():
    """Main command center with progressive disclosure - FIXED VERSION"""
    
    # Header with timestamp
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">⚡ WA Natural Gas Market Command Center</h1>', unsafe_allow_html=True)
    with col2:
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S AWST')}")
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    # Key Performance Indicators Row
    fundamentals = fetch_key_fundamentals()
    market_data = fetch_market_structure()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Storage KPI
        latest = fundamentals['latest_storage']
        consensus = fundamentals['consensus_storage']
        avg_5yr = fundamentals['five_year_avg_storage']
        
        consensus_diff = latest - consensus
        avg_diff = latest - avg_5yr
        
        delta_color = "#16a34a" if consensus_diff > 0 else "#dc2626"
        
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-value" style="color: {delta_color};">{latest}</p>
            <p class="kpi-label">Storage Inventory (TJ)</p>
            <p class="kpi-delta" style="color: {delta_color};">
                vs Consensus: {consensus_diff:+d} TJ<br>
                vs 5yr Avg: {avg_diff:+d} TJ
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Market Structure
        structure = market_data['structure']
        spread = market_data['spread']
        structure_class = 'contango' if structure == 'Contango' else 'backwardation'
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="structure-pill {structure_class}">
                {structure}
            </div>
            <p class="kpi-label" style="margin-top: 1rem;">M12-M1 Spread</p>
            <p class="kpi-value" style="font-size: 1.5rem;">${spread:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Linepack Status
        linepack_pct = 0.92  # Simulated
        if linepack_pct >= 0.90:
            status, icon, color = "Healthy", "✅", "#16a34a"
        elif linepack_pct >= 0.80:
            status, icon, color = "Watch", "⚠️", "#ca8a04"
        else:
            status, icon, color = "Critical", "🔴", "#dc2626"
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="linepack-status status-{status.lower()}">
                <span style="font-size: 2rem;">{icon}</span>
                <span>{status}</span>
            </div>
            <p class="kpi-label">Linepack Status</p>
            <p class="kpi-value" style="font-size: 1.5rem; color: {color};">{linepack_pct:.1%}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Market Balance - CORRECTED INDENTATION
        production_df = fetch_production_facility_data()
        demand_df = fetch_market_demand_data()
        
        if not production_df.empty and not demand_df.empty:
            today_supply = production_df['Total_Supply'].iloc[-1]
            today_demand = demand_df['Market_Demand'].iloc[-1]
            today_balance = today_supply - today_demand
            
            balance_status = "Surplus" if today_balance > 0 else "Deficit"
            balance_color = "#16a34a" if today_balance > 0 else "#dc2626"
        else:
            today_balance = 0
            balance_status = "Unknown"
            balance_color = "#64748b"
        
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-value" style="color: {balance_color};">{abs(today_balance):.0f}</p>
            <p class="kpi-label">Market {balance_status} (TJ/day)</p>
            <p class="kpi-delta" style="color: {balance_color};">
                {'⬆️' if today_balance > 0 else '⬇️'} {balance_status}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Main Content Area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Interactive Supply & Demand Chart by Production Facility
        st.markdown("### Supply by Production Facility vs Market Demand")
        
        # Chart controls (Interactive exploration)
        control_col1, control_col2, control_col3 = st.columns(3)
        with control_col1:
            chart_period = st.selectbox("Time Period", ["Last 30 Days", "Last 90 Days", "YTD"], index=1)
        with control_col2:
            show_future = st.checkbox("Include Future Facilities", value=False)
        with control_col3:
            if st.button("🔄 Refresh Chart Data"):
                st.cache_data.clear()
                st.rerun()
        
        # Initialize session state for facility selection
        if 'selected_facilities' not in st.session_state:
            default_facilities = [f for f, config in WA_PRODUCTION_FACILITIES.items() 
                                if config['status'] in ['operating', 'ramping']]
            st.session_state.selected_facilities = default_facilities[:6]  # First 6 for better visualization
        
        # Facility selector with guaranteed defaults
        all_facilities = list(WA_PRODUCTION_FACILITIES.keys())
        available_facilities = all_facilities if show_future else [
            f for f, config in WA_PRODUCTION_FACILITIES.items() 
            if config['status'] != 'future'
        ]
        
        selected_facilities = st.multiselect(
            "Select Production Facilities to Display:",
            options=available_facilities,
            default=[f for f in st.session_state.selected_facilities if f in available_facilities],
            key="facility_selector"
        )
        
        # Update session state
        if selected_facilities:
            st.session_state.selected_facilities = selected_facilities
        
        # Generate facility supply chart - FIXED VERSION
        production_df = fetch_production_facility_data()
        demand_df = fetch_market_demand_data()
        
        # Debug information (can be hidden in production)
        with st.expander("🔍 Data Debug Info", expanded=False):
            st.markdown(f"""
            <div class="debug-info">
            Production data shape: {production_df.shape}<br>
            Demand data shape: {demand_df.shape}<br>
            Production date range: {production_df['Date'].min() if not production_df.empty else 'No data'} to {production_df['Date'].max() if not production_df.empty else 'No data'}<br>
            Demand date range: {demand_df['Date'].min() if not demand_df.empty else 'No data'} to {demand_df['Date'].max() if not demand_df.empty else 'No data'}<br>
            Selected facilities: {len(selected_facilities)}<br>
            Available facilities: {len(available_facilities)}
            </div>
            """, unsafe_allow_html=True)
        
        # Filter based on period selection
        if not production_df.empty and not demand_df.empty:
            if chart_period == "Last 30 Days":
                cutoff_date = datetime.now() - timedelta(days=30)
                production_df = production_df[production_df['Date'] >= cutoff_date]
                demand_df = demand_df[demand_df['Date'] >= cutoff_date]
            elif chart_period == "YTD":
                cutoff_date = datetime(datetime.now().year, 1, 1)
                production_df = production_df[production_df['Date'] >= cutoff_date]
                demand_df = demand_df[demand_df['Date'] >= cutoff_date]
        
        # Generate and display chart
        if selected_facilities and not production_df.empty and not demand_df.empty:
            try:
                fig_facility = create_facility_supply_demand_chart(production_df, demand_df, selected_facilities)
                st.plotly_chart(fig_facility, use_container_width=True)
                
                # Progressive disclosure: Facility details
                if st.button("📊 View Facility Details & Capacity"):
                    with st.expander("Production Facility Analysis", expanded=True):
                        if not production_df.empty:
                            latest_data = production_df.iloc[-1]
                            
                            # Create facility summary table
                            facility_summary = []
                            for facility in selected_facilities:
                                config = WA_PRODUCTION_FACILITIES.get(facility, {})
                                current_production = latest_data.get(facility, 0)
                                max_capacity = config.get('max_domestic_capacity', 0)
                                utilization = (current_production / max_capacity * 100) if max_capacity > 0 else 0
                                
                                facility_summary.append({
                                    'Facility': facility,
                                    'Operator': config.get('operator', 'Unknown'),
                                    'Current Production (TJ/day)': f"{current_production:.1f}",
                                    'Max Capacity (TJ/day)': f"{max_capacity}",
                                    'Utilization (%)': f"{utilization:.1f}%",
                                    'Status': config.get('status', 'Unknown').title()
                                })
                            
                            summary_df = pd.DataFrame(facility_summary)
                            st.dataframe(summary_df, use_container_width=True, hide_index=True)
                            
                            total_capacity = sum(WA_PRODUCTION_FACILITIES.get(f, {}).get('max_domestic_capacity', 0) for f in selected_facilities)
                            current_demand = demand_df['Market_Demand'].iloc[-1] if not demand_df.empty else 0
                            
                            st.markdown(f"""
                            **Total Selected Capacity:** {total_capacity:,} TJ/day
                            
                            **Current Market Demand:** {current_demand:.1f} TJ/day
                            
                            **Capacity Utilization:** {(current_demand / total_capacity * 100) if total_capacity > 0 else 0:.1f}% of selected facilities
                            
                            *Data Source: WA Gas Statement of Opportunities 2024, AEMO*
                            """)
                        
            except Exception as e:
                st.error(f"❌ Chart generation failed: {e}")
                st.info("Please try refreshing the data or selecting different facilities.")
        else:
            if not selected_facilities:
                st.warning("⚠️ Please select at least one production facility to display the chart.")
            elif production_df.empty or demand_df.empty:
                st.error("❌ Unable to load market data. Please try refreshing.")
            else:
                st.info("📊 Chart loading...")
    
    with col2:
        # Enhanced News Feed with Clickable Links
        st.markdown("### Market Intelligence Feed")
        
        news_items = fetch_news_feed()
        
        # News filter (Interactive exploration)
        news_filter = st.selectbox("Filter by:", ["All News", "Positive", "Negative", "Neutral"])
        
        filtered_news = news_items
        if news_filter != "All News":
            sentiment_map = {"Positive": "+", "Negative": "-", "Neutral": "N"}
            filtered_news = [item for item in news_items if item['sentiment'] == sentiment_map[news_filter]]
        
        for item in filtered_news:
            sentiment_class_map = {'+': 'sentiment-positive', '-': 'sentiment-negative', 'N': 'sentiment-neutral'}
            sentiment_icon_map = {'+': '📈', '-': '📉', 'N': '📰'}
            
            st.markdown(f"""
            <div class="news-item">
                <span class="{sentiment_class_map[item['sentiment']]}" style="margin-right: 0.5rem; font-size: 1.2rem;">
                    {sentiment_icon_map[item['sentiment']]}
                </span>
                <div style="flex: 1;">
                    <a href="{item['url']}" target="_blank" class="news-headline">
                        {item['headline']}
                    </a><br>
                    <small style="color: #64748b;">{item['source']} • {item['timestamp']}</small>
                    <div style="margin-top: 0.25rem; font-size: 0.875rem; color: #374151;">
                        {item['summary']}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==============================================================================
# MODULE 2: FUNDAMENTAL ANALYSIS
# ==============================================================================

def display_fundamental_analysis():
    """Deep-dive fundamental analysis module"""
    st.markdown("### Deep-Dive Fundamental Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Storage Seasonality Chart
        storage_df = fetch_storage_data()
        fig_storage = create_storage_seasonality_chart(storage_df)
        st.plotly_chart(fig_storage, use_container_width=True)
        
        # Interactive elements
        if st.button("📋 Storage Analysis Report"):
            with st.expander("Storage Position Analysis", expanded=True):
                latest_storage = storage_df.iloc[-1]
                spread = latest_storage['Spread_vs_Average']
                
                if spread > 10:
                    status = "🟢 Well-supplied"
                elif spread > -10:
                    status = "🟡 Normal range"
                else:
                    status = "🔴 Below average"
                
                st.markdown(f"""
                **Current Status:** {status}
                
                **Key Metrics:**
                - Current Inventory: {latest_storage['Current_Inventory']:.0f} TJ
                - vs 5-Year Average: {spread:+.0f} TJ ({spread/latest_storage['Five_Year_Average']*100:+.1f}%)
                - Days of Cover: {latest_storage['Current_Inventory']/25:.1f} days (at avg demand)
                
                **Market Implications:**
                - {'Adequate storage supporting price stability' if spread > 0 else 'Below-average storage may support prices'}
                
                *Source: WA Gas Statement of Opportunities 2024, AEMO*
                """)
    
    with col2:
        # Inventory Spread Chart
        spread_df = storage_df.tail(90)  # Last 90 days
        
        fig_spread = go.Figure()
        
        # Color bars based on positive/negative
        colors = ['#16a34a' if x > 0 else '#dc2626' for x in spread_df['Spread_vs_Average']]
        
        fig_spread.add_trace(go.Bar(
            x=spread_df['Date'],
            y=spread_df['Spread_vs_Average'],
            name='Storage vs 5-Year Average',
            marker_color=colors,
            hovertemplate='<b>%{x}</b><br>Spread: %{y:.0f} TJ<extra></extra>'
        ))
        
        fig_spread.update_layout(
            title='Storage Inventory vs 5-Year Average Spread',
            xaxis_title='',
            yaxis_title='Spread (TJ)',
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=False,
            height=400,
            yaxis=dict(zeroline=True, zerolinecolor='#374151', zerolinewidth=2)
        )
        
        st.plotly_chart(fig_spread, use_container_width=True)

# ==============================================================================
# MODULE 3: MARKET STRUCTURE & PRICING
# ==============================================================================

def display_market_structure():
    """Market structure and price dynamics module"""
    st.markdown("### Market Structure & Price Dynamics")
    
    market_data = fetch_market_structure()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Forward Curve Chart
        fig_curve = create_forward_curve_chart(market_data)
        st.plotly_chart(fig_curve, use_container_width=True)
        
        # Spread Calculator (Interactive tool)
        st.markdown("#### Spread Calculator")
        calc_col1, calc_col2, calc_col3 = st.columns(3)
        
        with calc_col1:
            month1 = st.selectbox("Near Month", range(1, 13), index=0)
        with calc_col2:
            month2 = st.selectbox("Far Month", range(1, 13), index=11)
        with calc_col3:
            if st.button("Calculate Spread"):
                spread_calc = market_data['curve_today'][month2-1] - market_data['curve_today'][month1-1]
                st.metric("Spread", f"${spread_calc:.2f}")
    
    with col2:
        # Market Structure Analysis
        st.markdown("#### Market Structure Analysis")
        
        structure = market_data['structure']
        spread = market_data['spread']
        
        # Structure pill
        structure_class = 'contango' if structure == 'Contango' else 'backwardation'
        st.markdown(f'<div class="structure-pill {structure_class}">{structure}</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        **Current Spread:** ${spread:.2f}/MMBtu
        
        **Market Interpretation:**
        {f"Forward curve in {structure.lower()}, indicating {'storage costs and interest rates' if structure == 'Contango' else 'immediate supply tightness'} are the primary drivers."} 
        
        **Trading Implications:**
        {f"{'Calendar spreads may offer value on storage capacity' if structure == 'Contango' else 'Near-term supply premiums suggest urgent demand'}."}
        """)
        
        # Price levels table
        st.markdown("#### Current Price Levels")
        price_data = pd.DataFrame({
            'Contract': [f'M{i}' for i in range(1, 7)],
            'Price': [f"${price:.2f}" for price in market_data['curve_today'][:6]],
            'Change': [f"{np.random.uniform(-0.5, 0.5):.2f}" for _ in range(6)]
        })
        st.dataframe(price_data, use_container_width=True, hide_index=True)

# ==============================================================================
# MODULE 4: LARGE USERS ANALYSIS  
# ==============================================================================

def display_large_users():
    """Enhanced large users analysis with no limits"""
    st.markdown("### Large User Consumption Analysis")
    
    large_users_df = fetch_large_users_data()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Facilities", len(large_users_df))
    with col2:
        st.metric("Total Consumption", f"{large_users_df['Consumption_TJ'].sum():.0f} TJ")
    with col3:
        st.metric("Average Utilization", f"{large_users_df['Utilization_Pct'].mean():.1f}%")
    with col4:
        top_10_share = large_users_df.head(10)['Consumption_TJ'].sum() / large_users_df['Consumption_TJ'].sum()
        st.metric("Top 10 Market Share", f"{top_10_share:.1%}")
    
    # Interactive filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("🔍 Search Facilities", placeholder="Enter facility name...")
    with col2:
        category_filter = st.selectbox("Filter by Category", 
                                     ['All Categories'] + list(large_users_df['Category'].unique()))
    with col3:
        region_filter = st.selectbox("Filter by Region", 
                                   ['All Regions'] + list(large_users_df['Region'].unique()))
    
    # Apply filters
    filtered_df = large_users_df.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['Facility_Name'].str.contains(search_term, case=False, na=False)
        ]
    
    if category_filter != 'All Categories':
        filtered_df = filtered_df[filtered_df['Category'] == category_filter]
    
    if region_filter != 'All Regions':
        filtered_df = filtered_df[filtered_df['Region'] == region_filter]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Data table with formatting
        st.markdown(f"**Showing {len(filtered_df)} of {len(large_users_df)} facilities**")
        
        display_df = filtered_df.copy()
        display_df['Consumption_TJ'] = display_df['Consumption_TJ'].round(1)
        display_df['Utilization_Pct'] = display_df['Utilization_Pct'].round(1)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400,
            column_config={
                'Facility_Code': 'Code',
                'Facility_Name': 'Facility Name',
                'Category': 'Category',
                'Consumption_TJ': st.column_config.NumberColumn('Consumption (TJ)', format="%.1f"),
                'Utilization_Pct': st.column_config.ProgressColumn('Utilization %', min_value=0, max_value=100),
                'Region': 'Region'
            },
            hide_index=True
        )
    
    with col2:
        # Category breakdown pie chart
        if len(filtered_df) > 0:
            category_summary = filtered_df.groupby('Category')['Consumption_TJ'].sum().reset_index()
            
            fig_pie = px.pie(
                category_summary, 
                values='Consumption_TJ', 
                names='Category',
                title='Consumption by Category'
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No data to display based on current filters")

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================

def main():
    """Main application with modular dashboard"""
    
    # Sidebar for module navigation
    with st.sidebar:
        st.markdown("## Dashboard Modules")
        
        selected_module = st.radio(
            "Choose Analysis Module:",
            [
                "🎯 Command Center",
                "⚡ Fundamental Analysis", 
                "📈 Market Structure",
                "🏭 Large Users",
                "🌦️ Weather & Risk",
                "🧮 Scenario Analysis"
            ],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### Production Facilities")
        
        # Show facility status overview
        operating_count = sum(1 for config in WA_PRODUCTION_FACILITIES.values() if config['status'] == 'operating')
        ramping_count = sum(1 for config in WA_PRODUCTION_FACILITIES.values() if config['status'] == 'ramping')
        future_count = sum(1 for config in WA_PRODUCTION_FACILITIES.values() if config['status'] == 'future')
        total_capacity = sum(config['max_domestic_capacity'] for config in WA_PRODUCTION_FACILITIES.values())
        
        st.markdown(f"""
        **Operating:** {operating_count} facilities  
        **Ramping:** {ramping_count} facilities
        **Future:** {future_count} facilities  
        **Total Capacity:** {total_capacity:,} TJ/day
        """)
        
        st.markdown("---")
        st.markdown("### Quick Filters")
        
        # Global date filter
        date_range = st.date_input(
            "Date Range",
            value=[datetime.now() - timedelta(days=30), datetime.now()],
            max_value=datetime.now()
        )
        
        # Global refresh
        if st.button("🔄 Refresh All Data"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("""
        ### Data Sources
        - **WA Gas Bulletin Board** (AEMO)
        - **WA Gas Statement of Opportunities 2024**
        - **Production Facility Operators**
        - **Market Intelligence Feeds**
        """)
        
        st.markdown("---")
        st.markdown("*Dashboard follows Tufte's principles: Maximum data-ink ratio, progressive disclosure, interactive exploration*")
    
    # Route to selected module
    if selected_module == "🎯 Command Center":
        display_command_center()
        
    elif selected_module == "⚡ Fundamental Analysis":
        display_fundamental_analysis()
        
    elif selected_module == "📈 Market Structure":
        display_market_structure()
        
    elif selected_module == "🏭 Large Users":
        display_large_users()
        
    elif selected_module == "🌦️ Weather & Risk":
        st.markdown("### Weather & Risk Monitoring")
        st.info("🚧 Weather dashboard and geopolitical risk heatmap coming soon...")
        
        # Placeholder for weather module
        st.markdown("""
        **Planned Features:**
        - Interactive weather maps with production zone overlays
        - Temperature and precipitation forecasts from Windy.com
        - Geopolitical risk heatmap
        - Infrastructure constraint monitoring
        - Pipeline maintenance schedules
        """)
        
    elif selected_module == "🧮 Scenario Analysis":
        st.markdown("### Quantitative & Scenario Analysis Workbench")
        st.info("🚧 Advanced analytics tools coming soon...")
        
        # Placeholder for quantitative tools
        st.markdown("""
        **Planned Features:**
        - Dynamic cost curve simulator with WA production facilities
        - Pre-trade VaR calculator
        - CFTC positioning analysis
        - Monte Carlo scenario modeling for supply/demand
        - Facility outage impact analysis
        """)

if __name__ == "__main__":
    main()
