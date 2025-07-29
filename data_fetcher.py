import os
import requests
import pandas as pd
from datetime import datetime

# Use national source but filter to WA only
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
    """Extract WA facilities from national nameplate data"""
    print(f"[DEBUG] National nameplate input: {df.shape}")
    
    if df.empty or 'capacityquantity' not in df.columns:
        return pd.DataFrame(columns=["FacilityName", "TJ_Nameplate"])
    
    # Filter for WA facilities by location or facility name patterns
    wa_df = df.copy()
    if 'state' in df.columns:
        wa_df = df[df['state'].isin(['WA', 'wa', 'Western Australia'])]
        print(f"[DEBUG] Filtered by state to WA: {wa_df.shape}")
    elif 'deliverylocationname' in df.columns:
        # Filter by WA locations
        wa_locations = df[df['deliverylocationname'].str.contains(
            'WA|Western|Perth|Karratha|Dampier|Varanus|Macedon|Wheatstone|Gorgon|NWS|North West Shelf', 
            case=False, na=False
        )]
        wa_df = wa_locations
        print(f"[DEBUG] Filtered by WA location names: {wa_df.shape}")
    elif 'facilityname' in df.columns:
        # Filter by known WA facility names
        wa_facilities = df[df['facilityname'].str.contains(
            'Karratha|Varanus|Macedon|Wheatstone|Gorgon|NWS|North West Shelf|Dampier|Mondarra|Tubridgi|Devil Creek|Scarborough|Waitsia', 
            case=False, na=False
        )]
        wa_df = wa_facilities
        print(f"[DEBUG] Filtered by WA facility names: {wa_df.shape}")
    
    result = wa_df[['facilityname', 'capacityquantity']].copy()
    result.rename(columns={
        'facilityname': 'FacilityName',
        'capacityquantity': 'TJ_Nameplate'
    }, inplace=True)
    
    result = result.dropna()
    print(f"[DEBUG] WA Nameplate output: {result.shape} facilities")
    return result

def clean_mto(df):
    """Extract WA facilities from national MTO data"""
    print(f"[DEBUG] National MTO input: {df.shape}")
    
    if df.empty:
        return pd.DataFrame(columns=["FacilityName", "GasDay", "TJ_Available"])
    
    required_cols = ['facilityname', 'fromgasdate', 'outlookquantity']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"[WARNING] Missing MTO columns: {missing}")
        return pd.DataFrame(columns=["FacilityName", "GasDay", "TJ_Available"])

    # Filter for WA facilities
    wa_df = df.copy()
    if 'deliverylocationname' in df.columns:
        wa_locations = df[df['deliverylocationname'].str.contains(
            'WA|Western|Perth|Karratha|Dampier|Varanus|Macedon|Wheatstone|Gorgon|NWS|North West Shelf', 
            case=False, na=False
        )]
        wa_df = wa_locations
        print(f"[DEBUG] MTO filtered by WA locations: {wa_df.shape}")
    elif 'facilityname' in df.columns:
        wa_facilities = df[df['facilityname'].str.contains(
            'Karratha|Varanus|Macedon|Wheatstone|Gorgon|NWS|North West Shelf|Dampier|Mondarra|Tubridgi|Devil Creek|Scarborough|Waitsia', 
            case=False, na=False
        )]
        wa_df = wa_facilities
        print(f"[DEBUG] MTO filtered by WA facility names: {wa_df.shape}")
    
    wa_df['fromgasdate'] = pd.to_datetime(wa_df['fromgasdate'], errors="coerce")
    result = wa_df[['facilityname', 'fromgasdate', 'outlookquantity']].copy()
    result = result.dropna(subset=['fromgasdate'])
    
    result.rename(columns={
        'facilityname': 'FacilityName',
        'fromgasdate': 'GasDay',
        'outlookquantity': 'TJ_Available'
    }, inplace=True)
    
    # Aggregate duplicates
    result = result.groupby(['FacilityName', 'GasDay'])['TJ_Available'].sum().reset_index()
    
    print(f"[DEBUG] WA MTO output: {result.shape} records")
    return result

def build_supply_profile():
    """Build WA supply profile from national data"""
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
    """Build WA-only demand profile with relaxed filtering"""
    flows = fetch_csv("flows")
    print(f"[DEBUG] National flows input: {flows.shape}")
    
    if flows.empty or 'gasdate' not in flows.columns or 'demand' not in flows.columns:
        return pd.DataFrame(columns=["GasDay", "TJ_Demand"])

    flows['gasdate'] = pd.to_datetime(flows['gasdate'], errors="coerce")
    flows = flows.dropna(subset=['gasdate'])
    
    # RELAXED WA FILTERING - Less restrictive approach
    wa_flows = flows.copy()
    
    # Try multiple filtering approaches in order of preference
    if 'locationname' in flows.columns:
        # First try: Look for "whole wa" specifically
        whole_wa = flows[flows['locationname'].str.contains('whole wa', case=False, na=False)]
        if not whole_wa.empty:
            wa_flows = whole_wa
            print(f"[DEBUG] Found 'whole wa' location data: {wa_flows.shape}")
        else:
            # Second try: Broader WA location filtering
            wa_locations = flows[flows['locationname'].str.contains(
                'WA|Western Australia|wa', case=False, na=False
            )]
            if not wa_locations.empty:
                wa_flows = wa_locations
                print(f"[DEBUG] WA flows after location filter: {wa_flows.shape}")
            else:
                print("[DEBUG] No WA locations found, using proportional estimate")
    
    # If no location-based filtering worked, use proportional approach
    if wa_flows.shape[0] == flows.shape[0]:  # No filtering occurred
        print("[DEBUG] No WA filtering applied - using proportional estimate (15% of national)")
        # Filter for positive demand only first
        positive_flows = flows[flows['demand'] > 0].copy()
        
        # Aggregate national demand by date
        national_demand = positive_flows.groupby('gasdate')['demand'].sum().reset_index()
        
        # Apply WA proportion (approximately 15% of national gas demand)
        national_demand['demand'] = national_demand['demand'] * 0.15
        
        demand = national_demand.rename(columns={'gasdate': 'GasDay', 'demand': 'TJ_Demand'})
        
        print(f"[DEBUG] WA Proportional demand profile: {demand.shape}, avg daily: {demand['TJ_Demand'].mean():.1f} TJ")
        return demand
    
    # Process the filtered WA flows
    demand_flows = wa_flows[wa_flows['demand'] > 0].copy()
    print(f"[DEBUG] WA positive demand records: {len(demand_flows)}")
    
    if demand_flows.empty:
        print("[WARNING] No positive demand records after WA filtering - using proportional estimate")
        # Fallback to proportional approach
        positive_flows = flows[flows['demand'] > 0].copy()
        national_demand = positive_flows.groupby('gasdate')['demand'].sum().reset_index()
        national_demand['demand'] = national_demand['demand'] * 0.15
        demand = national_demand.rename(columns={'gasdate': 'GasDay', 'demand': 'TJ_Demand'})
        return demand
    
    # Aggregate demand by date
    demand = demand_flows.groupby('gasdate')['demand'].sum().reset_index()
    
    # Apply scaling if demand seems too high
    if demand['demand'].mean() > 3000:
        demand['demand'] = demand['demand'] / 2.0
        print("[DEBUG] Applied scaling for realistic WA demand levels")
    
    demand.rename(columns={'gasdate': 'GasDay', 'demand': 'TJ_Demand'}, inplace=True)
    
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
        print(f"[DEBUG] Used latest WA supply {supply_total} TJ for all demand dates")
