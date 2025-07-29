import os
import requests
import pandas as pd
from datetime import datetime

# Base URL for AEMO Gas Bulletin Board WA reports
GBB_WA_BASE = "https://gbbwa.aemo.com.au/data/"

# CSV filenames for key WA datasets
FILES = {
    "flows": "ActualFlowStorage.csv",
    "nameplate": "NameplateRating.csv", 
    "mto_future": "MediumTermCapacityOutlook.csv",
}

# Local cache directory for downloads
CACHE_DIR = "data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def _download(fname):
    try:
        url = GBB_WA_BASE + fname
        response = requests.get(url, timeout=40)
        response.raise_for_status()

        text = response.text.strip().lower()
        if text.startswith("<!doctype html") or text.startswith("<html"):
            raise ValueError(f"{url} returned HTML page, not CSV data")

        path = os.path.join(CACHE_DIR, fname)
        with open(path, "wb") as f:
            f.write(response.content)
        return path

    except Exception as e:
        print(f"[ERROR] Failed to download {fname}: {e}")
        error_path = os.path.join(CACHE_DIR, fname)
        if os.path.exists(error_path):
            os.remove(error_path)
        raise

def _stale(path):
    if not os.path.exists(path):
        return True
    last_modified = datetime.utcfromtimestamp(os.path.getmtime(path))
    return (datetime.utcnow() - last_modified).days > 0

def fetch_csv(key, force=False):
    try:
        fname = FILES[key]
        fpath = os.path.join(CACHE_DIR, fname)
        
        if force or _stale(fpath):
            fpath = _download(fname)

        df = pd.read_csv(fpath)
        df.columns = df.columns.str.lower()
        return df

    except Exception as e:
        print(f"[ERROR] Could not load {key}: {e}")
        return pd.DataFrame()

def clean_nameplate(df):
    """Extract facilities from WA nameplate data"""
    print(f"[DEBUG] WA Nameplate input: {df.shape}")
    
    if df.empty:
        return pd.DataFrame(columns=["FacilityName", "TJ_Nameplate"])
    
    # Look for capacity columns in WA data structure
    capacity_col = None
    for col in ['nameplaterating', 'capacityquantity', 'capacity', 'rating']:
        if col in df.columns:
            capacity_col = col
            break
    
    if capacity_col is None or 'facilityname' not in df.columns:
        print(f"[WARNING] Required columns not found in WA nameplate data")
        print(f"Available columns: {list(df.columns)}")
        return pd.DataFrame(columns=["FacilityName", "TJ_Nameplate"])
    
    result = df[['facilityname', capacity_col]].copy()
    result.rename(columns={
        'facilityname': 'FacilityName',
        capacity_col: 'TJ_Nameplate'
    }, inplace=True)
    
    result = result.dropna()
    print(f"[DEBUG] WA Nameplate output: {result.shape} facilities")
    return result

def clean_mto(df):
    """Extract facilities from WA MTO data"""
    print(f"[DEBUG] WA MTO input: {df.shape}")
    
    if df.empty:
        return pd.DataFrame(columns=["FacilityName", "GasDay", "TJ_Available"])
    
    # Look for required columns in WA MTO structure
    date_col = None
    for col in ['gasday', 'fromgasday', 'gasdate', 'date']:
        if col in df.columns:
            date_col = col
            break
    
    capacity_col = None
    for col in ['capacity', 'availablecapacity', 'outlookquantity', 'quantity']:
        if col in df.columns:
            capacity_col = col
            break
    
    if not all([date_col, capacity_col, 'facilityname' in df.columns]):
        print(f"[WARNING] Required columns not found in WA MTO data")
        print(f"Available columns: {list(df.columns)}")
        return pd.DataFrame(columns=["FacilityName", "GasDay", "TJ_Available"])

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    result = df[['facilityname', date_col, capacity_col]].copy()
    result = result.dropna(subset=[date_col])
    
    result.rename(columns={
        'facilityname': 'FacilityName',
        date_col: 'GasDay',
        capacity_col: 'TJ_Available'
    }, inplace=True)
    
    # Aggregate duplicates
    result = result.groupby(['FacilityName', 'GasDay'])['TJ_Available'].sum().reset_index()
    
    print(f"[DEBUG] WA MTO output: {result.shape} records")
    return result

def build_supply_profile():
    """Build WA supply profile"""
    nameplate = clean_nameplate(fetch_csv("nameplate"))
    mto = clean_mto(fetch_csv("mto_future"))

    print(f"[DEBUG] WA Supply building - Nameplate: {nameplate.shape}, MTO: {mto.shape}")

    if nameplate.empty and mto.empty:
        return pd.DataFrame(columns=["FacilityName", "GasDay", "TJ_Available", "TJ_Nameplate"])
    
    # If no MTO data, create future dates with nameplate capacity
    if mto.empty and not nameplate.empty:
        dates = pd.date_range(start=pd.Timestamp.now(), periods=365, freq='D')
        supply_list = []
        for _, facility in nameplate.iterrows():
            for date in dates:
                supply_list.append({
                    'FacilityName': facility['FacilityName'],
                    'GasDay': date,
                    'TJ_Available': facility['TJ_Nameplate'],
                    'TJ_Nameplate': facility['TJ_Nameplate']
                })
        return pd.DataFrame(supply_list)

    # If no nameplate data, use MTO only
    if nameplate.empty and not mto.empty:
        mto['TJ_Nameplate'] = mto['TJ_Available']
        return mto

    # Merge nameplate and MTO
    supply = mto.merge(nameplate, on="FacilityName", how="left")
    supply["TJ_Available"] = supply["TJ_Available"].fillna(supply["TJ_Nameplate"])
    
    print(f"[DEBUG] WA Final supply profile: {supply.shape}")
    return supply

