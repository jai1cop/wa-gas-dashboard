import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import time
from io import StringIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_static_content(url, page_name):
    """
    Scrape static HTML content without browser automation
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        logger.info(f"Fetching {page_name} from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for tables in the static HTML
        tables = soup.find_all('table')
        for table in tables:
            try:
                df = pd.read_html(str(table))[0]
                if not df.empty and df.shape[1] > 1:
                    logger.info(f"✅ Found data in {page_name} - Shape: {df.shape}")
                    return df
            except:
                continue
        
        # If no tables, try to find CSV links or data URLs
        csv_links = soup.find_all('a', href=lambda x: x and '.csv' in x.lower())
        for link in csv_links:
            try:
                csv_url = link.get('href')
                if not csv_url.startswith('http'):
                    csv_url = 'https://gbbwa.aemo.com.au' + csv_url
                
                csv_response = requests.get(csv_url, headers=headers, timeout=30)
                csv_response.raise_for_status()
                df = pd.read_csv(StringIO(csv_response.text))
                
                if not df.empty:
                    logger.info(f"✅ Found CSV data for {page_name} - Shape: {df.shape}")
                    return df
            except:
                continue
        
        logger.warning(f"⚠️ No data found for {page_name}")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"❌ Error fetching {page_name}: {e}")
        return pd.DataFrame()

def try_api_endpoints():
    """
    Try common API endpoints that might work
    """
    endpoints = {
        'flows': [
            'https://gbbwa.aemo.com.au/api/flows.json',
            'https://gbbwa.aemo.com.au/data/flows.csv',
            'https://gbbwa.aemo.com.au/export/flows.csv'
        ],
        'capacity': [
            'https://gbbwa.aemo.com.au/api/capacity.json',
            'https://gbbwa.aemo.com.au/data/capacity.csv',
            'https://gbbwa.aemo.com.au/export/capacity.csv'
        ],
        'storage': [
            'https://gbbwa.aemo.com.au/api/storage.json',
            'https://gbbwa.aemo.com.au/data/storage.csv',
            'https://gbbwa.aemo.com.au/export/storage.csv'
        ]
    }
    
    results = {}
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; DataBot/1.0)'}
    
    for data_type, urls in endpoints.items():
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    if '.json' in url:
                        data = response.json()
                        df = pd.DataFrame(data)
                    else:
                        df = pd.read_csv(StringIO(response.text))
                    
                    if not df.empty:
                        logger.info(f"✅ API endpoint found for {data_type}: {url}")
                        results[data_type] = df
                        break
            except:
                continue
        
        if data_type not in results:
            results[data_type] = pd.DataFrame()
    
    return results['flows'], results['capacity'], results['storage']

def get_daily_flows():
    """Try multiple methods to get flows data"""
    # Method 1: Try direct page scraping
    df = scrape_static_content("https://gbbwa.aemo.com.au/#flows", "Daily Flows")
    if not df.empty:
        return df
    
    # Method 2: Try API endpoints
    flows, _, _ = try_api_endpoints()
    return flows

def get_medium_term_constraints():
    """Try multiple methods to get capacity data"""
    df = scrape_static_content("https://gbbwa.aemo.com.au/#reports/mediumTermCapacity", "Medium Term Capacity")
    if not df.empty:
        return df
    
    _, capacity, _ = try_api_endpoints()
    return capacity

def get_storage_history():
    """Try multiple methods to get storage data"""
    df = scrape_static_content("https://gbbwa.aemo.com.au/#reports/actualFlow", "Storage Data")
    if not df.empty:
        return df
    
    _, _, storage = try_api_endpoints()
    return storage

def get_all_gbb_data():
    """Get all data using Streamlit Cloud compatible methods"""
    logger.info("🌐 Starting data collection (Streamlit Cloud compatible)")
    
    flows = get_daily_flows()
    constraints = get_medium_term_constraints()
    storage = get_storage_history()
    
    logger.info(f"📊 Data collection complete - Flows: {flows.shape}, Constraints: {constraints.shape}, Storage: {storage.shape}")
    
    return flows, constraints, storage
