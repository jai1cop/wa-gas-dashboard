import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fetch_gbb_data import get_all_gbb_data

st.set_page_config(page_title="WA Gas Market Dashboard", page_icon="⛽", layout="wide")

@st.cache_data(ttl=3600)
def load_data():
    return get_all_gbb_data()

flows, outages, storage = load_data()

# --- Sidebar Controls ---
st.sidebar.header("Market Settings")
yara_value = st.sidebar.slider(
    "Yara Pilbara Fertilisers Gas Use (TJ/day)", 0, 100, 80, 1
)

dates = pd.to_datetime(flows['GasDate'])
date_min, date_max = dates.min(), dates.max()
date_range = st.sidebar.date_input(
    "Date Range", [date_min, date_max], min_value=date_min, max_value=date_max
)
st.sidebar.markdown(
    "Data auto-pulls from GBB WA (AEMO). All outages, flows, facilities, and storage included.\n"
    "[GBB Portal](https://gbbwa.aemo.com.au) | [Data Docs](https://aemo.com.au/energy-systems/gas/gas-bulletin-board-gbb/data-gbb/gas-flows)"
)

# --- DATE FILTER ---
flows = flows[(pd.to_datetime(flows['GasDate']) >= pd.to_datetime(date_range[0])) &
              (pd.to_datetime(flows['GasDate']) <= pd.to_datetime(date_range[1]))]
storage = storage[(pd.to_datetime(storage['GasDate']) >= pd.to_datetime(date_range[0])) &
                  (pd.to_datetime(storage['GasDate']) <= pd.to_datetime(date_range[1]))]

# --- Facilities and Future Plants Setup ---
facilities = list(sorted(flows['FacilityName'].unique()))
future_plants = {
    "Scarborough": {"start": pd.Timestamp("2025-11-01"), "cap": 180},
    "West Erregulla": {"start": pd.Timestamp("2026-07-01"), "cap": 100},
    "Waitsia": {"start": pd.Timestamp("2026-07-01"), "cap": 100},
    # Add more if needed
}

# --- Construct Supply Stack Data ---
stack = pd.pivot_table(
    flows, index='GasDate', columns='FacilityName', values='TotalEnergy', aggfunc='sum', fill_value=0
)
stack.index = pd.to_datetime(stack.index)

for name, conf in future_plants.items():
    if name not in stack.columns and stack.index.max() >= conf["start"]:
        stack[name] = 0
        stack.loc[conf["start"]:, name] = conf["cap"]

# Medium-term outages
if not outages.empty and "Facility" in outages.columns:
    outages['StartDate'] = pd.to_datetime(outages['StartDate'])
    outages['EndDate'] = pd.to_datetime(outages['EndDate'])
    for _, row in outages.iterrows():
        fac = row['Facility']
        start = row['StartDate']
        end = row['EndDate']
        avcap = row['AvailableCapacity']
        if fac in stack.columns:
            filt = (stack.index >= start) & (stack.index <= end)
            stack.loc[filt, fac] = avcap

# --- Storage withdrawals as supply overlay ---
if not storage.empty and 'Withdrawal' in storage.columns:
    withdrawals = storage.groupby('GasDate')['Withdrawal'].sum()
    withdrawals.index = pd.to_datetime(withdrawals.index)
    # pad reindex
    stack['Storage Withdrawal'] = withdrawals.reindex(stack.index, fill_value=0)

# --- Demand Preparation ---
if 'TotalConsumption' in flows.columns:
    demand_series = flows.groupby('GasDate')['TotalConsumption'].sum().reindex(stack.index, fill_value=0)
else:
    demand_series = pd.Series(index=stack.index, data=900)  # Placeholder if not available

base_yara = 80
demand_series = demand_series + (yara_value - base_yara)

# --- Market Balance Calculation ---
market_balance = stack.sum(axis=1) - demand_series
status_panel = ("LONG", "success") if market_balance.iloc[-1] >= 0 else ("SHORT", "error")
storage_inventory = None
if not storage.empty and 'Inventory' in storage.columns:
    storage_inventory = storage.groupby('GasDate')['Inventory'].sum().reindex(stack.index, fill_value=np.nan)

# --- MAIN LAYOUT ---
st.title("WA Gas Market Dashboard: Real-Time Facility, Storage, and Outage View")
st.subheader("Advanced Supply-Demand Analysis with Facility Constraints, Storage, and Yara Scenario Modeling")

col1, col2 = st.columns(2)
with col1:
    st.metric("Current Market Status", status_panel[0], delta=f"{market_balance.iloc[-1]:.0f} TJ/day", delta_color=status_panel[1])
with col2:
    if storage_inventory is not None:
        st.metric("Storage Inventory Now", f"{storage_inventory.iloc[-1]:.2f} PJ")

# --- AREA STACKED CHART ---
fig = go.Figure()
# Assign color per facility (customize as needed)
color_sequence = [
    "#2E91E5", "#F66095", "#1CA71C", "#FFBE0B", "#B12F49", "#EB89B5", "#222A2A",
    "#A3A7A8", "#FB7E00", "#03254E", "#31A2AC", "#3A2E39", "#C0345E", "#6F2DBD"
]
for i, fac in enumerate(stack.columns):
    fig.add_trace(go.Scatter(
        x=stack.index, y=stack[fac], name=fac,
        stackgroup='one', line=dict(width=0.5), fillcolor=color_sequence[i % len(color_sequence)]
    ))

# Demand
fig.add_trace(go.Scatter(
    x=stack.index, y=demand_series, name="Demand (inc. Yara Adj.)",
    mode="lines", line=dict(color='black', width=4, dash="solid")
))

# Outage overlays
if not outages.empty and all(k in outages.columns for k in ['Facility','StartDate','EndDate','AvailableCapacity']):
    for _, out in outages.iterrows():
        fig.add_vrect(
            x0=out['StartDate'], x1=out['EndDate'],
            fillcolor='red', opacity=0.15,
            annotation_text=f"{out['Facility']} Outage",
            annotation_position="top left"
        )

# Shortfall coloring below demand
gap = stack.sum(axis=1) - demand_series
short_idx = gap[gap < 0].index
if len(short_idx):
    fig.add_traces([
        go.Scatter(
            x=short_idx, y=[demand_series.loc[i] for i in short_idx],
            mode='lines', name='Shortfall', line=dict(color='red', width=3, dash='dot'),
            fill=None
        )
    ])

fig.update_layout(
    title="Total WA Gas Market: Supply Stack by Facility, Demand, Storage, and Outages",
    xaxis_title="Date", yaxis_title="TJ/day",
    legend_title="Facility/Source"
)
st.plotly_chart(fig, use_container_width=True)

# --- Storage Inventory Trend ---
if storage_inventory is not None:
    st.subheader("Storage Inventory (PJ)")
    st.line_chart(storage_inventory)

# --- Facility Outage Table ---
if not outages.empty:
    st.subheader("Facility Outages & Maintenance Timeline")
    st.dataframe(outages[['Facility','StartDate','EndDate','AvailableCapacity']], use_container_width=True)

# --- Export/Download ---
st.subheader("Download Data")
csv_out = stack.copy()
csv_out['MarketBalance'] = market_balance
csv_out['DemandAdj'] = demand_series
if storage_inventory is not None:
    csv_out['StorageInventory_PJ'] = storage_inventory
st.download_button("Export Data as CSV", csv_out.to_csv().encode(), "wa_gas_dashboard_data.csv", "text/csv")

st.caption("Live data integration from AEMO GBB WA, continuous outages/constraints monitoring, and dynamic Yara impact tool.")
