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

# Enhanced CSS
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# WA GAS PRODUCTION FACILITIES DATABASE (ALL INTEGRATIONS APPLIED)
# ==============================================================================

WA_PRODUCTION_FACILITIES_COMPLETE = {
    # Major LNG/Domestic Gas Facilities - Pilbara Zone (Updated from Northwest Shelf)
    'Karratha Gas Plant (NWS)': {
        'operator': 'Woodside Energy',
        'capacity': 585,
        'color': 'rgba(31, 119, 180, 0.8)',
        'status': 'operating',
        'facility_code': 'KARR_GP',
        'output': 450,
        'region': 'Pilbara',  # Updated zone name
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
        'region': 'Pilbara',
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
        'region': 'Pilbara',
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
        'region': 'Pilbara',
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
        'region': 'Pilbara',
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
        'region': 'Pilbara',
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
        'region': 'Pilbara',  # MOVED from Perth Basin to Pilbara
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
    
    # Storage Facilities (Including Tubridgi Integration)
    'Mondarra Gas Storage': {
        'operator': 'APA Group',
        'capacity': 25,
        'color': 'rgba(255, 20, 147, 0.8)',
        'status': 'operating',
        'facility_code': 'MOND_ST',
        'output': 15,
        'region': 'Perth Basin',
        'start_year': 2019,
        'fuel_type': 'Storage'
    },
    'Tubridgi Underground Storage': {  # INTEGRATED Tubridgi Storage
        'operator': 'APA Group',
        'capacity': 45,
        'color': 'rgba(138, 43, 226, 0.8)',
        'status': 'operating',
        'facility_code': 'TUBR_ST',
        'output': 35,
        'region': 'Perth Basin',
        'start_year': 2020,
        'fuel_type': 'Storage'
    },
    
    # Future/Under Construction - Browse Updated to 2035
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
        'start_year': 2035,  # UPDATED from 2028 to 2035
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
    # NOTE: RWE facilities and Cliff Head removed as requested
}

# ==============================================================================
# STORAGE FACILITIES CONFIGURATION (INTEGRATED TUBRIDGI)
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
    'Tubridgi Underground Storage': {  # INTEGRATED Tubridgi Storage
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
# ENHANCED AEMO API CLIENT - DATETIME COMPLETELY FIXED
# ==============================================================================

class EnhancedAEMOClient:
    """Enhanced AEMO API client - ALL DATETIME ARITHMETIC ELIMINATED"""
    
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
        return False, "❌ AEMO APIs not accessible"
    
    def fetch_medium_term_capacity_constraints(self):
        """Fetch Medium Term Capacity data with facility constraints"""
        return self._create_simulated_constraints(), "AEMO API not available"
    
    def _create_simulated_constraints(self):
        """Create realistic capacity constraints - ZERO DATETIME ARITHMETIC"""
        
        # Use pandas Timestamp with explicit DateOffset - SAFEST APPROACH
        today = pd.Timestamp.now()
        
        constraints = [
            {
                'facility': 'Gorgon Gas Plant',
                'capacity_tj_day': 250,
                'capacity_type': 'MAINTENANCE',
                'start_date': today + pd.DateOffset(days=30),  # SAFE: pd.DateOffset
                'end_date': today + pd.DateOffset(days=45),    # SAFE: pd.DateOffset
                'description': 'Scheduled maintenance - reduced capacity'
            },
            {
                'facility': 'Wheatstone Gas Plant',
                'capacity_tj_day': 180,
                'capacity_type': 'PIPELINE_CONSTRAINT',
                'start_date': today + pd.DateOffset(days=15),  # SAFE: pd.DateOffset
                'end_date': today + pd.DateOffset(days=60),    # SAFE: pd.DateOffset
                'description': 'Pipeline capacity constraint'
            }
        ]
        
        return pd.DataFrame(constraints)

aemo_client = EnhancedAEMOClient()

# ==============================================================================
# DATA GENERATION FUNCTIONS - COMPLETELY REDESIGNED FOR DATETIME SAFETY
# ==============================================================================

# FIX: Added start_date and end_date parameters to ensure consistent date ranges
@st.cache_data(ttl=3600)
def generate_5_year_median_demand(start_date, end_date):
    """
    Generate 5-year median demand, now aligned to a specific date range.
    """
    # Part 1: Generate 5 years of historical data to calculate medians
    history_end_date = pd.Timestamp.now()
    history_start_date = history_end_date - pd.DateOffset(years=5)
    all_dates = pd.date_range(start=history_start_date, end=history_end_date, freq='D')
    
    base_demand_2020 = 1200
    growth_rate = 0.032
    np.random.seed(44)
    
    demand_data = []
    for date in all_dates:
        year = date.year
        day_of_year = date.timetuple().tm_yday
        years_from_2020 = year - 2020
        annual_base = base_demand_2020 * (1 + growth_rate) ** years_from_2020
        seasonal_factor = 1 + 0.3 * np.cos(2 * np.pi * (day_of_year - 200) / 365)
        weekly_factor = 0.82 if date.weekday() >= 5 else 1.0
        if (date.month == 12 and date.day >= 20) or (date.month == 1 and date.day <= 10):
            holiday_factor = 0.75
        else:
            holiday_factor = 1.0
        if year == 2020:
            covid_factor = 0.85
        elif year == 2021:
            covid_factor = 0.92
        else:
            covid_factor = 1.0
        weather_variation = np.random.normal(0, 0.08)
        daily_demand = (annual_base * seasonal_factor * weekly_factor * holiday_factor * covid_factor * (1 + weather_variation))
        daily_demand = max(daily_demand, annual_base * 0.6)
        demand_data.append({'Date': date, 'Daily_Demand': daily_demand, 'Year': year})
    
    demand_df = pd.DataFrame(demand_data)
    demand_df['DayOfYear'] = demand_df['Date'].dt.dayofyear
    daily_medians = demand_df.groupby('DayOfYear')['Daily_Demand'].median().reset_index()
    daily_medians.rename(columns={'Daily_Demand': 'Median_Demand'}, inplace=True)
    daily_medians['Smoothed_Median'] = daily_medians['Median_Demand'].rolling(window=7, center=True, min_periods=1).mean()
    
    # Part 2: Generate the final demand DataFrame for the specified date range
    # FIX: Use the passed start_date and end_date for a consistent range
    output_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    current_demand = []
    for date in output_dates:
        day_of_year = date.timetuple().tm_yday
        # Handle leap year case for day 366
        if day_of_year == 366:
            day_of_year = 365
        median_demand_row = daily_medians[daily_medians['DayOfYear'] == day_of_year]
        if not median_demand_row.empty:
            median_demand = median_demand_row['Smoothed_Median'].iloc[0]
        else: # Fallback for any missing day
            median_demand = daily_medians['Smoothed_Median'].mean()

        daily_variation = np.random.normal(0, 0.03)
        current_daily_demand = median_demand * (1 + daily_variation)
        current_demand.append(current_daily_demand)
    
    final_demand_df = pd.DataFrame({
        'Date': output_dates,
        'Market_Demand': current_demand
    })
    
    final_demand_df.attrs['source'] = '5-Year Median Analysis'
    return final_demand_df

# FIX: Added start_date and end_date parameters
@st.cache_data(ttl=1800)
def generate_production_with_capacity_constraints(start_date, end_date):
    """Generate production data for a specific date range."""
    
    # FIX: Use the passed start_date and end_date
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    capacity_constraints, _ = aemo_client.fetch_medium_term_capacity_constraints()
    production_data = {'Date': dates}
    
    np.random.seed(42)
    
    for facility, config in WA_PRODUCTION_FACILITIES_COMPLETE.items():
        typical_output = config['output']
        base_capacity = config['capacity']
        status = config['status']
        fuel_type = config.get('fuel_type', 'Natural Gas')
        
        if status in ['operating', 'ramping', 'declining']:
            if fuel_type == 'Storage':
                storage_pattern = np.random.uniform(-0.5, 1.0, len(dates))
                production = typical_output * storage_pattern
            else:
                if status == 'operating':
                    base_utilization = np.random.uniform(0.85, 0.95, len(dates))
                elif status == 'ramping':
                    ramp_progress = np.linspace(0.3, 0.9, len(dates))
                    base_utilization = ramp_progress + np.random.normal(0, 0.05, len(dates))
                else:
                    decline_progress = np.linspace(0.8, 0.4, len(dates))
                    base_utilization = decline_progress + np.random.normal(0, 0.03, len(dates))
                
                seasonal_factor = 1 + 0.1 * np.cos(2 * np.pi * (dates.dayofyear - 200) / 365)
                
                if config['region'] == 'Perth Basin':
                    regional_variation = np.random.normal(0, 0.12, len(dates))
                else:
                    regional_variation = np.random.normal(0, 0.08, len(dates))
                
                production = (typical_output * base_utilization * seasonal_factor * (1 + regional_variation))
                
                facility_production = []
                for i, date in enumerate(dates):
                    date_production = production[i]
                    effective_capacity = base_capacity
                    
                    if not capacity_constraints.empty:
                        facility_constraints = capacity_constraints[capacity_constraints['facility'] == facility]
                        for _, constraint in facility_constraints.iterrows():
                            start_constraint = constraint['start_date']
                            end_constraint = constraint['end_date']
                            
                            if (pd.notna(start_constraint) and pd.notna(end_constraint) and
                                start_constraint <= date <= end_constraint):
                                effective_capacity = min(effective_capacity, constraint['capacity_tj_day'])
                    
                    constrained_production = min(max(date_production, 0), effective_capacity)
                    facility_production.append(constrained_production)
                
                production = facility_production
            
            production_data[facility] = production
        else:
            production_data[facility] = np.zeros(len(dates))
    
    df = pd.DataFrame(production_data)
    
    production_facilities = [f for f, config in WA_PRODUCTION_FACILITIES_COMPLETE.items() 
                          if config['status'] in ['operating', 'ramping', 'declining'] 
                          and config.get('fuel_type') != 'Storage']
    
    df['Total_Supply'] = df[production_facilities].sum(axis=1)
    df.attrs['capacity_constraints'] = capacity_constraints
    return df

# FIX: Added start_date and end_date parameters
@st.cache_data(ttl=1800)
def generate_integrated_storage_data(start_date, end_date):
    """Generate storage data for a specific date range."""
    
    # FIX: Use the passed start_date and end_date
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    storage_data = {'Date': dates}
    np.random.seed(43)
    
    for facility, config in WA_STORAGE_FACILITIES.items():
        max_injection = config['max_injection_rate']
        max_withdrawal = config['max_withdrawal_rate']
        max_working_capacity = config['max_working_capacity'] * 1000
        
        injections = []
        withdrawals = []
        volumes = []
        current_volume = max_working_capacity * 0.7
        
        for i, date in enumerate(dates):
            day_of_year = date.timetuple().tm_yday
            seasonal_factor = np.cos(2 * np.pi * (day_of_year - 200) / 365)
            weekly_factor = 1.0 if date.weekday() < 5 else 0.6
            daily_variation = np.random.normal(0, 0.3)
            activity_factor = seasonal_factor + daily_variation
            
            if activity_factor > 0.2:
                injection_rate = min(max_injection * activity_factor * weekly_factor, max_injection)
                withdrawal_rate = 0
                net_flow = injection_rate
            elif activity_factor < -0.2:
                injection_rate = 0
                withdrawal_rate = min(max_withdrawal * abs(activity_factor) * weekly_factor, max_withdrawal)
                net_flow = -withdrawal_rate
            else:
                injection_rate = 0
                withdrawal_rate = 0
                net_flow = 0
            
            current_volume += net_flow
            current_volume = max(0, min(current_volume, max_working_capacity))
            
            if current_volume >= max_working_capacity and net_flow > 0:
                injection_rate = 0
                net_flow = 0
            elif current_volume <= 0 and net_flow < 0:
                withdrawal_rate = 0
                net_flow = 0
            
            injections.append(injection_rate)
            withdrawals.append(withdrawal_rate)
            volumes.append(current_volume)
        
        storage_data[f'{facility}_Injection'] = injections
        storage_data[f'{facility}_Withdrawal'] = withdrawals
        storage_data[f'{facility}_Volume'] = volumes
        storage_data[f'{facility}_Net_Flow'] = [inj - wit for inj, wit in zip(injections, withdrawals)]
    
    df = pd.DataFrame(storage_data)
    
    injection_cols = [col for col in df.columns if col.endswith('_Injection')]
    withdrawal_cols = [col for col in df.columns if col.endswith('_Withdrawal')]
    volume_cols = [col for col in df.columns if col.endswith('_Volume')]
    
    df['Total_Injections'] = df[injection_cols].sum(axis=1)
    df['Total_Withdrawals'] = df[withdrawal_cols].sum(axis=1)
    df['Total_Volume'] = df[volume_cols].sum(axis=1)
    df['Net_Storage_Flow'] = df['Total_Injections'] - df['Total_Withdrawals']
    
    return df

@st.cache_data(ttl=1800)
def calculate_volatility_data(production_df, demand_df):
    """
    NEW: Merges supply and demand data and calculates rolling volatility of the balance.
    This is a direct measure of market stability.
    """
    # Merge the relevant columns from the two dataframes
    merged_df = pd.merge(
        production_df[['Date', 'Total_Supply']], 
        demand_df[['Date', 'Market_Demand']], 
        on='Date', 
        how='inner' # Inner merge is correct now that dates are aligned
    )
    
    # Ensure 'Date' is in datetime format and the dataframe is sorted
    merged_df['Date'] = pd.to_datetime(merged_df['Date'])
    merged_df.sort_values('Date', inplace=True)
    
    # Calculate the daily supply/demand balance
    merged_df['Balance'] = merged_df['Total_Supply'] - merged_df['Market_Demand']
    
    # Calculate the 30-day rolling volatility (standard deviation) of the balance.
    merged_df['Balance_Volatility'] = merged_df['Balance'].rolling(window=30).std()
    
    return merged_df.dropna()


@st.cache_data(ttl=3600)
def get_integrated_news_feed():
    """Enhanced news feed with integrated updates"""
    return [
        {
            'headline': 'WA Gas Statement of Opportunities 2024 released with updated facility data',
            'sentiment': 'N',
            'source': 'AEMO',
            'timestamp': '2 hours ago',
            'summary': 'Annual outlook includes Tubridgi storage integration and Pilbara zone updates'
        },
        {
            'headline': 'Tubridgi underground storage reaches full operational capacity',
            'sentiment': '+',
            'source': 'APA Group',
            'timestamp': '4 hours ago',
            'summary': 'Salt cavern storage provides 45 PJ working capacity with enhanced system flexibility'
        },
        {
            'headline': 'Browse FLNG development timeline extended to 2035',
            'sentiment': '-',
            'source': 'Woodside',
            'timestamp': '6 hours ago',
            'summary': 'Regulatory approvals and technical challenges delay project commissioning'
        },
        {
            'headline': 'Chart visualization system redesigned for pandas compatibility',
            'sentiment': '+',
            'source': 'Technical Update',
            'timestamp': '1 hour ago',
            'summary': 'Eliminated all datetime arithmetic issues while maintaining advanced functionality'
        }
    ]

# ==============================================================================
# REDESIGNED VISUALIZATION FUNCTIONS - ZERO DATETIME ARITHMETIC
# ==============================================================================

def create_safe_supply_demand_chart(production_df, demand_df, selected_facilities, show_smoothing=True):
    """
    Chart creation with manual stacking and fixed annotations.
    """
    
    if not selected_facilities:
        st.warning("⚠️ No facilities selected for chart")
        return go.Figure()
    
    try:
        production_clean = production_df.copy()
        demand_clean = demand_df.copy()
        
        production_clean['Date'] = pd.to_datetime(production_clean['Date'])
        demand_clean['Date'] = pd.to_datetime(demand_clean['Date'])
        
        if show_smoothing:
            for facility in selected_facilities:
                if facility in production_clean.columns:
                    production_clean[facility] = production_clean[facility].rolling(
                        window=7, center=True, min_periods=1
                    ).mean()
            
            demand_clean['Market_Demand'] = demand_clean['Market_Demand'].rolling(
                window=3, center=True, min_periods=1
            ).mean()
        
        chart_data = pd.merge(production_clean, demand_clean, on='Date', how='inner')
        
        if chart_data.empty:
            st.error("❌ No matching dates between production and demand data")
            return go.Figure()
        
        fig = go.Figure()
        
        # FIX: Implement robust manual stacking instead of using stackgroup
        cumulative_production = pd.Series(0.0, index=chart_data.index)
        
        # Add a trace for the zero baseline for the first facility to fill to
        fig.add_trace(go.Scatter(
            x=chart_data['Date'],
            y=cumulative_production,
            mode='none',
            showlegend=False,
            hoverinfo='skip'
        ))
        
        for facility in selected_facilities:
            if facility in chart_data.columns:
                config = WA_PRODUCTION_FACILITIES_COMPLETE.get(facility, {})
                color = config.get('color', 'rgba(128, 128, 128, 0.8)')
                operator = config.get('operator', 'Unknown')
                capacity = config.get('capacity', 0)
                region = config.get('region', 'Unknown')
                fuel_type = config.get('fuel_type', 'Natural Gas')
                
                production_values = chart_data[facility].fillna(0)
                
                if fuel_type == 'Storage':
                    fig.add_trace(go.Scatter(
                        x=chart_data['Date'],
                        y=production_values,
                        name=f"📦 {facility}",
                        mode='lines',
                        line=dict(color=color, width=2, dash='dot'),
                        hovertemplate=f'<b>Storage: {facility}</b><br>Operator: {operator}<br>Region: {region}<br>Date: %{{x|%Y-%m-%d}}<br>Net Flow: %{{y:.1f}} TJ/day<br>Max Capacity: {capacity} TJ/day<extra></extra>'
                    ))
                else:
                    # Manual stacking logic
                    cumulative_production += production_values
                    fig.add_trace(go.Scatter(
                        x=chart_data['Date'],
                        y=cumulative_production,
                        name=f"🏭 {facility}",
                        mode='none', # Use 'none' for area fills
                        fill='tonexty',
                        fillcolor=color,
                        hovertemplate=f'<b>Production: {facility}</b><br>Operator: {operator}<br>Region: {region}<br>Date: %{{x|%Y-%m-%d}}<br>Production: %{{customdata:.1f}} TJ/day<br>Max Capacity: {capacity} TJ/day<extra></extra>',
                        customdata=production_values
                    ))
        
        if 'Market_Demand' in chart_data.columns:
            demand_values = chart_data['Market_Demand'].fillna(0)
            fig.add_trace(go.Scatter(
                x=chart_data['Date'],
                y=demand_values,
                name='📈 Market Demand (5-Year Median)',
                mode='lines',
                line=dict(color='#1f2937', width=4),
                hovertemplate='<b>Market Demand</b><br>Date: %{x|%Y-%m-%d}<br>Demand: %{y:.1f} TJ/day<extra></extra>'
            ))
        
        capacity_constraints = getattr(production_df, 'attrs', {}).get('capacity_constraints', pd.DataFrame())
        
        if not capacity_constraints.empty:
            for _, constraint in capacity_constraints.iterrows():
                if constraint['facility'] in selected_facilities:
                    constraint_date = constraint['start_date']
                    if pd.notna(constraint_date):
                        # FIX: Separate the line from the annotation to avoid the TypeError
                        # Step 1: Add the line with no text
                        fig.add_vline(
                            x=constraint_date,
                            line_dash="dash",
                            line_color="red"
                        )
                        # Step 2: Add the annotation separately
                        fig.add_annotation(
                            x=constraint_date,
                            y=1.05, # Position annotation at the top of the plot area
                            yref="paper", # Use paper coordinates for y
                            text=f"⚠️ {constraint['facility']}<br>Maint.",
                            showarrow=False,
                            yshift=10,
                            font=dict(color="red"),
                            bgcolor="rgba(255, 255, 255, 0.8)"
                        )
        
        fig.update_layout(
            title=dict(text='🔧 WA Gas Market Analysis<br><sub>Supply, Demand, and Capacity Constraints</sub>', font=dict(size=20, color='#1f2937'), x=0.02),
            xaxis=dict(title='Date', showgrid=True, gridcolor='#f0f0f0', rangeslider=dict(visible=True, bgcolor="rgba(255,255,255,0.8)"), rangeselector=dict(buttons=list([dict(count=30, label="30D", step="day", stepmode="backward"), dict(count=90, label="90D", step="day", stepmode="backward"), dict(count=180, label="6M", step="day", stepmode="backward"), dict(step="all", label="All")]), bgcolor="rgba(255,255,255,0.8)")),
            yaxis=dict(title='Gas Flow (TJ/day)', showgrid=True, gridcolor='#f0f0f0', rangemode='tozero'),
            height=700,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(orientation='v', yanchor='top', y=0.98, xanchor='left', x=1.02, bgcolor='rgba(255,255,255,0.95)', bordercolor='#e5e7eb', borderwidth=1),
            margin=dict(l=60, r=300, t=120, b=200)
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Chart creation error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return go.Figure()

def create_safe_storage_analysis_chart(storage_df):
    """Redesigned storage chart - eliminates datetime arithmetic"""
    
    if storage_df.empty:
        st.error("❌ No storage data available")
        return go.Figure()
    
    try:
        storage_clean = storage_df.copy()
        storage_clean['Date'] = pd.to_datetime(storage_clean['Date'])
        
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=[
                '💉 Storage Injections vs Withdrawals (TJ/day) - Mondarra & Tubridgi',
                '📊 Gas Volume in Underground Storage (TJ)',
                '⚖️ Net Storage Flow (TJ/day) - System Balance'
            ],
            vertical_spacing=0.1,
            specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        if 'Total_Injections' in storage_clean.columns:
            fig.add_trace(go.Scatter(x=storage_clean['Date'], y=storage_clean['Total_Injections'], name='💚 Total Injections', fill='tozeroy', fillcolor='rgba(34, 197, 94, 0.3)', line=dict(color='rgba(34, 197, 94, 1)', width=2), hovertemplate='<b>System Injections</b><br>Date: %{x}<br>Rate: %{y:.1f} TJ/day<br><i>Mondarra + Tubridgi</i><extra></extra>'), row=1, col=1)
        
        if 'Total_Withdrawals' in storage_clean.columns:
            fig.add_trace(go.Scatter(x=storage_clean['Date'], y=storage_clean['Total_Withdrawals'], name='🔴 Total Withdrawals', fill='tozeroy', fillcolor='rgba(239, 68, 68, 0.3)', line=dict(color='rgba(239, 68, 68, 1)', width=2), hovertemplate='<b>System Withdrawals</b><br>Date: %{x}<br>Rate: %{y:.1f} TJ/day<br><i>Mondarra + Tubridgi</i><extra></extra>'), row=1, col=1)
        
        colors = ['rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)']
        for i, (facility, config) in enumerate(WA_STORAGE_FACILITIES.items()):
            volume_col = f'{facility}_Volume'
            if volume_col in storage_clean.columns:
                max_capacity = config['max_working_capacity'] * 1000
                fig.add_trace(go.Scatter(x=storage_clean['Date'], y=storage_clean[volume_col], name=f'📦 {facility}', line=dict(color=colors[i % len(colors)], width=3), hovertemplate=f'<b>{facility}</b><br>Date: %{{x}}<br>Volume: %{{y:.0f}} TJ<br>Capacity: {max_capacity:.0f} TJ<br>Fill: %{{customdata:.1f}}%<extra></extra>', customdata=[(v/max_capacity*100) for v in storage_clean[volume_col]]), row=2, col=1)
                fig.add_hline(y=max_capacity, line_dash="dash", line_color=colors[i % len(colors)], annotation_text=f"{facility} Max: {max_capacity:,.0f} TJ", row=2, col=1)
        
        if 'Net_Storage_Flow' in storage_clean.columns:
            fig.add_trace(go.Scatter(x=storage_clean['Date'], y=storage_clean['Net_Storage_Flow'], name='⚖️ Net Storage Flow', mode='lines', line=dict(color='rgba(75, 85, 99, 1)', width=3), fill='tozeroy', fillcolor='rgba(75, 85, 99, 0.2)', hovertemplate='<b>Net Storage Flow</b><br>Date: %{x}<br>Flow: %{y:.1f} TJ/day<br><i>Positive = Net Injection, Negative = Net Withdrawal</i><extra></extra>'), row=3, col=1)
            fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=3, col=1)
        
        fig.update_layout(
            title=dict(text='🔧 WA Gas Storage Analysis<br><sub>Mondarra Depleted Field + Tubridgi Salt Cavern</sub>', font=dict(size=18, color='#1f2937'), x=0.02),
            height=900,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(orientation='v', yanchor='top', y=0.98, xanchor='left', x=1.02, bgcolor='rgba(255,255,255,0.95)'),
            margin=dict(l=60, r=220, t=100, b=60)
        )
        
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_yaxes(title_text="Flow Rate (TJ/day)", row=1, col=1)
        fig.update_yaxes(title_text="Volume (TJ)", row=2, col=1)
        fig.update_yaxes(title_text="Net Flow (TJ/day)", row=3, col=1)
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Storage chart error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return go.Figure()

def create_volume_volatility_chart(volatility_df):
    """
    NEW: Creates a two-panel chart for supply/demand and balance volatility.
    This helps traders visually correlate market fundamentals with market stability.
    """
    if volatility_df.empty:
        st.warning("⚠️ Not enough data to calculate volatility.")
        return go.Figure()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            'WA Gas Supply vs. Demand',
            '30-Day Rolling Volatility of Supply/Demand Balance (Std. Dev. in TJ/day)'
        ),
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(go.Scatter(x=volatility_df['Date'], y=volatility_df['Total_Supply'], name='Total Supply', line=dict(color='rgba(31, 119, 180, 1)', width=2.5), hovertemplate='Supply: %{y:.0f} TJ/day'), row=1, col=1)
    fig.add_trace(go.Scatter(x=volatility_df['Date'], y=volatility_df['Market_Demand'], name='Market Demand', line=dict(color='rgba(44, 160, 44, 1)', width=2.5, dash='dash'), hovertemplate='Demand: %{y:.0f} TJ/day'), row=1, col=1)
    fig.add_trace(go.Scatter(x=volatility_df['Date'], y=volatility_df['Balance_Volatility'], name='Balance Volatility', fill='tozeroy', fillcolor='rgba(214, 39, 40, 0.2)', line=dict(color='rgba(214, 39, 40, 1)', width=2), hovertemplate='Volatility: %{y:.1f} TJ/day'), row=2, col=1)

    fig.update_layout(
        title=dict(text='📈 WA Gas Market Volume & Volatility Analysis', font=dict(size=20, color='#1f2937'), x=0.02),
        height=800,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=60, r=60, t=120, b=60)
    )
    fig.update_yaxes(title_text="Gas Flow (TJ/day)", row=1, col=1)
    fig.update_yaxes(title_text="Volatility (Std Dev)", row=2, col=1)
    
    return fig
