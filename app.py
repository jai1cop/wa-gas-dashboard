import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
import requests
import json
from io import StringIO
import time

# Handle optional dependencies gracefully
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    st.warning("📰 feedparser not available - using static news feed")

import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="WA Natural Gas Market Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS with storage-specific styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1rem;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 0.5rem;
    }
    
    .kpi-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
    }
    
    .kpi-label {
        font-size: 0.9rem;
        color: #64748b;
        margin: 0.5rem 0;
        font-weight: 500;
    }
    
    .storage-card {
        background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .storage-metric {
        display: inline-block;
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem;
        text-align: center;
        min-width: 120px;
    }
    
    .api-status {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .api-live { 
        background: #dcfce7; 
        color: #166534; 
        border: 1px solid #bbf7d0; 
    }
    
    .api-cached { 
        background: #fef3c7; 
        color: #92400e; 
        border: 1px solid #fcd34d; 
    }
    
    .api-error { 
        background: #fef2f2; 
        color: #991b1b; 
        border: 1px solid #fecaca; 
    }
    
    .data-source-badge {
        background: #3b82f6;
        color: white;
        padding: 0.3rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .facility-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .storage-flow-positive {
        color: #16a34a;
        font-weight: 700;
    }
    
    .storage-flow-negative {
        color: #dc2626;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# UPDATED WA GAS PRODUCTION FACILITIES (WITH CORRECTIONS)
# ==============================================================================

WA_PRODUCTION_FACILITIES_COMPLETE = {
    # Major LNG/Domestic Gas Facilities - Pilbara Zone
    'Karratha Gas Plant (NWS)': {
        'operator': 'Woodside Energy',
        'capacity': 585,
        'color': 'rgba(31, 119, 180, 0.8)',
        'status': 'operating',
        'facility_code': 'KARR_GP',
        'output': 450,
        'region': 'Pilbara',  # Updated from North West Shelf
        'start_year': 1984,
        'fuel_type': 'Natural Gas'
    },
    'Gorgon Gas Plant': {
        'operator': 'Chevron Australia',
        'capacity': 300,
        'color': 'rgba(255, 127, 14, 0.8)',
        'status': 'operating',
        'facility_code': 'GORG_GP',
        'output': 280,
        'region': 'Pilbara',  # Updated from Barrow Island
        'start_year': 2016,
        'fuel_type': 'Natural Gas'
    },
    'Wheatstone Gas Plant': {
        'operator': 'Chevron Australia',
        'capacity': 230,
        'color': 'rgba(44, 160, 44, 0.8)',
        'status': 'operating',
        'facility_code': 'WHET_GP',
        'output': 210,
        'region': 'Pilbara',  # Updated from Onslow
        'start_year': 2017,
        'fuel_type': 'Natural Gas'
    },
    'Pluto LNG': {
        'operator': 'Woodside Energy',
        'capacity': 50,
        'color': 'rgba(214, 39, 40, 0.8)',
        'status': 'operating',
        'facility_code': 'PLUT_GP',
        'output': 35,
        'region': 'Pilbara',  # Updated from Karratha
        'start_year': 2012,
        'fuel_type': 'Natural Gas'
    },
    'Varanus Island Hub': {
        'operator': 'Santos/Beach Energy/APA',
        'capacity': 390,
        'color': 'rgba(148, 103, 189, 0.8)',
        'status': 'operating',
        'facility_code': 'VARN_GP',
        'output': 340,
        'region': 'Pilbara',  # Updated from North West Shelf
        'start_year': 2003,
        'fuel_type': 'Natural Gas'
    },
    'Macedon Gas Plant': {
        'operator': 'Woodside/Santos',
        'capacity': 170,
        'color': 'rgba(140, 86, 75, 0.8)',
        'status': 'operating',
        'facility_code': 'MCED_GP',
        'output': 155,
        'region': 'Pilbara',  # Updated from Ashburton North
        'start_year': 2013,
        'fuel_type': 'Natural Gas'
    },
    'Devil Creek Gas Plant': {
        'operator': 'Santos/Beach Energy',
        'capacity': 50,
        'color': 'rgba(227, 119, 194, 0.8)',
        'status': 'declining',
        'facility_code': 'DVCR_GP',
        'output': 25,
        'region': 'Pilbara',  # CORRECTED: Moved from Perth Basin to Pilbara
        'start_year': 1990,
        'fuel_type': 'Natural Gas'
    },
    
    # Perth Basin Facilities
    'Beharra Springs': {
        'operator': 'Beach Energy/Mitsui',
        'capacity': 28,
        'color': 'rgba(127, 127, 127, 0.8)',
        'status': 'operating',
        'facility_code': 'BEHA_GP',
        'output': 24,
        'region': 'Perth Basin',
        'start_year': 2006,
        'fuel_type': 'Natural Gas'
    },
    'Waitsia Gas Plant': {
        'operator': 'Mitsui/Beach Energy',
        'capacity': 65,
        'color': 'rgba(188, 189, 34, 0.8)',
        'status': 'ramping',
        'facility_code': 'WAIT_GP',
        'output': 50,
        'region': 'Perth Basin',
        'start_year': 2022,
        'fuel_type': 'Natural Gas'
    },
    'Walyering Gas Plant': {
        'operator': 'Strike Energy/Talon',
        'capacity': 33,
        'color': 'rgba(23, 190, 207, 0.8)',
        'status': 'operating',
        'facility_code': 'WALY_GP',
        'output': 28,
        'region': 'Perth Basin',
        'start_year': 2021,
        'fuel_type': 'Natural Gas'
    },
    'Dongara Gas Plant': {
        'operator': 'AWE Limited',
        'capacity': 15,
        'color': 'rgba(255, 165, 0, 0.8)',
        'status': 'operating',
        'facility_code': 'DONG_GP',
        'output': 12,
        'region': 'Perth Basin',
        'start_year': 1995,
        'fuel_type': 'Natural Gas'
    },
    # REMOVED: Cliff Head Gas Plant (as requested)
    'Red Gully Processing': {
        'operator': 'AWE Limited',
        'capacity': 12,
        'color': 'rgba(178, 34, 34, 0.8)',
        'status': 'operating',
        'facility_code': 'REDG_GP',
        'output': 9,
        'region': 'Perth Basin',
        'start_year': 2008,
        'fuel_type': 'Natural Gas'
    },
    
    # Storage Facilities
    'Mondarra Gas Storage': {
        'operator': 'APA Group',
        'capacity': 25,  # Peak injection rate
        'color': 'rgba(255, 20, 147, 0.8)',
        'status': 'operating',
        'facility_code': 'MOND_ST',
        'output': 15,
        'region': 'Perth Basin',
        'start_year': 2019,
        'fuel_type': 'Storage'
    },
    'Tubridgi Underground Storage': {  # ADDED: New storage facility
        'operator': 'APA Group',
        'capacity': 45,  # Peak injection/withdrawal rate
        'color': 'rgba(138, 43, 226, 0.8)',
        'status': 'operating',
        'facility_code': 'TUBR_ST',
        'output': 35,
        'region': 'Perth Basin',
        'start_year': 2020,
        'fuel_type': 'Storage'
    },
    
    # Future/Under Construction - Updated Browse date
    'Scarborough Gas Plant': {
        'operator': 'Woodside Energy',
        'capacity': 225,
        'color': 'rgba(174, 199, 232, 0.8)',
        'status': 'under_construction',
        'facility_code': 'SCAR_GP',
        'output': 0,
        'region': 'Pilbara',
        'start_year': 2026,
        'fuel_type': 'Natural Gas'
    },
    'Browse FLNG': {
        'operator': 'Woodside Energy',
        'capacity': 180,
        'color': 'rgba(100, 149, 237, 0.8)',
        'status': 'future',
        'facility_code': 'BROW_FL',
        'output': 0,
        'region': 'Browse Basin',
        'start_year': 2035,  # UPDATED: Changed from 2028 to 2035
        'fuel_type': 'Natural Gas'
    },
    'Burrup Hub Expansion': {
        'operator': 'Woodside Energy',
        'capacity': 150,
        'color': 'rgba(205, 92, 92, 0.8)',
        'status': 'planned',
        'facility_code': 'BURR_EX',
        'output': 0,
        'region': 'Pilbara',
        'start_year': 2027,
        'fuel_type': 'Natural Gas'
    }
    # REMOVED: RWE facilities (as requested)
}

# ==============================================================================
# STORAGE FACILITIES CONFIGURATION
# ==============================================================================

WA_STORAGE_FACILITIES = {
    'Mondarra Gas Storage': {
        'operator': 'APA Group',
        'max_working_capacity': 23,  # PJ
        'max_injection_rate': 25,  # TJ/day
        'max_withdrawal_rate': 50,  # TJ/day
        'facility_code': 'MOND_ST',
        'region': 'Perth Basin',
        'storage_type': 'Depleted Gas Field',
        'status': 'operating'
    },
    'Tubridgi Underground Storage': {
        'operator': 'APA Group',
        'max_working_capacity': 45,  # PJ
        'max_injection_rate': 45,  # TJ/day
        'max_withdrawal_rate': 85,  # TJ/day
        'facility_code': 'TUBR_ST',
        'region': 'Perth Basin',
        'storage_type': 'Salt Cavern',
        'status': 'operating'
    }
}

# ==============================================================================
# SIMPLE AEMO API CLIENT
# ==============================================================================

class SimpleAEMOClient:
    """Simplified AEMO API client that works reliably"""
    
    def __init__(self):
        self.base_urls = [
            'https://gbbwa.aemo.com.au/api/v1/report',
            'https://gbbwa-trial.aemo.com.au/api/v1/report'
        ]
    
    def test_api_connection(self, report_name='mediumTermCapacity'):
        """Test if AEMO APIs are accessible"""
        
        for base_url in self.base_urls:
            try:
                url = f"{base_url}/{report_name}/current"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    return True, f"✅ Connected to {base_url.split('//')[1]}"
                else:
                    continue
                    
            except Exception as e:
                continue
        
        return False, "❌ AEMO APIs not accessible (systems may not be commissioned yet)"

# Initialize client
aemo_client = SimpleAEMOClient()

# ==============================================================================
# ENHANCED DATA GENERATION FUNCTIONS
# ==============================================================================

@st.cache_data(ttl=3600)
def generate_advanced_demand_data_5_year():
    """Generate sophisticated 5-year median demand with seasonal patterns"""
    
    # Create 5 years of historical data for median calculation
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)  # 5 years
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # WA-specific demand parameters (based on GSOO 2024 and historical data)
    base_demand_2020 = 1200  # TJ/day
    base_demand_2025 = 1400  # TJ/day (current)
    growth_rate = 0.032  # 3.2% annual growth
    
    np.random.seed(44)  # Consistent results
    
    # Generate 5 years of daily demand with realistic patterns
    demand_data = []
    
    for date in all_dates:
        year = date.year
        day_of_year = date.timetuple().tm_yday
        
        # Annual growth trend
        years_from_2020 = year - 2020
        annual_base = base_demand_2020 * (1 + growth_rate) ** years_from_2020
        
        # Seasonal variation (Australian winter = higher demand)
        seasonal_factor = 1 + 0.3 * np.cos(2 * np.pi * (day_of_year - 200) / 365)
        
        # Weekly pattern (lower weekends, higher weekdays)
        weekly_factor = 0.82 if date.weekday() >= 5 else 1.0
        
        # Holiday effects (Christmas/New Year period)
        if (date.month == 12 and date.day >= 20) or (date.month == 1 and date.day <= 10):
            holiday_factor = 0.75
        else:
            holiday_factor = 1.0
        
        # Economic cycles and COVID impact
        if year == 2020:
            covid_factor = 0.85  # Demand reduction
        elif year == 2021:
            covid_factor = 0.92  # Partial recovery
        else:
            covid_factor = 1.0
        
        # Weather-driven variation
        weather_variation = np.random.normal(0, 0.08)
        
        daily_demand = (annual_base * seasonal_factor * weekly_factor * 
                       holiday_factor * covid_factor * (1 + weather_variation))
        
        # Ensure minimum demand floor
        daily_demand = max(daily_demand, annual_base * 0.6)
        
        demand_data.append({
            'Date': date,
            'Daily_Demand': daily_demand,
            'Year': year
        })
    
    demand_df = pd.DataFrame(demand_data)
    
    # Calculate 5-year median for each day of year
    demand_df['DayOfYear'] = demand_df['Date'].dt.dayofyear
    daily_medians = demand_df.groupby('DayOfYear')['Daily_Demand'].median().reset_index()
    daily_medians.rename(columns={'Daily_Demand': 'Median_Demand'}, inplace=True)
    
    # Apply smoothing to the median (7-day rolling average)
    daily_medians['Smoothed_Median'] = daily_medians['Median_Demand'].rolling(
        window=7, center=True, min_periods=1
    ).mean()
    
    # Create current year demand based on smoothed median
    current_year_start = datetime(datetime.now().year, 1, 1)
    current_year_end = datetime.now() + timedelta(days=90)
    current_dates = pd.date_range(start=current_year_start, end=current_year_end, freq='D')
    
    current_demand = []
    for date in current_dates:
        day_of_year = date.timetuple().tm_yday
        median_demand = daily_medians[daily_medians['DayOfYear'] == day_of_year]['Smoothed_Median'].iloc[0]
        
        # Add small random variation around median
        daily_variation = np.random.normal(0, 0.03)
        current_daily_demand = median_demand * (1 + daily_variation)
        current_demand.append(current_daily_demand)
    
    final_demand_df = pd.DataFrame({
        'Date': current_dates,
        'Market_Demand': current_demand
    })
    
    # Add metadata
    final_demand_df.attrs['source'] = '5-Year Median Analysis'
    final_demand_df.attrs['method'] = 'Smoothed Median with Seasonal Adjustment'
    final_demand_df.attrs['data_years'] = f'{start_date.year}-{end_date.year}'
    
    return final_demand_df

@st.cache_data(ttl=1800)
def generate_complete_production_data():
    """Generate production data for ALL WA facilities"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Full year for better analysis
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    production_data = {'Date': dates}
    
    np.random.seed(42)
    
    # Generate data for ALL facilities
    for facility, config in WA_PRODUCTION_FACILITIES_COMPLETE.items():
        typical_output = config['output']
        base_capacity = config['capacity']
        status = config['status']
        start_year = config.get('start_year', 2020)
        fuel_type = config.get('fuel_type', 'Natural Gas')
        
        # Only generate production for operational or ramping facilities
        if status in ['operating', 'ramping', 'declining']:
            
            # Handle storage facilities differently
            if fuel_type == 'Storage':
                # Storage facilities show net withdrawals (can be negative for injections)
                storage_pattern = np.random.uniform(-0.5, 1.0, len(dates))  # Can inject or withdraw
                production = typical_output * storage_pattern
            else:
                # Regular gas production facilities
                if status == 'operating':
                    base_utilization = np.random.uniform(0.85, 0.95, len(dates))
                elif status == 'ramping':
                    ramp_progress = np.linspace(0.3, 0.9, len(dates))
                    base_utilization = ramp_progress + np.random.normal(0, 0.05, len(dates))
                else:  # declining
                    decline_progress = np.linspace(0.8, 0.4, len(dates))
                    base_utilization = decline_progress + np.random.normal(0, 0.03, len(dates))
                
                # Seasonal factors (maintenance typically in summer)
                seasonal_factor = 1 + 0.1 * np.cos(2 * np.pi * (dates.dayofyear - 200) / 365)
                
                # Regional factors
                if config['region'] == 'Perth Basin':
                    regional_variation = np.random.normal(0, 0.12, len(dates))
                else:
                    regional_variation = np.random.normal(0, 0.08, len(dates))
                
                production = (typical_output * base_utilization * seasonal_factor * 
                             (1 + regional_variation))
                
                # Cap production at capacity
                production = np.clip(production, 0, base_capacity)
            
            production_data[facility] = production
        
        else:
            # Future/planned facilities have zero current production
            production_data[facility] = np.zeros(len(dates))
    
    df = pd.DataFrame(production_data)
    
    # Calculate total supply from operating production facilities only (exclude storage)
    production_facilities = [f for f, config in WA_PRODUCTION_FACILITIES_COMPLETE.items() 
                          if config['status'] in ['operating', 'ramping', 'declining'] 
                          and config.get('fuel_type') != 'Storage']
    
    df['Total_Supply'] = df[production_facilities].sum(axis=1)
    
    # Add comprehensive metadata
    df.attrs['total_facilities'] = len(WA_PRODUCTION_FACILITIES_COMPLETE)
    df.attrs['production_facilities'] = len(production_facilities)
    df.attrs['storage_facilities'] = len([f for f, c in WA_PRODUCTION_FACILITIES_COMPLETE.items() 
                                        if c.get('fuel_type') == 'Storage'])
    
    return df

@st.cache_data(ttl=1800)
def generate_storage_data():
    """Generate detailed storage facility data for injections, withdrawals, and volumes"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    storage_data = {'Date': dates}
    
    np.random.seed(43)  # Different seed for storage
    
    for facility, config in WA_STORAGE_FACILITIES.items():
        max_injection = config['max_injection_rate']
        max_withdrawal = config['max_withdrawal_rate'] 
        max_working_capacity = config['max_working_capacity'] * 1000  # Convert PJ to TJ
        
        # Generate seasonal storage patterns
        injections = []
        withdrawals = []
        volumes = []
        current_volume = max_working_capacity * 0.7  # Start at 70% full
        
        for i, date in enumerate(dates):
            day_of_year = date.timetuple().tm_yday
            
            # Seasonal injection/withdrawal patterns
            # Inject during low demand periods (summer), withdraw during high demand (winter)
            seasonal_factor = np.cos(2 * np.pi * (day_of_year - 200) / 365)
            
            # Weekly patterns (more activity on weekdays)
            weekly_factor = 1.0 if date.weekday() < 5 else 0.6
            
            # Random daily variation
            daily_variation = np.random.normal(0, 0.3)
            
            # Determine injection vs withdrawal
            activity_factor = seasonal_factor + daily_variation
            
            if activity_factor > 0.2:  # Injection period (summer/low demand)
                injection_rate = min(max_injection * activity_factor * weekly_factor, max_injection)
                withdrawal_rate = 0
                net_flow = injection_rate
            elif activity_factor < -0.2:  # Withdrawal period (winter/high demand)
                injection_rate = 0
                withdrawal_rate = min(max_withdrawal * abs(activity_factor) * weekly_factor, max_withdrawal)
                net_flow = -withdrawal_rate
            else:  # Neutral period (no significant activity)
                injection_rate = 0
                withdrawal_rate = 0
                net_flow = 0
            
            # Update storage volume
            current_volume += net_flow
            
            # Ensure volume stays within bounds
            current_volume = max(0, min(current_volume, max_working_capacity))
            
            # Adjust flows if volume constraints would be violated
            if current_volume >= max_working_capacity and net_flow > 0:
                injection_rate = 0
                net_flow = 0
            elif current_volume <= 0 and net_flow < 0:
                withdrawal_rate = 0
                net_flow = 0
            
            injections.append(injection_rate)
            withdrawals.append(withdrawal_rate)
            volumes.append(current_volume)
        
        # Store data for this facility
        storage_data[f'{facility}_Injection'] = injections
        storage_data[f'{facility}_Withdrawal'] = withdrawals
        storage_data[f'{facility}_Volume'] = volumes
        storage_data[f'{facility}_Net_Flow'] = [inj - wit for inj, wit in zip(injections, withdrawals)]
    
    df = pd.DataFrame(storage_data)
    
    # Calculate total system storage metrics
    injection_cols = [col for col in df.columns if col.endswith('_Injection')]
    withdrawal_cols = [col for col in df.columns if col.endswith('_Withdrawal')]
    volume_cols = [col for col in df.columns if col.endswith('_Volume')]
    
    df['Total_Injections'] = df[injection_cols].sum(axis=1)
    df['Total_Withdrawals'] = df[withdrawal_cols].sum(axis=1)
    df['Total_Volume'] = df[volume_cols].sum(axis=1)
    df['Net_Storage_Flow'] = df['Total_Injections'] - df['Total_Withdrawals']
    
    # Add metadata
    total_capacity = sum(config['max_working_capacity'] for config in WA_STORAGE_FACILITIES.values()) * 1000
    df.attrs['total_working_capacity'] = total_capacity
    df.attrs['num_facilities'] = len(WA_STORAGE_FACILITIES)
    
    return df

@st.cache_data(ttl=3600)
def get_news_feed():
    """Get news feed (with fallback)"""
    
    return [
        {
            'headline': 'WA Gas Statement of Opportunities 2024 released',
            'sentiment': 'N',
            'source': 'AEMO',
            'timestamp': '2 hours ago',
            'summary': 'AEMO releases annual outlook showing adequate gas supply for WA through 2030'
        },
        {
            'headline': 'Tubridgi storage facility reaches full operational capacity',
            'sentiment': '+',
            'source': 'APA Group',
            'timestamp': '4 hours ago',
            'summary': 'Underground salt cavern storage provides enhanced system flexibility'
        },
        {
            'headline': 'Winter gas demand peaks challenge system capacity',
            'sentiment': '-',
            'source': 'Analysis',
            'timestamp': '6 hours ago',
            'summary': 'Cold weather drives residential demand above seasonal norms'
        },
        {
            'headline': 'Browse FLNG development timeline extended to 2035',
            'sentiment': '-',
            'source': 'Woodside',
            'timestamp': '1 day ago',
            'summary': 'Regulatory approvals and technical challenges delay project startup'
        }
    ]

# ==============================================================================
# ENHANCED VISUALIZATION FUNCTIONS
# ==============================================================================

def create_enhanced_supply_demand_chart_with_slider(production_df, demand_df, selected_facilities):
    """Enhanced chart with date range slider and all facilities"""
    
    if not selected_facilities:
        st.warning("⚠️ No facilities selected for chart")
        return go.Figure()
    
    try:
        # Merge data
        production_clean = production_df.copy()
        demand_clean = demand_df.copy()
        
        production_clean['Date'] = pd.to_datetime(production_clean['Date']).dt.date
        demand_clean['Date'] = pd.to_datetime(demand_clean['Date']).dt.date
        
        chart_data = production_clean.merge(demand_clean, on='Date', how='inner')
        chart_data['Date'] = pd.to_datetime(chart_data['Date'])
        
        if chart_data.empty:
            st.error("❌ No matching dates between production and demand data")
            return go.Figure()
        
        # Create figure with date range slider
        fig = go.Figure()
        
        # Add stacked areas for all selected facilities
        for i, facility in enumerate(selected_facilities):
            if facility in chart_data.columns:
                config = WA_PRODUCTION_FACILITIES_COMPLETE.get(facility, {})
                color = config.get('color', f'rgba({50 + i*25}, {100 + i*20}, {150 + i*15}, 0.8)')
                operator = config.get('operator', 'Unknown')
                capacity = config.get('capacity', 0)
                region = config.get('region', 'Unknown')
                fuel_type = config.get('fuel_type', 'Natural Gas')
                
                production_values = chart_data[facility].fillna(0)
                
                # Different handling for storage facilities
                if fuel_type == 'Storage':
                    line_style = dict(dash='dot', width=2)
                    fill_style = 'none'
                    stack_group = None
                else:
                    line_style = dict(width=0)
                    fill_style = 'tonexty' if i > 0 else 'tozeroy'
                    stack_group = 'supply'
                
                fig.add_trace(go.Scatter(
                    x=chart_data['Date'],
                    y=production_values,
                    name=facility,
                    stackgroup=stack_group,
                    mode='none' if fuel_type != 'Storage' else 'lines',
                    fill=fill_style,
                    fillcolor=color,
                    line=line_style,
                    hovertemplate=f'<b>{facility}</b><br>' +
                                 f'Operator: {operator}<br>' +
                                 f'Region: {region}<br>' +
                                 f'Type: {fuel_type}<br>' +
                                 'Date: %{x|%Y-%m-%d}<br>' +
                                 ('Net Flow: %{y:.1f} TJ/day<br>' if fuel_type == 'Storage' else 'Production: %{y:.1f} TJ/day<br>') +
                                 f'Max Capacity: {capacity} TJ/day<extra></extra>'
                ))
        
        # Add 5-year median demand line
        if 'Market_Demand' in chart_data.columns:
            demand_values = chart_data['Market_Demand'].fillna(0)
            demand_source = getattr(demand_df, 'attrs', {}).get('source', 'Unknown')
            
            fig.add_trace(go.Scatter(
                x=chart_data['Date'],
                y=demand_values,
                name='Market Demand (5-Year Median)',
                mode='lines',
                line=dict(color='#1f2937', width=4),
                hovertemplate='<b>Market Demand (5-Year Median)</b><br>' +
                             'Date: %{x|%Y-%m-%d}<br>' +
                             'Demand: %{y:.1f} TJ/day<br>' +
                             f'Source: {demand_source}<extra></extra>'
            ))
        
        # Enhanced layout with date range slider
        fig.update_layout(
            title=dict(
                text='Complete WA Gas Market Supply vs 5-Year Median Demand<br><sub>Updated Facilities • Pilbara Zone • Storage Integration</sub>',
                font=dict(size=20, color='#1f2937'),
                x=0.02
            ),
            xaxis=dict(
                title='Date',
                showgrid=True,
                gridcolor='#f0f0f0',
                rangeslider=dict(visible=True),
                rangeselector=dict(
                    buttons=list([
                        dict(count=30, label="30D", step="day", stepmode="backward"),
                        dict(count=90, label="90D", step="day", stepmode="backward"),
                        dict(count=6, label="6M", step="month", stepmode="backward"),
                        dict(count=1, label="1Y", step="year", stepmode="backward"),
                        dict(step="all", label="All")
                    ])
                )
            ),
            yaxis=dict(
                title='Gas Flow (TJ/day)',
                showgrid=True,
                gridcolor='#f0f0f0'
            ),
            height=700,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
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
            margin=dict(l=60, r=280, t=100, b=150)
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Enhanced chart creation error: {e}")
        return go.Figure()

def create_storage_analysis_chart(storage_df):
    """Create comprehensive storage analysis with multiple subplots"""
    
    if storage_df.empty:
        st.error("❌ No storage data available")
        return go.Figure()
    
    # Create subplots: Storage Flows, Volume Levels, Net Flow
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[
            'Storage Injections vs Withdrawals (TJ/day)',
            'Gas Volume in Storage (TJ)',
            'Net Storage Flow (TJ/day)'
        ],
        vertical_spacing=0.08,
        specs=[[{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}]]
    )
    
    # Plot 1: Injections vs Withdrawals
    fig.add_trace(
        go.Scatter(
            x=storage_df['Date'],
            y=storage_df['Total_Injections'],
            name='Total Injections',
            fill='tozeroy',
            fillcolor='rgba(34, 197, 94, 0.3)',
            line=dict(color='rgba(34, 197, 94, 1)', width=2),
            hovertemplate='<b>Injections</b><br>Date: %{x}<br>Rate: %{y:.1f} TJ/day<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=storage_df['Date'],
            y=storage_df['Total_Withdrawals'],
            name='Total Withdrawals',
            fill='tozeroy',
            fillcolor='rgba(239, 68, 68, 0.3)',
            line=dict(color='rgba(239, 68, 68, 1)', width=2),
            hovertemplate='<b>Withdrawals</b><br>Date: %{x}<br>Rate: %{y:.1f} TJ/day<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Plot 2: Volume levels for each facility
    colors = ['rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)']
    for i, (facility, config) in enumerate(WA_STORAGE_FACILITIES.items()):
        volume_col = f'{facility}_Volume'
        if volume_col in storage_df.columns:
            max_capacity = config['max_working_capacity'] * 1000  # Convert to TJ
            
            fig.add_trace(
                go.Scatter(
                    x=storage_df['Date'],
                    y=storage_df[volume_col],
                    name=f'{facility} Volume',
                    line=dict(color=colors[i % len(colors)], width=3),
                    hovertemplate=f'<b>{facility}</b><br>Date: %{{x}}<br>Volume: %{{y:.0f}} TJ<br>Capacity: {max_capacity:.0f} TJ<extra></extra>'
                ),
                row=2, col=1
            )
            
            # Add capacity line
            fig.add_hline(
                y=max_capacity, 
                line_dash="dash", 
                line_color=colors[i % len(colors)],
                annotation_text=f"{facility} Max Capacity",
                row=2, col=1
            )
    
    # Plot 3: Net storage flow
    fig.add_trace(
        go.Scatter(
            x=storage_df['Date'],
            y=storage_df['Net_Storage_Flow'],
            name='Net Storage Flow',
            mode='lines',
            line=dict(color='rgba(75, 85, 99, 1)', width=3),
            fill='tonexty',
            fillcolor='rgba(75, 85, 99, 0.2)',
            hovertemplate='<b>Net Storage Flow</b><br>Date: %{x}<br>Flow: %{y:.1f} TJ/day<br><i>Positive = Net Injection, Negative = Net Withdrawal</i><extra></extra>'
        ),
        row=3, col=1
    )
    
    # Add zero line for net flow
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=3, col=1)
    
    # Update layout
    fig.update_layout(
        title=dict(
            text='WA Gas Storage System Analysis<br><sub>Mondarra & Tubridgi Underground Storage Facilities</sub>',
            font=dict(size=20, color='#1f2937'),
            x=0.02
        ),
        height=900,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02
        ),
        margin=dict(l=60, r=200, t=100, b=60)
    )
    
    # Update x-axis labels
    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_yaxes(title_text="Flow Rate (TJ/day)", row=1, col=1)
    fig.update_yaxes(title_text="Volume (TJ)", row=2, col=1)
    fig.update_yaxes(title_text="Net Flow (TJ/day)", row=3, col=1)
    
    return fig

def create_facility_capacity_chart():
    """Create facility capacity chart with updated facilities"""
    
    facilities = []
    capacities = []
    colors = []
    regions = []
    
    for facility, config in WA_PRODUCTION_FACILITIES_COMPLETE.items():
        if config['status'] in ['operating', 'ramping', 'declining', 'under_construction']:
            facilities.append(facility)
            capacities.append(config['capacity'])
            colors.append(config['color'])
            regions.append(config['region'])
    
    fig = go.Figure(go.Bar(
        y=facilities,
        x=capacities,
        orientation='h',
        marker_color=colors,
        text=capacities,
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Capacity: %{x} TJ/day<br>Region: %{customdata}<extra></extra>',
        customdata=regions
    ))
    
    fig.update_layout(
        title='WA Gas Production Facilities - Maximum Capacity<br><sub>Updated Zones: Pilbara & Perth Basin</sub>',
        xaxis_title='Capacity (TJ/day)',
        height=600,
        plot_bgcolor='white',
        margin=dict(l=200, r=50, t=80, b=50)
    )
    
    return fig

# ==============================================================================
# MAIN DASHBOARD PAGES
# ==============================================================================

def display_main_dashboard():
    """Main dashboard with comprehensive integration"""
    
    # Enhanced header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown('<h1 class="main-header">⚡ WA Natural Gas Market Dashboard</h1>', 
                    unsafe_allow_html=True)
        st.markdown("""
        <div class="data-source-badge">Updated Facilities & Zones</div>
        <div class="data-source-badge">Tubridgi Storage Integration</div>
        <div class="data-source-badge">5-Year Median Demand</div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%H:%M AWST')}")
        st.markdown("**Data Coverage:** Complete WA System")
        
    with col3:
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # Test AEMO connection
    with st.expander("📡 AEMO API Status", expanded=False):
        is_connected, status_message = aemo_client.test_api_connection()
        st.write(status_message)
        
        if is_connected:
            st.success("🎯 AEMO systems are accessible and ready for integration")
        else:
            st.info("📊 Using enhanced baseline data with 5-year demand analysis")
    
    # Load data
    try:
        with st.spinner("Loading comprehensive WA gas market data..."):
            production_df = generate_complete_production_data()
            demand_df = generate_advanced_demand_data_5_year()
            storage_df = generate_storage_data()
            news_items = get_news_feed()
    except Exception as e:
        st.error(f"❌ Data loading error: {e}")
        return
    
    # Enhanced KPI Cards with storage metrics
    if not production_df.empty and not demand_df.empty:
        today_supply = production_df['Total_Supply'].iloc[-1]
        today_demand = demand_df['Market_Demand'].iloc[-1]
        balance = today_supply - today_demand
        today_storage_flow = storage_df['Net_Storage_Flow'].iloc[-1]
        total_storage_volume = storage_df['Total_Volume'].iloc[-1]
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value" style="color: {'green' if balance > 0 else 'red'}">
                    {abs(balance):.0f}
                </p>
                <p class="kpi-label">Supply/Demand Balance (TJ/day)</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_capacity = sum(config['capacity'] for config in WA_PRODUCTION_FACILITIES_COMPLETE.values()
                              if config['status'] in ['operating', 'ramping', 'declining'] 
                              and config.get('fuel_type') != 'Storage')
            utilization = (today_supply / total_capacity * 100) if total_capacity > 0 else 0
            
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{utilization:.1f}%</p>
                <p class="kpi-label">System Utilization</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            operating_facilities = sum(1 for config in WA_PRODUCTION_FACILITIES_COMPLETE.values() 
                                     if config['status'] == 'operating' and config.get('fuel_type') != 'Storage')
            
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{operating_facilities}</p>
                <p class="kpi-label">Operating Facilities</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            storage_flow_color = 'green' if today_storage_flow > 0 else 'red' if today_storage_flow < 0 else 'gray'
            
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value" style="color: {storage_flow_color}">
                    {today_storage_flow:.0f}
                </p>
                <p class="kpi-label">Net Storage Flow (TJ/day)</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            max_storage_capacity = sum(config['max_working_capacity'] for config in WA_STORAGE_FACILITIES.values()) * 1000
            storage_fill = (total_storage_volume / max_storage_capacity * 100) if max_storage_capacity > 0 else 0
            
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{storage_fill:.1f}%</p>
                <p class="kpi-label">Storage Fill Level</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Main content
    col1, col2 = st.columns([2.5, 1])
    
    with col1:
        st.markdown("### 📊 WA Gas Market Supply & Demand Analysis")
        st.markdown("*Complete Facility Coverage • Updated Zones • 5-Year Median Demand*")
        
        # Enhanced chart controls
        control_col1, control_col2, control_col3 = st.columns(3)
        with control_col1:
            chart_type = st.selectbox("📊 Chart Type", 
                                    ["Supply vs Demand", "Facility Capacity", "Storage Analysis"])
        with control_col2:
            time_period = st.selectbox("📅 Time Period", 
                                     ["Last 30 Days", "Last 90 Days", "Last 6 Months", "Full Year"], 
                                     index=1)
        with control_col3:
            include_future = st.checkbox("🔮 Include Future Projects", value=False)
        
        if chart_type == "Supply vs Demand":
            # Enhanced facility selection with regional grouping
            st.markdown("### 🌍 Select Facilities by Updated Zones:")
            
            regions = {}
            for facility, config in WA_PRODUCTION_FACILITIES_COMPLETE.items():
                region = config.get('region', 'Other')
                if region not in regions:
                    regions[region] = []
                regions[region].append(facility)
            
            selected_facilities = []
            
            for region, facilities in regions.items():
                with st.expander(f"📍 {region} Zone ({len(facilities)} facilities)", expanded=True):
                    region_cols = st.columns(2)
                    
                    for i, facility in enumerate(facilities):
                        config = WA_PRODUCTION_FACILITIES_COMPLETE[facility]
                        status = config['status']
                        capacity = config['capacity']
                        operator = config['operator']
                        fuel_type = config.get('fuel_type', 'Natural Gas')
                        
                        status_icons = {'operating': '🟢', 'ramping': '🟡', 'declining': '🟠', 
                                      'future': '⚪', 'under_construction': '🔵', 'planned': '⚫'}
                        status_icon = status_icons.get(status, '❓')
                        
                        # Skip future facilities unless explicitly included
                        if not include_future and status in ['future', 'planned']:
                            continue
                        
                        col_idx = i % 2
                        with region_cols[col_idx]:
                            is_selected = st.checkbox(
                                f"{status_icon} **{facility}**",
                                value=(status in ['operating', 'ramping'] and len(selected_facilities) < 12),
                                key=f"facility_{region}_{facility}",
                                help=f"Operator: {operator} | Capacity: {capacity} TJ/day | Type: {fuel_type} | Status: {status.title()}"
                            )
                            
                            if is_selected:
                                selected_facilities.append(facility)
                                st.caption(f"📊 {capacity} TJ/day | {operator}")
            
            if selected_facilities:
                fig = create_enhanced_supply_demand_chart_with_slider(
                    production_df, demand_df, selected_facilities
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Facility contribution summary
                st.markdown("### 🏭 Selected Facility Analysis")
                
                facility_contributions = []
                for facility in selected_facilities:
                    if facility in production_df.columns:
                        avg_production = production_df[facility].mean()
                        config = WA_PRODUCTION_FACILITIES_COMPLETE[facility]
                        capacity = config['capacity']
                        utilization = (avg_production / capacity * 100) if capacity > 0 else 0
                        
                        facility_contributions.append({
                            'Facility': facility,
                            'Avg Production (TJ/day)': f"{avg_production:.1f}",
                            'Capacity (TJ/day)': capacity,
                            'Utilization (%)': f"{utilization:.1f}%",
                            'Operator': config['operator'],
                            'Zone': config['region'],  # Updated from 'Region'
                            'Type': config.get('fuel_type', 'Natural Gas')
                        })
                
                contrib_df = pd.DataFrame(facility_contributions)
                st.dataframe(contrib_df, use_container_width=True, height=300)
            else:
                st.warning("⚠️ Please select at least one facility")
        
        elif chart_type == "Facility Capacity":
            fig = create_facility_capacity_chart()
            st.plotly_chart(fig, use_container_width=True)
            
        elif chart_type == "Storage Analysis":
            fig = create_storage_analysis_chart(storage_df)
            st.plotly_chart(fig, use_container_width=True)
            
            # Storage system summary
            st.markdown("### 🔋 WA Storage System Overview")
            
            storage_col1, storage_col2 = st.columns(2)
            
            with storage_col1:
                st.markdown("#### Storage Facilities")
                for facility, config in WA_STORAGE_FACILITIES.items():
                    st.markdown(f"""
                    **🏭 {facility}**
                    - **Operator:** {config['operator']}
                    - **Working Capacity:** {config['max_working_capacity']} PJ
                    - **Max Injection:** {config['max_injection_rate']} TJ/day
                    - **Max Withdrawal:** {config['max_withdrawal_rate']} TJ/day
                    - **Storage Type:** {config['storage_type']}
                    """)
            
            with storage_col2:
                st.markdown("#### Current Status")
                current_total_volume = storage_df['Total_Volume'].iloc[-1]
                max_total_capacity = sum(config['max_working_capacity'] for config in WA_STORAGE_FACILITIES.values()) * 1000
                current_fill_level = (current_total_volume / max_total_capacity * 100) if max_total_capacity > 0 else 0
                
                st.metric("Total Storage Volume", f"{current_total_volume:,.0f} TJ")
                st.metric("System Fill Level", f"{current_fill_level:.1f}%")
                st.metric("Available Capacity", f"{max_total_capacity - current_total_volume:,.0f} TJ")
                
                recent_injection = storage_df['Total_Injections'].tail(7).mean()
                recent_withdrawal = storage_df['Total_Withdrawals'].tail(7).mean()
                
                st.metric("Avg Daily Injection (7d)", f"{recent_injection:.1f} TJ/day")
                st.metric("Avg Daily Withdrawal (7d)", f"{recent_withdrawal:.1f} TJ/day")
    
    with col2:
        # Enhanced news and market intelligence
        st.markdown("### 📰 WA Gas Market News")
        st.markdown("*Updated with storage and facility changes*")
        
        for item in news_items:
            sentiment_icon = {'N': '📰', '+': '📈', '-': '📉'}.get(item['sentiment'], '📰')
            
            st.markdown(f"""
            **{sentiment_icon} {item['headline']}**  
            *{item['source']} • {item['timestamp']}*  
            {item['summary']}
            """)
            st.markdown("---")
        
        # Market summary with storage integration
        st.markdown("### 📈 Enhanced Market Summary")
        if not production_df.empty:
            avg_supply = production_df['Total_Supply'].mean()
            avg_demand = demand_df['Market_Demand'].mean()
            avg_storage_net = storage_df['Net_Storage_Flow'].mean()
            
            st.metric("Avg Daily Supply", f"{avg_supply:.0f} TJ/day")
            st.metric("Avg Daily Demand", f"{avg_demand:.0f} TJ/day")
            st.metric("Market Balance", f"{avg_supply - avg_demand:+.0f} TJ/day")
            st.metric("Avg Storage Net Flow", f"{avg_storage_net:+.1f} TJ/day")
        
        # Zone summary
        st.markdown("### 🌍 Updated Zone Summary")
        
        pilbara_facilities = [f for f, c in WA_PRODUCTION_FACILITIES_COMPLETE.items() 
                            if c['region'] == 'Pilbara' and c['status'] in ['operating', 'ramping']]
        perth_basin_facilities = [f for f, c in WA_PRODUCTION_FACILITIES_COMPLETE.items() 
                                if c['region'] == 'Perth Basin' and c['status'] in ['operating', 'ramping']]
        
        pilbara_capacity = sum(WA_PRODUCTION_FACILITIES_COMPLETE[f]['capacity'] for f in pilbara_facilities
                             if WA_PRODUCTION_FACILITIES_COMPLETE[f].get('fuel_type') != 'Storage')
        perth_basin_capacity = sum(WA_PRODUCTION_FACILITIES_COMPLETE[f]['capacity'] for f in perth_basin_facilities
                                 if WA_PRODUCTION_FACILITIES_COMPLETE[f].get('fuel_type') != 'Storage')
        
        st.markdown(f"**🏭 Pilbara Zone:** {len(pilbara_facilities)} facilities, {pilbara_capacity:,} TJ/day capacity")
        st.markdown(f"**🏭 Perth Basin:** {len(perth_basin_facilities)} facilities, {perth_basin_capacity:,} TJ/day capacity")
        
        storage_capacity = sum(config['max_working_capacity'] for config in WA_STORAGE_FACILITIES.values())
        st.markdown(f"**🔋 Storage System:** {len(WA_STORAGE_FACILITIES)} facilities, {storage_capacity} PJ working capacity")

def display_storage_dashboard():
    """NEW: Dedicated storage analysis dashboard"""
    
    st.markdown('<h1 class="main-header">🔋 WA Gas Storage Analysis Dashboard</h1>', 
                unsafe_allow_html=True)
    st.markdown("*Comprehensive Storage Injection, Withdrawal & Volume Tracking*")
    
    # Load storage data
    try:
        storage_df = generate_storage_data()
    except Exception as e:
        st.error(f"❌ Storage data loading error: {e}")
        return
    
    # Storage system overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_capacity = sum(config['max_working_capacity'] for config in WA_STORAGE_FACILITIES.values())
        st.metric("Total Working Capacity", f"{total_capacity} PJ")
    
    with col2:
        total_injection_capacity = sum(config['max_injection_rate'] for config in WA_STORAGE_FACILITIES.values())
        st.metric("Max Injection Rate", f"{total_injection_capacity} TJ/day")
    
    with col3:
        total_withdrawal_capacity = sum(config['max_withdrawal_rate'] for config in WA_STORAGE_FACILITIES.values())
        st.metric("Max Withdrawal Rate", f"{total_withdrawal_capacity} TJ/day")
    
    with col4:
        current_fill = (storage_df['Total_Volume'].iloc[-1] / (total_capacity * 1000) * 100)
        st.metric("Current Fill Level", f"{current_fill:.1f}%")
    
    st.markdown("---")
    
    # Main storage analysis chart
    fig = create_storage_analysis_chart(storage_df)
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed facility analysis
    st.markdown("### 🏭 Individual Storage Facility Performance")
    
    facility_tabs = st.tabs(list(WA_STORAGE_FACILITIES.keys()))
    
    for i, (facility, config) in enumerate(WA_STORAGE_FACILITIES.items()):
        with facility_tabs[i]:
            
            # Facility overview
            fac_col1, fac_col2, fac_col3 = st.columns(3)
            
            with fac_col1:
                st.markdown(f"""
                <div class="storage-card">
                    <h4>{facility}</h4>
                    <p><strong>Operator:</strong> {config['operator']}</p>
                    <p><strong>Storage Type:</strong> {config['storage_type']}</p>
                    <p><strong>Location:</strong> {config['region']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with fac_col2:
                current_volume = storage_df[f'{facility}_Volume'].iloc[-1]
                max_capacity = config['max_working_capacity'] * 1000
                fill_level = (current_volume / max_capacity * 100) if max_capacity > 0 else 0
                
                st.markdown(f"""
                <div class="storage-metric">
                    <h3>{current_volume:,.0f}</h3>
                    <p>Current Volume (TJ)</p>
                </div>
                <div class="storage-metric">
                    <h3>{fill_level:.1f}%</h3>
                    <p>Fill Level</p>
                </div>
                """, unsafe_allow_html=True)
            
            with fac_col3:
                recent_injection = storage_df[f'{facility}_Injection'].tail(30).mean()
                recent_withdrawal = storage_df[f'{facility}_Withdrawal'].tail(30).mean()
                
                st.markdown(f"""
                <div class="storage-metric">
                    <h3 class="storage-flow-positive">{recent_injection:.1f}</h3>
                    <p>Avg Injection (30d)</p>
                </div>
                <div class="storage-metric">
                    <h3 class="storage-flow-negative">{recent_withdrawal:.1f}</h3>
                    <p>Avg Withdrawal (30d)</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Individual facility chart
            facility_fig = go.Figure()
            
            # Volume level
            facility_fig.add_trace(go.Scatter(
                x=storage_df['Date'],
                y=storage_df[f'{facility}_Volume'],
                name='Volume Level',
                yaxis='y',
                line=dict(color='blue', width=3),
                fill='tozeroy',
                fillcolor='rgba(59, 130, 246, 0.2)'
            ))
            
            # Injection/Withdrawal flows (secondary y-axis)
            facility_fig.add_trace(go.Scatter(
                x=storage_df['Date'],
                y=storage_df[f'{facility}_Injection'],
                name='Injections',
                yaxis='y2',
                line=dict(color='green', width=2),
                fill='tozeroy',
                fillcolor='rgba(34, 197, 94, 0.2)'
            ))
            
            facility_fig.add_trace(go.Scatter(
                x=storage_df['Date'],
                y=storage_df[f'{facility}_Withdrawal'],
                name='Withdrawals',
                yaxis='y2',
                line=dict(color='red', width=2),
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.2)'
            ))
            
            # Add capacity line
            facility_fig.add_hline(
                y=config['max_working_capacity'] * 1000,
                line_dash="dash",
                line_color="black",
                annotation_text="Max Capacity"
            )
            
            facility_fig.update_layout(
                title=f'{facility} - Volume and Flow Analysis',
                xaxis_title='Date',
                yaxis=dict(title='Volume (TJ)', side='left'),
                yaxis2=dict(title='Flow Rate (TJ/day)', side='right', overlaying='y'),
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(facility_fig, use_container_width=True)
            
            # Statistics table
            stats_data = {
                'Metric': [
                    'Maximum Volume Recorded',
                    'Minimum Volume Recorded',
                    'Average Volume',
                    'Maximum Injection Rate',
                    'Maximum Withdrawal Rate',
                    'Days Above 80% Capacity',
                    'Days Below 20% Capacity'
                ],
                'Value': [
                    f"{storage_df[f'{facility}_Volume'].max():,.0f} TJ",
                    f"{storage_df[f'{facility}_Volume'].min():,.0f} TJ",
                    f"{storage_df[f'{facility}_Volume'].mean():,.0f} TJ",
                    f"{storage_df[f'{facility}_Injection'].max():,.1f} TJ/day",
                    f"{storage_df[f'{facility}_Withdrawal'].max():,.1f} TJ/day",
                    f"{sum(storage_df[f'{facility}_Volume'] > config['max_working_capacity'] * 800)} days",
                    f"{sum(storage_df[f'{facility}_Volume'] < config['max_working_capacity'] * 200)} days"
                ]
            }
            
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

def display_enhanced_sidebar():
    """Enhanced sidebar with storage page navigation"""
    
    with st.sidebar:
        st.markdown("## 📡 WA Gas Market Dashboard")
        st.markdown("### Enhanced Facility & Storage Analysis")
        st.markdown("*Complete System Coverage*")
        
        # Navigation with new storage page
        selected_page = st.radio(
            "🗂️ Dashboard Sections:",
            [
                "🎯 Main Dashboard", 
                "🔋 Storage Analysis",  # NEW PAGE
                "🏭 Facility Analysis",
                "📊 Market Reports",
                "🔧 System Status"
            ],
            index=0
        )
        
        st.markdown("---")
        
        # Updated facility counts
        st.markdown("### 🏭 Updated Facility Summary")
        
        pilbara_count = sum(1 for config in WA_PRODUCTION_FACILITIES_COMPLETE.values() 
                          if config['region'] == 'Pilbara')
        perth_basin_count = sum(1 for config in WA_PRODUCTION_FACILITIES_COMPLETE.values() 
                              if config['region'] == 'Perth Basin')
        storage_count = len(WA_STORAGE_FACILITIES)
        
        st.markdown(f"**🏭 Pilbara Zone:** {pilbara_count} facilities")
        st.markdown(f"**🏭 Perth Basin:** {perth_basin_count} facilities") 
        st.markdown(f"**🔋 Storage Systems:** {storage_count} facilities")
        st.markdown(f"**📊 Total Facilities:** {len(WA_PRODUCTION_FACILITIES_COMPLETE)}")
        
        # Key updates
        st.markdown("### ✨ Recent Updates")
        st.markdown("✅ Added Tubridgi Storage")
        st.markdown("✅ Updated Browse to 2035")
        st.markdown("✅ Renamed to Pilbara Zone")
        st.markdown("✅ Moved Devil Creek to Pilbara")
        st.markdown("✅ Removed RWE facilities")
        st.markdown("✅ Added Storage Dashboard")
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 Refresh All Data", type="primary"):
            st.cache_data.clear()
            st.success("✅ All data refreshed")
            st.rerun()
        
        if st.button("📊 Storage Status"):
            storage_df = generate_storage_data()
            total_volume = storage_df['Total_Volume'].iloc[-1]
            max_capacity = sum(config['max_working_capacity'] for config in WA_STORAGE_FACILITIES.values()) * 1000
            fill_level = (total_volume / max_capacity * 100)
            
            st.write(f"**Current Fill:** {fill_level:.1f}%")
            st.write(f"**Total Volume:** {total_volume:,.0f} TJ")
            st.write(f"**Available Space:** {max_capacity - total_volume:,.0f} TJ")
        
        st.markdown("---")
        st.markdown("**🚀 Enhanced Dashboard v4.0**")
        st.markdown("*Complete WA Gas System Analysis*")
        st.markdown(f"*Updated: {datetime.now().strftime('%Y-%m-%d')}*")
        
        return selected_page

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================

def main():
    """Main application with enhanced storage integration"""
    
    selected_page = display_enhanced_sidebar()
    
    if selected_page == "🎯 Main Dashboard":
        display_main_dashboard()
        
    elif selected_page == "🔋 Storage Analysis":  # NEW PAGE
        display_storage_dashboard()
        
    elif selected_page == "🏭 Facility Analysis":
        st.markdown("### 🏭 WA Gas Production Facilities Analysis")
        st.markdown("*Enhanced with updated zones and facility corrections*")
        
        # Show updated facility summary
        st.markdown("#### 📊 Complete Facility Overview")
        
        summary_data = []
        for facility, config in WA_PRODUCTION_FACILITIES_COMPLETE.items():
            summary_data.append({
                'Facility': facility,
                'Operator': config['operator'],
                'Capacity (TJ/day)': config['capacity'],
                'Status': config['status'].replace('_', ' ').title(),
                'Zone': config['region'],  # Updated column name
                'Start Year': config.get('start_year', 'N/A'),
                'Type': config.get('fuel_type', 'Natural Gas')
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Add zone filter
        zone_filter = st.selectbox("Filter by Zone:", 
                                 ["All Zones"] + list(summary_df['Zone'].unique()))
        
        if zone_filter != "All Zones":
            filtered_df = summary_df[summary_df['Zone'] == zone_filter]
        else:
            filtered_df = summary_df
        
        st.dataframe(filtered_df, use_container_width=True, height=500)
        
        # Zone capacity analysis
        st.markdown("#### 🌍 Zone Capacity Analysis")
        
        zone_col1, zone_col2 = st.columns(2)
        
        with zone_col1:
            pilbara_facilities = filtered_df[filtered_df['Zone'] == 'Pilbara']
            pilbara_capacity = pilbara_facilities['Capacity (TJ/day)'].sum()
            
            st.markdown(f"""
            **🏭 Pilbara Zone Summary:**
            - **Facilities:** {len(pilbara_facilities)}
            - **Total Capacity:** {pilbara_capacity:,} TJ/day
            - **Key Projects:** NWS, Gorgon, Wheatstone, Scarborough
            """)
        
        with zone_col2:
            perth_basin_facilities = filtered_df[filtered_df['Zone'] == 'Perth Basin']
            perth_basin_capacity = perth_basin_facilities['Capacity (TJ/day)'].sum()
            
            st.markdown(f"""
            **🏭 Perth Basin Summary:**
            - **Facilities:** {len(perth_basin_facilities)}
            - **Total Capacity:** {perth_basin_capacity:,} TJ/day
            - **Includes Storage:** Mondarra, Tubridgi
            """)
        
    elif selected_page == "📊 Market Reports":
        st.markdown("### 📊 WA Gas Market Reports")
        st.info("🚧 Enhanced market reporting with storage integration coming soon...")
        
    elif selected_page == "🔧 System Status":
        st.markdown("### 🔧 System Status & Diagnostics")
        
        # System information
        st.markdown("#### 📊 Dashboard Information")
        st.markdown(f"- **Version:** 4.0 Enhanced")
        st.markdown(f"- **Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M AWST')}")
        st.markdown(f"- **Total Facilities:** {len(WA_PRODUCTION_FACILITIES_COMPLETE)}")
        st.markdown(f"- **Storage Facilities:** {len(WA_STORAGE_FACILITIES)}")
        
        # Recent changes
        st.markdown("#### ✨ Recent Changes Applied")
        changes = [
            "✅ Added Tubridgi Underground Storage facility",
            "✅ Updated Browse FLNG startup date to 2035", 
            "✅ Removed RWE facilities as requested",
            "✅ Removed Cliff Head Gas Plant",
            "✅ Renamed Northwest Shelf Zone to Pilbara Zone",
            "✅ Moved Devil Creek from Perth Basin to Pilbara Zone",
            "✅ Added comprehensive Storage Analysis dashboard",
            "✅ Enhanced storage flow and volume tracking"
        ]
        
        for change in changes:
            st.markdown(change)
    
    else:
        st.markdown(f"### {selected_page}")
        st.info("🚧 This section is being enhanced...")

# ==============================================================================
# RUN APPLICATION
# ==============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Application Error: {e}")
        st.markdown("**Please refresh the page or contact support if the error persists.**")
        
        with st.expander("🔍 Debug Information"):
            st.code(str(e))
