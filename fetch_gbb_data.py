import requests
import pandas as pd
from io import StringIO

def fetch_csv_from_aemo(url):
    r = requests.get(url)
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text))

def get_daily_flows():
    # Replace with latest AEMO endpoints or API token as needed
    url = 'https://gbbwa.aemo.com.au/data/export/FacilityDailyProduction'
    return fetch_csv_from_aemo(url)

def get_medium_term_constraints():
    url = 'https://gbbwa.aemo.com.au/data/export/MediumTermCapacityOutlook'
    return fetch_csv_from_aemo(url)

def get_storage_history():
    url = 'https://gbbwa.aemo.com.au/data/export/Storage'
    return fetch_csv_from_aemo(url)

def get_all_gbb_data():
    flows = get_daily_flows()
    capacities = get_medium_term_constraints()
    storage = get_storage_history()
    return flows, capacities, storage
