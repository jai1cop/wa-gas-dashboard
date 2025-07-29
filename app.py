import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import logging
import os

# Import data fetcher with error handling
try:
    from data_fetcher import fetch_csv, validate_dataframe, get_sample_data
    DATA_FETCHER_AVAILABLE = True
except ImportError:
    DATA_FETCHER_AVAILABLE = False
    logging.warning("⚠️ data_fetcher module not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GasDashboardDataLoader:
    """Handle all data loading operations for the gas dashboard"""
    
    def __init__(self):
        self.supply_df = pd.DataFrame()
        self.demand_df = pd.DataFrame()
        self.flows_df = pd.DataFrame()
        self.prices_df = pd.DataFrame()
        self.data_loaded = False
    
    def generate_sample_gas_data(self) -> dict:
        """Generate realistic sample gas market data"""
        logger.info("📊 Generating sample gas market data...")
        
        # Generate date range for last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate realistic gas supply data
        base_supply = 1000
        supply_data = []
        for date in dates:
            daily_supply = base_supply + np.random.normal(0, 50) + 100 * np.sin(2 * np.pi * date.dayofyear / 365)
            supply_data.append({
                'Date': date,
                'Supply': max(daily_supply, 800),  # Minimum supply threshold
                'Source': np.random.choice(['Gas Field A', 'Gas Field B', 'LNG Import'], p=[0.6, 0.3, 0.1]),
                'Region': 'Western Australia'
            })
        
        # Generate realistic gas demand data
        base_demand = 950
        demand_data = []
        for date in dates:
            # Higher demand in winter months (June-August in Australia)
            seasonal_factor = 1.2 if date.month in [6, 7, 8] else 1.0
            daily_demand = (base_demand * seasonal_factor + 
                          np.random.normal(0, 40) + 
                          80 * np.sin(2 * np.pi * date.dayofyear / 365))
            demand_data.append({
                'Date': date,
                'Demand': max(daily_demand, 700),  # Minimum demand threshold
                'Sector': np.random.choice(['Industrial', 'Commercial', 'Residential'], p=[0.5, 0.3, 0.2]),
                'Region': 'Western Australia'
            })
        
        # Generate gas flow data
        flows_data = []
        for date in dates:
            flows_data.append({
                'Date': date,
                'Pipeline_Flow': np.random.uniform(800, 1200),
                'Storage_Level': np.random.uniform(60, 90),  # Percentage
                'Import_Volume': np.random.uniform(0, 100),
                'Export_Volume': np.random.uniform(50, 200)
            })
        
        # Generate price data
        base_price = 12.50  # $/GJ
        prices_data = []
        for date in dates:
            price_volatility = np.random.normal(0, 1.5)
            daily_price = max(base_price + price_volatility, 8.0)  # Minimum price floor
            prices_data.append({
                'Date': date,
                'Price_GJ': daily_price,
                'Market': 'WA Gas Market',
                'Currency': 'AUD'
            })
        
        return {
            'supply': pd.DataFrame(supply_data),
            'demand': pd.DataFrame(demand_data),
            'flows': pd.DataFrame(flows_data),
            'prices': pd.DataFrame(prices_data)
        }
    
    def load_real_data(self) -> dict:
        """Load real data from CSV files"""
        logger.info("📁 Attempting to load real data files...")
        
        data_files = {
            'supply': 'data/supply_data.csv',
            'demand': 'data/demand_data.csv',
            'flows': 'data/flows_data.csv',
            'prices': 'data/prices_data.csv'
        }
        
        loaded_data = {}
        
        for data_type, file_path in data_files.items():
            try:
                if DATA_FETCHER_AVAILABLE:
                    df = fetch_csv(file_path)
                else:
                    if os.path.exists(file_path):
                        df = pd.read_csv(file_path)
                        logger.info(f"✅ Loaded {file_path}")
                    else:
                        logger.error(f"❌ File not found: {file_path}")
                        df = pd.DataFrame()
                
                loaded_data[data_type] = df
            except Exception as e:
                logger.error(f"❌ Error loading {file_path}: {e}")
                loaded_data[data_type] = pd.DataFrame()
        
        return loaded_data
    
    def load_data(self, use_sample_data: bool = True) -> dict:
        """Load all required datasets"""
        if use_sample_data:
            data = self.generate_sample_gas_data()
        else:
            data = self.load_real_data()
            # If real data loading fails, fall back to sample data
            if all(df.empty for df in data.values()):
                logger.warning("⚠️ Real data loading failed, using sample data")
                data = self.generate_sample_gas_data()
        
        self.supply_df = data['supply']
        self.demand_df = data['demand']
        self.flows_df = data['flows']
        self.prices_df = data['prices']
        
        self.data_loaded = not all(df.empty for df in [self.supply_df, self.demand_df, self.flows_df, self.prices_df])
        
        return {
            'supply': not self.supply_df.empty,
            'demand': not self.demand_df.empty,
            'flows': not self.flows_df.empty,
            'prices': not self.prices_df.empty
        }

def create_supply_demand_chart(supply_df, demand_df):
    """Create supply vs demand chart with unique key"""
    if supply_df.empty or demand_df.empty:
        return None
    
    # Merge supply and demand data
    supply_agg = supply_df.groupby('Date')['Supply'].sum().reset_index()
    demand_agg = demand_df.groupby('Date')['Demand'].sum().reset_index()
    
    merged_df = pd.merge(supply_agg, demand_agg, on='Date', how='outer')
    
    fig = px.line(merged_df, x='Date', y=['Supply', 'Demand'],
                  title="WA Gas Supply vs Demand",
                  labels={'value': 'Volume (TJ)', 'variable': 'Type'})
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Volume (TJ)",
        hovermode='x unified'
    )
    
    return fig

