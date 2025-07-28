import streamlit as st
import pandas as pd
import plotly.express as px
import data_fetcher as dfc
from datetime import date

st.set_page_config("WA Gas Dashboard", layout="wide")
st.title("WA Gas Supply & Demand Dashboard")

# Load real AEMO data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_real_data():
    try:
        return dfc.get_model()
    except Exception as e:
        st.error(f"Error loading AEMO data: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Sidebar controls
st.sidebar.header("Scenario Controls")

# Yara consumption slider
yara_val = st.sidebar.slider(
    "Yara Pilbara Fertilisers gas consumption (TJ/day)",
    min_value=0, max_value=100, value=80, step=5,
    help="Adjust Yara's gas consumption to see market impact"
)

# Manual refresh button
if st.sidebar.button("Refresh AEMO Data"):
    st.cache_data.clear()
    st.sidebar.success("Data refreshed!")

# Load data
sup, model = load_real_data()

# COMPREHENSIVE DEBUG SECTION
st.sidebar.write("**📊 Comprehensive Debug Information:**")
st.sidebar.write(f"Supply DataFrame shape: {sup.shape}")
st.sidebar.write(f"Model DataFrame shape: {model.shape}")

# SUPPLY AGGREGATION DEBUG - This is key for your zero supply issue
st.sidebar.write("**🔍 Supply Aggregation Debug:**")
if not sup.empty:
    st.sidebar.write("**Supply DataFrame Analysis:**")
    st.sidebar.write(f"Supply date range: {sup['GasDay'].min()} to {sup['GasDay'].max()}")
    st.sidebar.write(f"Unique facilities: {sup['FacilityName'].nunique()}")
    st.sidebar.write(f"Total TJ_Available sum: {sup['TJ_Available'].sum():.2f}")
    st.sidebar.write(f"Max daily TJ_Available: {sup['TJ_Available'].max():.2f}")
    
    # Show supply totals by date
    total_supply_debug = sup.groupby("GasDay")["TJ_Available"].sum().reset_index()
    st.sidebar.write(f"**Daily supply aggregation:** {len(total_supply_debug)} days")
    st.sidebar.write("Supply totals sample:")
    st.sidebar.dataframe(total_supply_debug.head())
    
    # Show top facilities
    facility_totals = sup.groupby('FacilityName')['TJ_Available'].sum().sort_values(ascending=False).head(5)
    st.sidebar.write("**Top 5 facilities by capacity:**")
    st.sidebar.dataframe(facility_totals)
    
    # Check for duplicates
    duplicates = sup.groupby(['GasDay', 'FacilityName']).size()
    duplicate_count = len(duplicates[duplicates > 1])
    st.sidebar.write(f"Duplicate facility-date entries: {duplicate_count}")
else:
    st.sidebar.error("❌ Supply DataFrame is completely empty")
    st.sidebar.write("This means build_supply_profile() returned no data")

# MODEL DEBUG - Check what happened in the merge
if not model.empty:
    st.sidebar.write("**📈 Model DataFrame Analysis:**")
    st.sidebar.write(f"Model date range: {model['GasDay'].min()} to {model['GasDay'].max()}")
    
    # Critical: Check TJ_Available values in model
    if 'TJ_Available' in model.columns:
        available_stats = model['TJ_Available'].describe()
        st.sidebar.write("**TJ_Available statistics in model:**")
        st.sidebar.dataframe(available_stats)
        
        zero_supply_days = len(model[model['TJ_Available'] == 0])
        st.sidebar.write(f"Days with zero supply: {zero_supply_days} out of {len(model)}")
        
        if zero_supply_days == len(model):
            st.sidebar.error("🚨 ALL DAYS HAVE ZERO SUPPLY - This is the problem!")
        
        # Show sample of model data
        st.sidebar.write("**Model data sample:**")
        st.sidebar.dataframe(model[['GasDay', 'TJ_Available', 'TJ_Demand']].head())
    else:
        st.sidebar.error("❌ No TJ_Available column in model")

# RAW DATA DEBUG
st.sidebar.write("**📁 Raw Data Verification:**")
try:
    # Check raw MTO data specifically
    mto_raw = dfc.fetch_csv("mto_future", force=False)
    st.sidebar.write(f"Raw MTO records: {mto_raw.shape[0]}")
    
    if not mto_raw.empty and 'outlookquantity' in mto_raw.columns:
        positive_capacity = mto_raw[mto_raw['outlookquantity'] > 0]
        st.sidebar.write(f"MTO records with positive capacity: {len(positive_capacity)}")
        st.sidebar.write(f"Max outlook quantity: {mto_raw['outlookquantity'].max()}")
        st.sidebar.write(f"Total outlook quantity: {mto_raw['outlookquantity'].sum()}")
        
        # Check date range in raw MTO
        if 'fromgasdate' in mto_raw.columns:
            mto_raw['fromgasdate'] = pd.to_datetime(mto_raw['fromgasdate'], errors='coerce')
            valid_dates = mto_raw.dropna(subset=['fromgasdate'])
            if not valid_dates.empty:
                st.sidebar.write(f"MTO date range: {valid_dates['fromgasdate'].min()} to {valid_dates['fromgasdate'].max()}")
    
    # Test individual cleaning functions
    st.sidebar.write("**🔧 Cleaning Function Results:**")
    nameplate_clean = dfc.clean_nameplate(dfc.fetch_csv("nameplate"))
    mto_clean = dfc.clean_mto(dfc.fetch_csv("mto_future"))
    demand_clean = dfc.build_demand_profile()
    
    st.sidebar.write(f"Clean nameplate: {nameplate_clean.shape}")
    st.sidebar.write(f"Clean MTO: {mto_clean.shape}")
    st.sidebar.write(f"Clean demand: {demand_clean.shape}")
    
    if not mto_clean.empty:
        st.sidebar.write(f"MTO clean max capacity: {mto_clean['TJ_Available'].max()}")
        st.sidebar.write(f"MTO clean total capacity: {mto_clean['TJ_Available'].sum()}")
    else:
        st.sidebar.error("❌ MTO cleaning returned empty - this is the root cause!")
        
except Exception as e:
    st.sidebar.error(f"Raw data debug error: {e}")

# MAIN DASHBOARD LOGIC
if model.empty:
    st.error("No data available - using sample data")
    # Sample data fallback
    sample_data = {
        'Date': pd.date_range('2025-07-28', periods=30),
        'Supply': [1800 + i*5 for i in range(30)],
        'Demand': [1600 + i*3 for i in range(30)]
    }
    df = pd.DataFrame(sample_data)
    df['Balance'] = df['Supply'] - df['Demand']
    
    fig = px.line(df, x='Date', y=['Supply', 'Demand'], 
                  title="Sample Gas Supply vs Demand")
    st.plotly_chart(fig, use_container_width=True)
    
else:
    st.success(f"✅ Loaded {len(model)} days of real AEMO data")
    
    # Check required columns
    required_cols = ['TJ_Demand', 'TJ_Available']
    missing_cols = [col for col in required_cols if col not in model.columns]
    
    if missing_cols:
        st.error(f"❌ Missing required columns: {missing_cols}")
        st.write("Available columns:", list(model.columns))
        st.stop()
    
    # ZERO SUPPLY WARNING
    if model['TJ_Available'].sum() == 0:
        st.error("🚨 **CRITICAL ISSUE: All supply values are zero!**")
        st.write("**Possible causes:**")
        st.write("1. Supply DataFrame is empty (check debug sidebar)")
        st.write("2. Date mismatch between supply and demand data")
        st.write("3. MTO cleaning function filtering out all records")
        st.write("4. All outlook quantities in raw data are zero/negative")
        st.write("**Check the debug information in sidebar for details**")
    
    # Apply Yara adjustment
    model_adj = model.copy()
    model_adj["TJ_Demand"] = model_adj["TJ_Demand"] + (yara_val - 80)
    model_adj["Shortfall"] = model_adj["TJ_Available"] - model_adj["TJ_Demand"]
    
    # Supply stack chart with duplicate handling
    if not sup.empty and all(col in sup.columns for col in ['TJ_Available', 'FacilityName', 'GasDay']):
        try:
            # Aggregate duplicate facility-date combinations
            sup_agg = sup.groupby(['GasDay', 'FacilityName'])['TJ_Available'].sum().reset_index()
            
            # Pivot for stacked area chart
            stack = sup_agg.pivot(index="GasDay", columns="FacilityName", values="TJ_Available")
            today_dt = pd.to_datetime(date.today())
            stack = stack.loc[stack.index >= today_dt]
            
            if not stack.empty:
                fig1 = px.area(stack,
                              labels={"value": "TJ/day", "GasDay": "Date", "variable": "Facility"},
                              title="WA Gas Supply by Facility (Stacked)")
                fig1.update_traces(hovertemplate="%{y:.0f} TJ<br>%{x|%d-%b-%Y}")
                
                # Add demand line
                fig1.add_scatter(x=model_adj["GasDay"], y=model_adj["TJ_Demand"],
                               mode="lines", name="Historical / Forecast Demand",
                               line=dict(color="black", width=3))
                
                # Add shortfall markers
                shortfalls = model_adj[model_adj["Shortfall"] < 0]
                if not shortfalls.empty:
                    fig1.add_scatter(x=shortfalls["GasDay"], y=shortfalls["TJ_Demand"],
                                   mode="markers", name="Shortfall",
                                   marker=dict(color="red", size=7, symbol="x"))
                
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.warning("⚠️ No future supply data available for chart")
                st.write("All supply data may be historical (before today)")
        except Exception as e:
            st.error(f"Error creating supply chart: {e}")
            # Show additional debug for chart error
            if not sup.empty:
                st.write("Supply data for chart debugging:")
                st.dataframe(sup.head())
    else:
        st.error("❌ Supply data missing required columns for stacked chart")
        st.write("**Required:** ['TJ_Available', 'FacilityName', 'GasDay']")
        if not sup.empty:
            st.write("**Available supply columns:**", list(sup.columns))
        else:
            st.write("**Supply DataFrame is empty - check debug sidebar**")
    
    # Supply-demand balance bar chart
    try:
        fig2 = px.bar(model_adj, x="GasDay", y="Shortfall",
                      color=model_adj["Shortfall"] >= 0,
                      color_discrete_map={True: "green", False: "red"},
                      labels={"Shortfall": "Supply-Demand Gap (TJ)"},
                      title="Daily Market Balance")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
        
        # Show balance statistics
        if model_adj['TJ_Available'].sum() == 0:
            st.warning("⚠️ All bars are red because supply is zero - see debug info above")
        
    except Exception as e:
        st.error(f"Error creating balance chart: {e}")
    
    # Data table
    st.subheader("Daily Balance Summary")
    try:
        display_cols = ["GasDay", "TJ_Available", "TJ_Demand", "Shortfall"]
        available_cols = [col for col in display_cols if col in model_adj.columns]
        
        if available_cols:
            display_df = model_adj[available_cols].copy()
            
            # Rename for display
            rename_map = {
                "GasDay": "Date",
                "TJ_Available": "Available Supply (TJ)",
                "TJ_Demand": "Demand (TJ)",
                "Shortfall": "Balance (TJ)"
            }
            display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
            
            st.dataframe(display_df, use_container_width=True)
            
            # Show summary statistics
            if 'Available Supply (TJ)' in display_df.columns:
                avg_supply = display_df['Available Supply (TJ)'].mean()
                max_supply = display_df['Available Supply (TJ)'].max()
                st.write(f"**Supply Statistics:** Average: {avg_supply:.1f} TJ/day, Maximum: {max_supply:.1f} TJ/day")
                
        else:
            st.error("No suitable columns for data table")
            
    except Exception as e:
        st.error(f"Error creating data table: {e}")

# FINAL DEBUG SUMMARY WITH ZERO SUPPLY FOCUS
st.sidebar.write("**🎯 Zero Supply Issue Summary:**")
st.sidebar.write(f"Dashboard loaded: {'✅' if not model.empty else '❌'}")
st.sidebar.write(f"Supply data present: {'✅' if not sup.empty else '❌'}")
st.sidebar.write(f"Model has TJ_Available: {'✅' if not model.empty and 'TJ_Available' in model.columns else '❌'}")

if not model.empty and 'TJ_Available' in model.columns:
    total_supply = model['TJ_Available'].sum()
    st.sidebar.write(f"Total supply across all days: {total_supply:.2f} TJ")
    if total_supply == 0:
        st.sidebar.error("🚨 ROOT CAUSE: Total supply is zero!")
        st.sidebar.write("Check MTO cleaning function and date ranges above")
    else:
        st.sidebar.success(f"✅ Supply data is working: {total_supply:.2f} TJ total")

# STREAMLIT CLOUD LOGS REMINDER
st.sidebar.info("💡 **Critical:** Check Streamlit Cloud logs (Manage app → Logs) for [DEBUG] messages from data_fetcher.py to see exactly where supply data is being lost!")