def build_demand_profile():
    """Build WA demand profile from flows data"""
    flows = fetch_csv("flows")
    print(f"[DEBUG] WA Demand building from flows: {flows.shape}")
    
    if flows.empty:
        return pd.DataFrame(columns=["GasDay", "TJ_Demand"])

    # Look for date and demand columns in WA flows structure
    date_col = None
    for col in ['gasday', 'gasdate', 'date']:
        if col in flows.columns:
            date_col = col
            break
    
    demand_col = None
    for col in ['demand', 'consumption', 'usage', 'flow']:
        if col in flows.columns:
            demand_col = col
            break
    
    if not all([date_col, demand_col]):
        print(f"[WARNING] Required columns not found in WA flows data")
        print(f"Available columns: {list(flows.columns)}")
        return pd.DataFrame(columns=["GasDay", "TJ_Demand"])

    flows[date_col] = pd.to_datetime(flows[date_col], errors="coerce")
    flows = flows.dropna(subset=[date_col])
    
    # Filter for positive demand only
    demand_flows = flows[flows[demand_col] > 0].copy()
    
    print(f"[DEBUG] WA Positive demand records: {len(demand_flows)} out of {len(flows)}")
    
    # Aggregate demand by date (WA data should already be WA-specific)
    demand = demand_flows.groupby(date_col)[demand_col].sum().reset_index()
    demand.rename(columns={date_col: 'GasDay', demand_col: 'TJ_Demand'}, inplace=True)
    
    print(f"[DEBUG] WA Demand profile: {demand.shape}, avg daily: {demand['TJ_Demand'].mean():.1f} TJ")
    return demand

def get_model():
    """Main function for WA gas market model"""
    sup = build_supply_profile()
    dem = build_demand_profile()

    print(f"[DEBUG] WA get_model - Supply: {sup.shape}, Demand: {dem.shape}")

    if dem.empty:
        return sup, dem

    if sup.empty:
        print("[WARNING] No WA supply data - creating zero supply model")
        dem['TJ_Available'] = 0
        dem['Shortfall'] = dem['TJ_Available'] - dem['TJ_Demand']
        return sup, dem

    print(f"[DEBUG] WA Supply dates: {sup['GasDay'].min()} to {sup['GasDay'].max()}")
    print(f"[DEBUG] WA Demand dates: {dem['GasDay'].min()} to {dem['GasDay'].max()}")

    # Get demand date range
    demand_start = dem['GasDay'].min()
    demand_end = dem['GasDay'].max()
    
    # Filter supply to demand date range
    extended_start = demand_start - pd.Timedelta(days=7)
    extended_end = demand_end + pd.Timedelta(days=365)
    
    relevant_supply = sup[
        (sup['GasDay'] >= extended_start) & 
        (sup['GasDay'] <= extended_end)
    ]
    
    print(f"[DEBUG] WA Filtered supply: {relevant_supply.shape}")
    
    if relevant_supply.empty:
        # Use latest available supply
        latest_supply_date = sup['GasDay'].max()
        latest_supply = sup[sup['GasDay'] == latest_supply_date]
        supply_total = latest_supply['TJ_Available'].sum()
        dem['TJ_Available'] = supply_total
        dem['Shortfall'] = dem['TJ_Available'] - dem['TJ_Demand']
        return sup, dem

    # Aggregate daily supply
    total_supply = relevant_supply.groupby("GasDay")["TJ_Available"].sum().reset_index()
    
    # Create complete date range and forward-fill
    all_dates = pd.DataFrame({
        'GasDay': pd.date_range(demand_start, demand_end, freq='D')
    })
    
    supply_filled = all_dates.merge(total_supply, on='GasDay', how='left')
    supply_filled['TJ_Available'] = supply_filled['TJ_Available'].fillna(method='ffill')
    supply_filled['TJ_Available'] = supply_filled['TJ_Available'].fillna(method='bfill')
    supply_filled['TJ_Available'] = supply_filled['TJ_Available'].fillna(0)
    
    # Merge with demand
    model = dem.merge(supply_filled, on="GasDay", how="left")
    model['TJ_Available'] = model['TJ_Available'].fillna(0)
    model["Shortfall"] = model["TJ_Available"] - model["TJ_Demand"]
    
    print(f"[DEBUG] WA Final model: {model.shape}, avg supply: {model['TJ_Available'].mean():.1f}, avg demand: {model['TJ_Demand'].mean():.1f}")
    return sup, model
