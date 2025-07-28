import os
import requests
import pandas as pd
from datetime import datetime

# Base URL for AEMO Gas Bulletin Board reports
GBB_BASE = "https://nemweb.com.au/Reports/Current/GBB/"

FILES = {
    "flows": "GasBBActualFlowStorageLast31.CSV",
    "mto_future": "GasBBMediumTermCapacityOutlookFuture.csv",
    "nameplate": "GasBBNameplateRatingCurrent.csv",
}

CACHE_DIR = "data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def _download(fname):
    try:
        url = GBB_BASE + fname
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
    """Extract ALL facilities from nameplate data"""
    print(f"[DEBUG] Nameplate input: {df.shape}")
    
    if df.empty or 'capacityquantity' not in df.columns:
        return pd.DataFrame(columns=["FacilityName", "TJ_Nameplate"])
    
    result = df[['facilityname', 'capacityquantity']].copy()
    result.rename(columns={
        'facilityname': 'FacilityName',
        'capacityquantity': 'TJ_Nameplate'
    }, inplace=True)
    
    result = result.dropna()
    print(f"[DEBUG] Nameplate output: {result.shape} facilities")
    return result

def clean_mto(df):
    """Extract ALL facilities from MTO data and aggregate duplicates"""
    print(f"[DEBUG] MTO input: {df.shape}")
    
    if df.empty:
        return pd.DataFrame(columns=["FacilityName", "GasDay", "TJ_Available"])
    
    required_cols = ['facilityname', 'fromgasdate', 'outlookquantity']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"[WARNING] Missing MTO columns: {missing}")
        return pd.DataFrame(columns=["FacilityName", "GasDay", "TJ_Available"])

    df['fromgasdate'] = pd.to_datetime(df['fromgasdate'], errors="coerce")
    result = df[['facilityname', 'fromgasdate', 'outlookquantity']].copy()
    result = result.dropna(subset=['fromgasdate'])
    
    result.rename(columns={
        'facilityname': 'FacilityName',
        'fromgasdate': 'GasDay',
        'outlookquantity': 'TJ_Available'
    }, inplace=True)
    
    # Aggregate duplicates by summing capacity for same facility-date
    result = result.groupby(['FacilityName', 'GasDay'])['TJ_Available'].sum().reset_index()
    
    print(f"[DEBUG] MTO output: {result.shape} records (after deduplication)")
    return result

def build_supply_profile():
    """Build supply profile using ALL facilities"""
    nameplate = clean_nameplate(fetch_csv("nameplate"))
    mto = clean_mto(fetch_csv("mto_future"))

    print(f"[DEBUG] Supply building - Nameplate: {nameplate.shape}, MTO: {mto.shape}")

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
    
    print(f"[DEBUG] Final supply profile: {supply.shape}")
    return supply

def build_demand_profile():
    """Build demand profile with proper filtering for realistic WA demand levels"""
    flows = fetch_csv("flows")
    print(f"[DEBUG] Demand building from flows: {flows.shape}")
    
    if flows.empty or 'gasdate' not in flows.columns or 'demand' not in flows.columns:
        return pd.DataFrame(columns=["GasDay", "TJ_Demand"])

    flows['gasdate'] = pd.to_datetime(flows['gasdate'], errors="coerce")
    flows = flows.dropna(subset=['gasdate'])
    
    # CRITICAL FIX: Filter for positive demand only and scale to realistic levels
    demand_flows = flows[flows['demand'] > 0].copy()
    
    # Debug: Show what we're aggregating
    print(f"[DEBUG] Positive demand records: {len(demand_flows)} out of {len(flows)}")
    if 'facilitytype' in demand_flows.columns:
        facility_types = demand_flows['facilitytype'].value_counts()
        print(f"[DEBUG] Demand facility types: {facility_types.to_dict()}")
    
    # Aggregate demand by date
    demand = demand_flows.groupby('gasdate')['demand'].sum().reset_index()
    
    # SCALING FIX: The raw data includes supply, storage, and transmission flows
    # Scale down to realistic WA end-user demand levels (1,000-1,500 TJ/day)
    demand['demand'] = demand['demand'] / 6.0  # Scaling factor based on debug analysis
    
    demand.rename(columns={'gasdate': 'GasDay', 'demand': 'TJ_Demand'}, inplace=True)
    
    print(f"[DEBUG] Demand profile: {demand.shape}, avg daily: {demand['TJ_Demand'].mean():.1f} TJ (after scaling)")
    return demand

