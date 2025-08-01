import pandas as pd
import requests
from datetime import datetime, date
import logging
import json
from typing import Optional, Dict, Any
import streamlit as st
from io import StringIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WA_GBB_API:
    """
    Western Australian Gas Bulletin Board API Client
    Uses official AEMO API endpoints - no authentication required
    """
    
    BASE_URL = "https://gbbwa.aemo.com.au/api/v1/report"
    
    # Report mapping based on API documentation
    REPORTS = {
        'actual_flows': 'actualFlow',
        'capacity_outlook': 'capacityOutlook', 
        'medium_term_capacity': 'mediumTermCapacity',
        'forecast_flows': 'forecastFlow',
        'end_user_consumption': 'endUserConsumption',
        'large_user_consumption': 'largeUserConsumption',
        'linepack_adequacy': 'linepackCapacityAdequacy',
        'trucked_gas': 'truckedGas',
        'storage': 'storageCapacity'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WA-Gas-Dashboard/1.0',
            'Accept': 'text/csv,application/json'
        })
    
    def fetch_report(self, report_name: str, gas_date: Optional[str] = None, 
                    format_type: str = 'csv') -> pd.DataFrame:
        """
        Fetch a report from the WA GBB API
        
        Args:
            report_name: Name of the report (key from REPORTS dict)
            gas_date: Specific date (YYYY-MM-DD) or None for current
            format_type: 'csv' or 'json'
        
        Returns:
            DataFrame with the report data or empty DataFrame if failed
        """
        
        if report_name not in self.REPORTS:
            logger.error(f"Unknown report: {report_name}. Available: {list(self.REPORTS.keys())}")
            return pd.DataFrame()
        
        api_report_name = self.REPORTS[report_name]
        
        # Build URL
        if gas_date:
            endpoint = f"{self.BASE_URL}/{api_report_name}/{gas_date}"
        else:
            endpoint = f"{self.BASE_URL}/{api_report_name}/current"
        
        if format_type == 'csv':
            endpoint += '.csv'
        
        try:
            logger.info(f"📡 Fetching {report_name} from: {endpoint}")
            
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            
            if format_type == 'csv':
                # Parse CSV directly into DataFrame
                df = pd.read_csv(StringIO(response.text))
                logger.info(f"✅ {report_name}: {len(df)} records loaded")
                
                # Add metadata
                df['data_source'] = 'WA_GBB_API'
                df['fetched_at'] = datetime.now().isoformat()
                df['gas_date_requested'] = gas_date or 'current'
                
                return df
            
            else:  # JSON format
                data = response.json()
                if isinstance(data, dict) and 'data' in data:
                    df = pd.DataFrame(data['data'])
                else:
                    df = pd.DataFrame(data)
                
                logger.info(f"✅ {report_name}: {len(df)} records loaded")
                
                # Add metadata
                df['data_source'] = 'WA_GBB_API'
                df['fetched_at'] = datetime.now().isoformat() 
                df['gas_date_requested'] = gas_date or 'current'
                
                return df
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API request failed for {report_name}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ Error parsing {report_name} data: {e}")
            return pd.DataFrame()

# Initialize API client
api_client = WA_GBB_API()

# Main data fetching functions
@st.cache_data(ttl=900)  # Cache for 15 minutes
def get_actual_flows(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get actual gas flows data"""
    result = api_client.fetch_report('actual_flows', gas_date)
    return result if result is not None else pd.DataFrame()

@st.cache_data(ttl=1800)  # Cache for 30 minutes  
def get_capacity_outlook(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get capacity outlook data"""
    result = api_client.fetch_report('capacity_outlook', gas_date)
    return result if result is not None else pd.DataFrame()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_medium_term_capacity(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get medium term capacity constraints"""
    result = api_client.fetch_report('medium_term_capacity', gas_date)
    return result if result is not None else pd.DataFrame()

@st.cache_data(ttl=1800)
def get_forecast_flows(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get forecast flows data"""
    result = api_client.fetch_report('forecast_flows', gas_date)
    return result if result is not None else pd.DataFrame()

@st.cache_data(ttl=1800)
def get_end_user_consumption(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get end user consumption data"""
    result = api_client.fetch_report('end_user_consumption', gas_date)
    return result if result is not None else pd.DataFrame()

@st.cache_data(ttl=1800)
def get_large_user_consumption(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get large user consumption data"""
    result = api_client.fetch_report('large_user_consumption', gas_date)
    return result if result is not None else pd.DataFrame()

@st.cache_data(ttl=3600)
def get_linepack_adequacy(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get linepack capacity adequacy data"""
    result = api_client.fetch_report('linepack_adequacy', gas_date)
    return result if result is not None else pd.DataFrame()

@st.cache_data(ttl=1800)
def get_trucked_gas(gas_date: Optional[str] = None) -> pd.DataFrame:
    """Get trucked gas data"""
    result = api_client.fetch_report('trucked_gas', gas_date)
    return result if result is not None else pd.DataFrame()

def get_all_current_data() -> Dict[str, pd.DataFrame]:
    """
    Get all current/latest data from WA GBB API
    Returns dictionary with all available datasets
    """
    logger.info("🚀 Fetching all current WA GBB data via API...")
    
    datasets = {
        'actual_flows': get_actual_flows(),
        'capacity_outlook': get_capacity_outlook(),
        'medium_term_capacity': get_medium_term_capacity(),
        'forecast_flows': get_forecast_flows(),
        'end_user_consumption': get_end_user_consumption(),
        'large_user_consumption': get_large_user_consumption(),
        'linepack_adequacy': get_linepack_adequacy(),
        'trucked_gas': get_trucked_gas()
    }
    
    # Log summary
    total_records = sum(len(df) for df in datasets.values() if not df.empty)
    logger.info(f"📊 Total records loaded: {total_records}")
    
    for name, df in datasets.items():
        if not df.empty:
            logger.info(f"   - {name}: {len(df)} records")
        else:
            logger.warning(f"   - {name}: No data available")
    
    return datasets
