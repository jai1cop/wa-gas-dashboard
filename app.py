import streamlit as st
import pandas as pd
import plotly.express as px
import data_fetcher as dfc
from datetime import date

st.set_page_config("WA Gas Dashboard", layout="wide")
st.title("WA Gas Supply & Demand Dashboard")

# Load real AEMO data with bulletproof error handling
@st.cache_data(ttl=3600)
def load_real_data():
    try:
        result = dfc.get_model()
        # Multiple checks to ensure we always return a tuple
        if result is None:
            return pd.DataFrame(), pd.DataFrame()
        if not isinstance(result, tuple):
            return pd.DataFrame(), pd.DataFrame()
        if len(result) != 2:
            return pd.DataFrame(), pd.DataFrame()
        return result
    except Exception as e:
        print(f"[ERROR] load_real_data failed: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Sidebar controls
st.sidebar.header("Scenario Controls")

# Yara consumption slider with unique key to fix duplicate ID error
yara_val = st.sidebar.slider(
    "Yara Pilbara Fertilisers gas consumption (TJ/day)",
    min_value=0, max_value=100, value=80, step=5,
    help="Adjust Yara's gas consumption to see market impact",
    key="yara_consumption_slider"  # CRITICAL: Add unique key
)

# Manual refresh button
if st.sidebar.button("Refresh AEMO Data", key="refresh_button"):
    st.cache_data.clear()
    st.sidebar.success("Data refreshed!")

# Load data with multiple layers of protection
sup = pd.DataFrame()
model = pd.DataFrame()

try:
    result = load_real_data()
    if result is not None and isinstance(result, tuple) and len(result) == 2:
        sup, model = result
    else:
        st.error("Data loading returned invalid format")
        sup, model = pd.DataFrame(), pd.DataFrame()
except Exception as e:
    st.error(f"Critical error loading data: {e}")
    sup, model = pd.DataFrame(), pd.DataFrame()

# Ensure DataFrames are valid
if not isinstance(sup, pd.DataFrame):
    sup = pd.DataFrame()
if not isinstance(model, pd.DataFrame):
    model = pd.DataFrame()

# COMPREHENSIVE DEBUG SECTION
st.sidebar.write("**📊 Debug Information:**")
st.sidebar.write(f"Supply DataFrame shape: {sup.shape}")
st.sidebar.write(f"Model DataFrame shape: {model.shape}")

# Supply Debug
if not sup.empty:
    st.sidebar.write("**Supply Analysis:**")
    if 'GasDay' in sup.columns:
        st.sidebar.write(f"Supply date range: {sup['GasDay'].min()} to {sup['GasDay'].max()}")
    if 'FacilityName' in sup.columns:
        st.sidebar.write(f"Unique facilities: {sup['FacilityName'].nunique()}")
    if 'TJ_Available' in sup.columns:
        st.sidebar.write(f"Total TJ_Available sum: {sup['TJ_Available'].sum():.2f}")
        duplicates = sup.groupby(['GasDay', 'FacilityName']).size()
        duplicate_count = len(duplicates[duplicates > 1])
        st.sidebar.write(f"Duplicate facility-date entries: {duplicate_count}")
else:
    st.sidebar.error("❌ Supply DataFrame is EMPTY")

# DEMAND ANALYSIS DEBUG
st.sidebar.write("**📈 Demand Analysis Debug:**")
if not model.empty and 'TJ_Demand' in model.columns:
    demand_stats = model['TJ_Demand'].describe()
    st.sidebar.write("**Demand Statistics:**")
    st.sidebar.dataframe(demand_stats)
    
    avg_demand = model['TJ_Demand'].mean()
    max_demand = model['TJ_Demand'].max()
    min_demand = model['TJ_Demand'].min()
    
    st.sidebar.write(f"Average daily demand: {avg_demand:.1f} TJ/day")
    st.sidebar.write(f"Maximum daily demand: {max_demand:.1f} TJ/day")
    st.sidebar.write(f"Minimum daily demand: {min_demand:.1f} TJ/day")
    
    if avg_demand > 2000:
        st.sidebar.warning("⚠️ Demand seems high - typical WA demand is 1,000-1,500 TJ/day")
    elif avg_demand < 500:
        st.sidebar.warning("⚠️ Demand seems low - check data aggregation")
    else:
        st.sidebar.success("✅ Demand levels look reasonable")

# Raw demand data debug
try:
    flows_raw = dfc.fetch_csv("flows", force=False)
    if not flows_raw.empty and 'demand' in flows_raw.columns:
        st.sidebar.write("**Raw Flows Demand Debug:**")
        st.sidebar.write(f"Total raw demand records: {len(flows_raw)}")
        
        negative_demand = flows_raw[flows_raw['demand'] < 0]
        st.sidebar.write(f"Negative demand records: {len(negative_demand)}")
        
        if 'facilitytype' in flows_raw.columns:
            demand_by_type = flows_raw.groupby('facilitytype')['demand'].sum().sort_values(ascending=False)
            st.sidebar.write("**Demand by facility type:**")
            st.sidebar.dataframe(demand_by_type.head())
        
        high_demand = flows_raw[flows_raw['demand'] > 1000]
        st.sidebar.write(f"Records with >1000 TJ demand: {len(high_demand)}")
        
        if len(high_demand) > 0:
            st.sidebar.write("**Sample high demand records:**")
            st.sidebar.dataframe(high_demand[['facilityname', 'gasdate', 'demand']].head())
            
except Exception as e:
    st.sidebar.error(f"Demand debug error: {e}")

# Model Debug
if not model.empty:
    st.sidebar.write("**Model Analysis:**")
    if 'GasDay' in model.columns:
        st.sidebar.write(f"Model date range: {model['GasDay'].min()} to {model['GasDay'].max()}")
    if 'TJ_Available' in model.columns:
        total_supply = model['TJ_Available'].sum()
        st.sidebar.write(f"Total supply across all days: {total_supply:.2f} TJ")

# MAIN DASHBOARD LOGIC
if model.empty:
    st.error("No data available - using sample data")
    sample_data = {
        'Date': pd.date_range('2025-07-29', periods=30),
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
    
    # Apply Yara adjustment
    model_adj = model.copy()
    model_adj["TJ_Demand"] = model_adj["TJ_Demand"] + (yara_val - 80)
    model_adj["Shortfall"] = model_adj["TJ_Available"] - model_adj["TJ_Demand"]
    
    # Supply stack chart
    if not sup.empty and all(col in sup.columns for col in ['TJ_Available', 'FacilityName', 'GasDay']):
        try:
            sup_agg = sup.groupby(['GasDay', 'FacilityName'])['TJ_Available'].sum().reset_index()
            stack = sup_agg.pivot(index="GasDay", columns="FacilityName", values="TJ_Available")
            today_dt = pd.to_datetime(date.today())
            stack = stack.loc[stack.index >= today_dt]
            
            if not stack.empty:
                fig1 = px.area(stack,
                              labels={"value": "TJ/day", "GasDay": "Date", "variable": "Facility"},
                              title="WA Gas Supply by Facility (Stacked)")
                fig1.update_traces(hovertemplate="%{y:.0f} TJ<br>%{x|%d-%b-%Y}")
                
                fig1.add_scatter(x=model_adj["GasDay"], y=model_adj["TJ_Demand"],
                               mode="lines", name="Historical / Forecast Demand",
                               line=dict(color="black", width=3))
                
                shortfalls = model_adj[model_adj["Shortfall"] < 0]
                if not shortfalls.empty:
                    fig1.add_scatter(x=shortfalls["GasDay"], y=shortfalls["TJ_Demand"],
                                   mode="markers", name="Shortfall",
                                   marker=dict(color="red", size=7, symbol="x"))
                
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.warning("⚠️ No future supply data available for chart")
        except Exception as e:
            st.error(f"Error creating supply chart: {e}")
    else:
        st.error("❌ Supply data missing required columns for stacked chart")
    
    # Balance bar chart
    try:
        fig2 = px.bar(model_adj, x="GasDay", y="Shortfall",
                      color=model_adj["Shortfall"] >= 0,
                      color_discrete_map={True: "green", False: "red"},
                      labels={"Shortfall": "Supply-Demand Gap (TJ)"},
                      title="Daily Market Balance")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
        
        avg_shortfall = model_adj['Shortfall'].mean()
        if avg_shortfall < 0:
            st.warning(f"⚠️ Average daily shortfall: {abs(avg_shortfall):.1f} TJ/day")
        else:
            st.success(f"✅ Average daily surplus: {avg_shortfall:.1f} TJ/day")
        
    except Exception as e:
        st.error(f"Error creating balance chart: {e}")
    
    # Data table
    st.subheader("Daily Balance Summary")
    try:
        display_cols = ["GasDay", "TJ_Available", "TJ_Demand", "Shortfall"]
        available_cols = [col for col in display_cols if col in model_adj.columns]
        
        if available_cols:
            display_df = model_adj[available_cols].copy()
            
            rename_map = {
                "GasDay": "Date",
                "TJ_Available": "Available Supply (TJ)",
                "TJ_Demand": "Demand (TJ)",
                "Shortfall": "Balance (TJ)"
            }
            display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
            
            st.dataframe(display_df, use_container_width=True)
            
            if 'Available Supply (TJ)' in display_df.columns and 'Demand (TJ)' in display_df.columns:
                avg_supply = display_df['Available Supply (TJ)'].mean()
                avg_demand = display_df['Demand (TJ)'].mean()
                st.write(f"**Summary:** Average Supply: {avg_supply:.1f} TJ/day | Average Demand: {avg_demand:.1f} TJ/day")
                
        else:
            st.error("No suitable columns for data table")
            
    except Exception as e:
        st.error(f"Error creating data table: {e}")

# STATUS SUMMARY
st.sidebar.write("**🎯 Status Summary:**")
st.sidebar.write(f"Dashboard loaded: {'✅' if not model.empty else '❌'}")
st.sidebar.write(f"Supply data: {'✅' if not sup.empty else '❌'}")
st.sidebar.write(f"Demand data: {'✅' if not model.empty and 'TJ_Demand' in model.columns else '❌'}")

st.sidebar.info("💡 **Tip:** Check Streamlit Cloud logs (Manage app → Logs) for detailed [DEBUG] messages from data_fetcher.py")