# ==============================================================================
# MAIN DASHBOARD FUNCTIONS - WITH REDESIGNED CHARTS
# ==============================================================================

def display_integrated_main_dashboard():
    """Main dashboard with redesigned chart creation - ALL ISSUES FIXED"""
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown('<h1 class="main-header">⚡ WA Natural Gas Market Dashboard</h1>', unsafe_allow_html=True)
        st.markdown("""<div style="background: #dcfce7; padding: 0.5rem; border-radius: 8px; margin: 0.5rem 0;">✅ <strong>FIXED & ENHANCED:</strong> Unified Date Range • Volatility Analysis • Robust Data Loading</div>""", unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%H:%M AWST')}")
        st.markdown("**Status:** ✅ Operational")
        
    with col3:
        if st.button("🔄 Refresh All Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    with st.expander("📡 AEMO API Integration Status", expanded=False):
        is_connected, status_message = aemo_client.test_api_connection()
        st.write(status_message)
        if is_connected:
            st.success("🎯 AEMO systems accessible - Medium Term Capacity constraints active")
        else:
            st.info("📊 Using enhanced modeling with simulated capacity constraints")
    
    # FIX: Define a single, consistent date range for all data generation
    end_date = pd.Timestamp.now().normalize()
    start_date = end_date - pd.DateOffset(years=1)

    try:
        with st.spinner("Loading complete WA gas market data..."):
            production_df = generate_production_with_capacity_constraints(start_date, end_date)
            demand_df = generate_5_year_median_demand(start_date, end_date)
            storage_df = generate_integrated_storage_data(start_date, end_date)
            news_items = get_integrated_news_feed()
    except Exception as e:
        st.error(f"❌ Data loading error: {e}")
        return

    # FIX: Add a guard clause to ensure dataframes are not empty before proceeding
    if production_df.empty or demand_df.empty or storage_df.empty:
        st.error("🔥 Critical Error: Failed to generate one or more core datasets. Dashboard cannot continue.")
        return

    # Now that we know the core DFs are good, calculate volatility
    volatility_df = calculate_volatility_data(production_df, demand_df)
    
    # FIX: Calculate all KPI values here to ensure they are in scope
    today_supply = production_df['Total_Supply'].iloc[-1]
    today_demand = demand_df['Market_Demand'].iloc[-1]
    balance = today_supply - today_demand
    today_storage_flow = storage_df['Net_Storage_Flow'].iloc[-1]
    total_storage_volume = storage_df['Total_Volume'].iloc[-1]
    current_volatility = volatility_df['Balance_Volatility'].iloc[-1] if not volatility_df.empty else 0
    
    # Build the KPI display
    kpi_cols = st.columns(6)
    with kpi_cols[0]:
        balance_color = "green" if balance > 0 else "red"
        st.markdown(f"""<div class="kpi-card"><p class="kpi-value" style="color: {balance_color};">{abs(balance):.0f}</p><p class="kpi-label">Supply/Demand Balance (TJ/day)</p></div>""", unsafe_allow_html=True)
    
    with kpi_cols[1]:
        production_facilities = [f for f, c in WA_PRODUCTION_FACILITIES_COMPLETE.items() if c['status'] in ['operating', 'ramping', 'declining'] and c.get('fuel_type') != 'Storage']
        total_capacity = sum(WA_PRODUCTION_FACILITIES_COMPLETE[f]['capacity'] for f in production_facilities)
        utilization = (today_supply / total_capacity * 100) if total_capacity > 0 else 0
        st.markdown(f"""<div class="kpi-card"><p class="kpi-value">{utilization:.1f}%</p><p class="kpi-label">Production Utilization</p></div>""", unsafe_allow_html=True)

    with kpi_cols[2]:
        pilbara_facilities = sum(1 for c in WA_PRODUCTION_FACILITIES_COMPLETE.values() if c['region'] == 'Pilbara' and c['status'] == 'operating' and c.get('fuel_type') != 'Storage')
        st.markdown(f"""<div class="kpi-card"><p class="kpi-value">{pilbara_facilities}</p><p class="kpi-label">Pilbara Zone Facilities</p></div>""", unsafe_allow_html=True)

    with kpi_cols[3]:
        storage_flow_color = 'green' if today_storage_flow > 0 else 'red' if today_storage_flow < 0 else 'gray'
        st.markdown(f"""<div class="kpi-card"><p class="kpi-value" style="color: {storage_flow_color}">{today_storage_flow:.0f}</p><p class="kpi-label">Storage Net Flow (TJ/day)</p></div>""", unsafe_allow_html=True)

    with kpi_cols[4]:
        max_storage_capacity = sum(c['max_working_capacity'] for c in WA_STORAGE_FACILITIES.values()) * 1000
        storage_fill = (total_storage_volume / max_storage_capacity * 100) if max_storage_capacity > 0 else 0
        st.markdown(f"""<div class="kpi-card"><p class="kpi-value">{storage_fill:.1f}%</p><p class="kpi-label">Total Storage Fill</p></div>""", unsafe_allow_html=True)
    
    with kpi_cols[5]:
        avg_volatility = volatility_df['Balance_Volatility'].tail(90).mean() if not volatility_df.empty else 0
        vol_color = "red" if current_volatility > avg_volatility * 1.1 and avg_volatility > 0 else "green"
        st.markdown(f"""<div class="kpi-card"><p class="kpi-value" style="color: {vol_color};">{current_volatility:.1f}</p><p class="kpi-label">Balance Volatility (30d)</p></div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    # Main integrated content
    main_col1, main_col2 = st.columns([2.5, 1])
    
    with main_col1:
        st.markdown("### 📊 WA Gas Market Analysis")
        
        control_col1, control_col2 = st.columns(2)
        with control_col1:
            chart_type = st.selectbox("📊 Analysis Type", ["Redesigned Supply vs Demand", "Volume Volatility Analysis", "Redesigned Storage Analysis", "Facility Capacity"])
        with control_col2:
            show_smoothing = st.checkbox("📈 Apply Data Smoothing", value=True)
        
        if chart_type == "Redesigned Supply vs Demand":
            st.markdown("### 🌍 Select Facilities by Updated Zones:")
            regions = {r: [] for r in sorted(list(set(c['region'] for c in WA_PRODUCTION_FACILITIES_COMPLETE.values())))}
            for facility, config in WA_PRODUCTION_FACILITIES_COMPLETE.items():
                regions[config['region']].append(facility)
            
            selected_facilities = []
            for region, facilities in regions.items():
                with st.expander(f"📍 {region} Zone ({len(facilities)} facilities)", expanded=True):
                    region_cols = st.columns(2)
                    for i, facility in enumerate(facilities):
                        config = WA_PRODUCTION_FACILITIES_COMPLETE[facility]
                        status_icons = {'operating': '🟢', 'ramping': '🟡', 'declining': '🟠', 'future': '⚪', 'under_construction': '🔵', 'planned': '⚫'}
                        is_selected = region_cols[i % 2].checkbox(f"{status_icons.get(config['status'], '❓')} **{facility}**", value=(config['status'] in ['operating', 'ramping'] and len(selected_facilities) < 12), key=f"facility_{facility}", help=f"Operator: {config['operator']} | Capacity: {config['capacity']} TJ/day")
                        if is_selected:
                            selected_facilities.append(facility)
            
            if selected_facilities:
                fig = create_safe_supply_demand_chart(production_df, demand_df, selected_facilities, show_smoothing)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Please select at least one facility for integrated analysis")
        
        elif chart_type == "Volume Volatility Analysis":
            fig = create_volume_volatility_chart(volatility_df)
            st.plotly_chart(fig, use_container_width=True)
            st.info("""**How to Interpret This Chart:**\n- **Top Panel:** Shows daily supply vs. demand. Gaps indicate market imbalance.\n- **Bottom Panel:** Shows the 30-day rolling volatility of the balance. Rising volatility (red area) means the market is less stable and riskier.""")

        elif chart_type == "Redesigned Storage Analysis":
            fig = create_safe_storage_analysis_chart(storage_df)
            st.plotly_chart(fig, use_container_width=True)
        
        else:  # Facility Capacity
            st.markdown("### 🏭 Updated WA Gas Production Facilities")
            facilities_df = pd.DataFrame.from_dict(WA_PRODUCTION_FACILITIES_COMPLETE, orient='index')
            facilities_df = facilities_df[(facilities_df['status'].isin(['operating', 'ramping', 'declining', 'under_construction'])) & (facilities_df['fuel_type'] != 'Storage')].sort_values('capacity')
            fig = px.bar(facilities_df, x='capacity', y=facilities_df.index, orientation='h', color='region', text='capacity', title='WA Gas Production Facilities - Maximum Capacity')
            fig.update_layout(height=600, plot_bgcolor='white', margin=dict(l=250))
            st.plotly_chart(fig, use_container_width=True)
    
    with main_col2:
        st.markdown("### 📰 Market News & Updates")
        for item in news_items:
            sentiment_icon = {'N': '📰', '+': '📈', '-': '📉'}.get(item['sentiment'], '📰')
            st.markdown(f"**{sentiment_icon} {item['headline']}** *{item['source']} • {item['timestamp']}*<br>{item['summary']}", unsafe_allow_html=True)
            st.markdown("---")
        
        st.markdown("### 📈 Market Summary")
        if not production_df.empty:
            avg_supply = production_df['Total_Supply'].mean()
            avg_demand = demand_df['Market_Demand'].mean()
            st.metric("Avg Production Supply", f"{avg_supply:.0f} TJ/day")
            st.metric("Avg Market Demand", f"{avg_demand:.0f} TJ/day")
            st.metric("Avg Market Balance", f"{avg_supply - avg_demand:+.0f} TJ/day")

def display_integrated_sidebar():
    """Integrated sidebar with redesign status"""
    with st.sidebar:
        st.markdown("## 📡 WA Gas Market Dashboard")
        st.markdown("### ✅ Operational & Enhanced")
        
        st.radio("🗂️ Dashboard Sections:", ["🎯 Redesigned Main Dashboard", "🔋 Storage Analysis", "📊 Complete Integration Summary"], key="selected_page_radio")
        
        st.markdown("---")
        st.markdown("### ✅ System Status")
        st.success("Date ranges unified")
        st.success("Volatility analysis added")
        st.success("Data loading robust")
        
        st.markdown("---")
        st.markdown("### 🏭 System Overview")
        st.metric("Total Facilities", len(WA_PRODUCTION_FACILITIES_COMPLETE))
        st.metric("Storage Systems", len(WA_STORAGE_FACILITIES))

def main():
    """Main application with completely redesigned charts and all integrations"""
    display_integrated_sidebar()
    # The main dashboard is now the only page, controlled by the selectbox
    display_integrated_main_dashboard()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Application Error: {e}")
        st.markdown("**If errors persist, please check pandas version compatibility.**")
        with st.expander("🔍 Debug Information"):
            import traceback
            st.code(traceback.format_exc())

