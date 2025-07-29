import pandas as pd
import streamlit as st
import logging
from typing import Tuple, Dict
import os

# Import your data fetcher with fallback
try:
    from data_fetcher import fetch_csv, validate_dataframe, get_sample_data
    DATA_FETCHER_AVAILABLE = True
except ImportError:
    DATA_FETCHER_AVAILABLE = False
    logging.warning("⚠️ data_fetcher module not available, using fallback methods")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardDataLoader:
    """Handle all data loading operations for the dashboard"""
    
    def __init__(self):
        self.supply_df = pd.DataFrame()
        self.demand_df = pd.DataFrame()
        self.model_df = pd.DataFrame()
        self.data_loaded = False
    
    def load_csv_fallback(self, file_path: str) -> pd.DataFrame:
        """Fallback CSV loading method when data_fetcher is unavailable"""
        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                logger.info(f"✅ Fallback load successful: {file_path} - Shape: {df.shape}")
                return df
            else:
                logger.error(f"❌ File not found: {file_path}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ Fallback load failed for {file_path}: {e}")
            return pd.DataFrame()
    
    def load_data(self, use_sample_data: bool = False) -> Dict[str, bool]:
        """
        Load all required datasets
        
        Args:
            use_sample_data (bool): Use sample data instead of real files
        
        Returns:
            Dict[str, bool]: Status of each data loading operation
        """
        status = {'supply': False, 'demand': False, 'model': False}
        
        if use_sample_data:
            logger.info("📊 Loading sample data...")
            self.supply_df = get_sample_data('supply')
            self.demand_df = get_sample_data('demand') 
            self.model_df = get_sample_data('model')
            status = {'supply': True, 'demand': True, 'model': True}
        else:
            # Data file paths - adjust these to your actual file locations
            data_files = {
                'supply': 'data/supply_data.csv',
                'demand': 'data/demand_data.csv', 
                'model': 'data/model_data.csv'
            }
            
            for data_type, file_path in data_files.items():
                if DATA_FETCHER_AVAILABLE:
                    df = fetch_csv(file_path)
                else:
                    df = self.load_csv_fallback(file_path)
                
                if not df.empty:
                    if data_type == 'supply':
                        self.supply_df = df
                        status['supply'] = True
                    elif data_type == 'demand':
                        self.demand_df = df
                        status['demand'] = True
                    elif data_type == 'model':
                        self.model_df = df
                        status['model'] = True
        
        self.data_loaded = all(status.values())
        return status
    
    def get_debug_info(self) -> str:
        """Generate debug information string"""
        debug_info = f"""
Debug Information:
Supply DataFrame shape: {self.supply_df.shape}
Model DataFrame shape: {self.model_df.shape}
{'✅' if not self.supply_df.empty else '❌'} Supply DataFrame {'loaded' if not self.supply_df.empty else 'is EMPTY'}

📈 Demand Analysis Debug:
Demand DataFrame shape: {self.demand_df.shape}
{'✅' if not self.demand_df.empty else '❌'} Demand DataFrame {'loaded' if not self.demand_df.empty else 'is EMPTY'}

🎯 Status Summary:
Dashboard loaded: {'✅' if self.data_loaded else '❌'}
Supply data: {'✅' if not self.supply_df.empty else '❌'}
Demand data: {'✅' if not self.demand_df.empty else '❌'}
Model data: {'✅' if not self.model_df.empty else '❌'}
        """
        return debug_info.strip()

def main():
    """Main dashboard application"""
    st.set_page_config(page_title="Supply & Demand Dashboard", layout="wide")
    
    st.title("📊 Supply & Demand Analytics Dashboard")
    
    # Initialize data loader
    if 'data_loader' not in st.session_state:
        st.session_state.data_loader = DashboardDataLoader()
    
    # Sidebar controls
    st.sidebar.header("🔧 Data Loading Controls")
    
    use_sample = st.sidebar.checkbox("Use Sample Data", value=False, 
                                    help="Check this to use sample data instead of CSV files")
    
    if st.sidebar.button("🔄 Load Data"):
        with st.spinner("Loading data..."):
            status = st.session_state.data_loader.load_data(use_sample_data=use_sample)
            
            # Display loading results
            for data_type, loaded in status.items():
                if loaded:
                    st.sidebar.success(f"✅ {data_type.title()} data loaded")
                else:
                    st.sidebar.error(f"❌ {data_type.title()} data failed")
    
    # Debug section
    st.sidebar.header("🐛 Debug Information")
    if st.sidebar.button("Show Debug Info"):
        st.code(st.session_state.data_loader.get_debug_info())
    
    # Main dashboard content
    if st.session_state.data_loader.data_loaded:
        display_dashboard(st.session_state.data_loader)
    else:
        st.warning("⚠️ No data loaded. Please use the sidebar controls to load data.")
        st.info("💡 Try checking 'Use Sample Data' and clicking 'Load Data' to get started.")

def display_dashboard(data_loader: DashboardDataLoader):
    """Display the main dashboard content"""
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "📦 Supply Analysis", "📊 Demand Analysis"])
    
    with tab1:
        st.subheader("📊 Data Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Supply Records", len(data_loader.supply_df))
            st.dataframe(data_loader.supply_df.head())
        
        with col2:
            st.metric("Demand Records", len(data_loader.demand_df))
            st.dataframe(data_loader.demand_df.head())
        
        with col3:
            st.metric("Model Records", len(data_loader.model_df))
            st.dataframe(data_loader.model_df.head())
    
    with tab2:
        st.subheader("📦 Supply Analysis")
        if not data_loader.supply_df.empty:
            st.dataframe(data_loader.supply_df)
            
            # Add basic analytics if columns exist
            if 'supply_quantity' in data_loader.supply_df.columns:
                st.bar_chart(data_loader.supply_df.set_index('product_id')['supply_quantity'])
        else:
            st.error("No supply data available")
    
    with tab3:
        st.subheader("📊 Demand Analysis")
        if not data_loader.demand_df.empty:
            st.dataframe(data_loader.demand_df)
            
            # Add basic analytics if columns exist
            if 'demand_quantity' in data_loader.demand_df.columns:
                st.bar_chart(data_loader.demand_df.set_index('product_id')['demand_quantity'])
        else:
            st.error("No demand data available")

if __name__ == "__main__":
    main()