def create_price_chart(prices_df):
    """Create price trend chart with unique key"""
    if prices_df.empty:
        return None
    
    fig = px.line(prices_df, x='Date', y='Price_GJ',
                  title="WA Gas Price Trends",
                  labels={'Price_GJ': 'Price ($/GJ)'})
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price ($/GJ)",
        showlegend=False
    )
    
    return fig

def create_flows_chart(flows_df):
    """Create gas flows chart with unique key"""
    if flows_df.empty:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=flows_df['Date'], y=flows_df['Pipeline_Flow'],
                            mode='lines+markers', name='Pipeline Flow'))
    fig.add_trace(go.Scatter(x=flows_df['Date'], y=flows_df['Import_Volume'],
                            mode='lines+markers', name='Imports'))
    fig.add_trace(go.Scatter(x=flows_df['Date'], y=flows_df['Export_Volume'],
                            mode='lines+markers', name='Exports'))
    
    fig.update_layout(
        title="WA Gas Flows Analysis",
        xaxis_title="Date",
        yaxis_title="Volume (TJ)",
        hovermode='x unified'
    )
    
    return fig

def display_key_metrics(data_loader):
    """Display key performance indicators"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if not data_loader.supply_df.empty:
            avg_supply = data_loader.supply_df['Supply'].mean()
            st.metric("Avg Daily Supply", f"{avg_supply:.1f} TJ")
        else:
            st.metric("Avg Daily Supply", "No Data")
    
    with col2:
        if not data_loader.demand_df.empty:
            avg_demand = data_loader.demand_df['Demand'].mean()
            st.metric("Avg Daily Demand", f"{avg_demand:.1f} TJ")
        else:
            st.metric("Avg Daily Demand", "No Data")
    
    with col3:
        if not data_loader.prices_df.empty:
            avg_price = data_loader.prices_df['Price_GJ'].mean()
            st.metric("Avg Price", f"${avg_price:.2f}/GJ")
        else:
            st.metric("Avg Price", "No Data")
    
    with col4:
        if not data_loader.flows_df.empty:
            avg_storage = data_loader.flows_df['Storage_Level'].mean()
            st.metric("Avg Storage", f"{avg_storage:.1f}%")
        else:
            st.metric("Avg Storage", "No Data")

def main():
    """Main dashboard application"""
    st.set_page_config(
        page_title="WA Gas Market Dashboard", 
        page_icon="⛽", 
        layout="wide"
    )
    
    # Header
    st.title("⛽ Western Australia Gas Market Dashboard")
    st.markdown("Real-time monitoring of gas supply, demand, and market conditions")
    
    # Initialize data loader
    if 'gas_data_loader' not in st.session_state:
        st.session_state.gas_data_loader = GasDashboardDataLoader()
    
    # Sidebar controls
    st.sidebar.header("🔧 Dashboard Controls")
    
    use_sample = st.sidebar.checkbox(
        "Use Sample Data", 
        value=True, 
        help="Use generated sample data instead of CSV files"
    )
    
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    
    if st.sidebar.button("🔄 Refresh Data") or auto_refresh:
        with st.spinner("Loading gas market data..."):
            status = st.session_state.gas_data_loader.load_data(use_sample_data=use_sample)
            
            # Display loading results
            for data_type, loaded in status.items():
                if loaded:
                    st.sidebar.success(f"✅ {data_type.title()} data loaded")
                else:
                    st.sidebar.error(f"❌ {data_type.title()} data failed")
    
    # Auto-refresh functionality
    if auto_refresh:
        st.rerun()
    
    # Main dashboard content
    if st.session_state.gas_data_loader.data_loaded:
        data_loader = st.session_state.gas_data_loader
        
        # Key Metrics
        st.subheader("📊 Key Performance Indicators")
        display_key_metrics(data_loader)
        
        st.divider()
        
        # Charts Section
        st.subheader("📈 Market Analysis")
        
        # Supply vs Demand Chart (Fixed with unique key)
        supply_demand_fig = create_supply_demand_chart(data_loader.supply_df, data_loader.demand_df)
        if supply_demand_fig:
            st.plotly_chart(supply_demand_fig, use_container_width=True, key="supply_demand_chart")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Price Chart (Fixed with unique key)
            price_fig = create_price_chart(data_loader.prices_df)
            if price_fig:
                st.plotly_chart(price_fig, use_container_width=True, key="price_chart")
        
        with col2:
            # Flows Chart (Fixed with unique key)
            flows_fig = create_flows_chart(data_loader.flows_df)
            if flows_fig:
                st.plotly_chart(flows_fig, use_container_width=True, key="flows_chart")
        
        st.divider()
        
        # Data Tables Section
        st.subheader("📋 Detailed Data")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Supply", "Demand", "Flows", "Prices"])
        
        with tab1:
            if not data_loader.supply_df.empty:
                st.dataframe(data_loader.supply_df.tail(10), use_container_width=True)
            else:
                st.error("No supply data available")
        
        with tab2:
            if not data_loader.demand_df.empty:
                st.dataframe(data_loader.demand_df.tail(10), use_container_width=True)
            else:
                st.error("No demand data available")
        
        with tab3:
            if not data_loader.flows_df.empty:
                st.dataframe(data_loader.flows_df.tail(10), use_container_width=True)
            else:
                st.error("No flows data available")
        
        with tab4:
            if not data_loader.prices_df.empty:
                st.dataframe(data_loader.prices_df.tail(10), use_container_width=True)
            else:
                st.error("No prices data available")
    
    else:
        st.warning("⚠️ No data loaded. Please use the sidebar controls to load data.")
        st.info("💡 Try checking 'Use Sample Data' and clicking 'Refresh Data' to get started.")
        
        # Load sample data by default on first run
        if st.button("🚀 Load Sample Data to Get Started"):
            with st.spinner("Loading sample data..."):
                st.session_state.gas_data_loader.load_data(use_sample_data=True)
                st.rerun()

if __name__ == "__main__":
    main()