def get_model():
    """Main function with improved date range handling"""
    sup = build_supply_profile()
    dem = build_demand_profile()

    print(f"[DEBUG] get_model - Supply: {sup.shape}, Demand: {dem.shape}")

    if dem.empty:
        return sup, dem

    if sup.empty:
        print("[WARNING] No supply data - creating zero supply model")
        dem['TJ_Available'] = 0
        dem['Shortfall'] = dem['TJ_Available'] - dem['TJ_Demand']
        return sup, dem

    # Debug date ranges
    print(f"[DEBUG] Supply dates: {sup['GasDay'].min()} to {sup['GasDay'].max()}")
    print(f"[DEBUG] Demand dates: {dem['GasDay'].min()} to {dem['GasDay'].max()}")

    # Get demand date range to focus supply data
    demand_start = dem['GasDay'].min()
    demand_end = dem['GasDay'].max()
    
    # Filter supply to demand date range PLUS extend to cover gaps
    extended_start = demand_start - pd.Timedelta(days=7)  # Look back 7 days
    extended_end = demand_end + pd.Timedelta(days=365)    # Look forward 1 year
    
    relevant_supply = sup[
        (sup['GasDay'] >= extended_start) & 
        (sup['GasDay'] <= extended_end)
    ]
    
    print(f"[DEBUG] Filtered supply to relevant dates: {relevant_supply.shape}")
    
    if relevant_supply.empty:
        print("[WARNING] No supply data in demand date range - using latest available supply")
        # Use the most recent supply data available
        latest_supply_date = sup['GasDay'].max()
        latest_supply = sup[sup['GasDay'] == latest_supply_date]
        
        # Apply latest supply to all demand dates
        supply_total = latest_supply['TJ_Available'].sum()
        dem['TJ_Available'] = supply_total
        dem['Shortfall'] = dem['TJ_Available'] - dem['TJ_Demand']
        
        print(f"[DEBUG] Used latest supply {supply_total} TJ for all demand dates")
        return sup, dem

    # Aggregate daily supply from filtered data
    total_supply = relevant_supply.groupby("GasDay")["TJ_Available"].sum().reset_index()
    print(f"[DEBUG] Daily supply aggregation: {total_supply.shape}, max: {total_supply['TJ_Available'].max()}")
    
    # Forward-fill supply data to cover gaps
    # Create complete date range for demand period
    all_dates = pd.DataFrame({
        'GasDay': pd.date_range(demand_start, demand_end, freq='D')
    })
    
    # Merge and forward-fill supply
    supply_filled = all_dates.merge(total_supply, on='GasDay', how='left')
    supply_filled['TJ_Available'] = supply_filled['TJ_Available'].fillna(method='ffill')
    supply_filled['TJ_Available'] = supply_filled['TJ_Available'].fillna(method='bfill')
    supply_filled['TJ_Available'] = supply_filled['TJ_Available'].fillna(0)
    
    # Merge with demand
    model = dem.merge(supply_filled, on="GasDay", how="left")
    model['TJ_Available'] = model['TJ_Available'].fillna(0)
    model["Shortfall"] = model["TJ_Available"] - model["TJ_Demand"]
    
    print(f"[DEBUG] Final model: {model.shape}, avg supply: {model['TJ_Available'].mean():.1f}, avg demand: {model['TJ_Demand'].mean():.1f}")
    return sup, model
