import pandas as pd
import os
from typing import Optional, Dict, Any
import logging
import numpy as np
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_csv(file_path: str, **kwargs) -> pd.DataFrame:
    """
    Fetch CSV data and return DataFrame with error handling
    
    Args:
        file_path (str): Path to the CSV file
        **kwargs: Additional arguments for pd.read_csv()
    
    Returns:
        pd.DataFrame: Loaded data or empty DataFrame if failed
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(file_path, **kwargs)
        logger.info(f"✅ Successfully loaded {file_path} - Shape: {df.shape}")
        return df
    
    except pd.errors.EmptyDataError:
        logger.error(f"❌ Empty CSV file: {file_path}")
        return pd.DataFrame()
    
    except pd.errors.ParserError as e:
        logger.error(f"❌ Parse error in {file_path}: {e}")
        return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"❌ Unexpected error loading {file_path}: {e}")
        return pd.DataFrame()

def validate_dataframe(df: pd.DataFrame, name: str, required_columns: list = None) -> bool:
    """
    Validate DataFrame structure and content
    
    Args:
        df (pd.DataFrame): DataFrame to validate
        name (str): Name for logging purposes
        required_columns (list): List of required column names
    
    Returns:
        bool: True if valid, False otherwise
    """
    if df.empty:
        logger.warning(f"⚠️ {name} DataFrame is empty")
        return False
    
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            logger.error(f"❌ {name} missing required columns: {missing_cols}")
            return False
    
    logger.info(f"✅ {name} DataFrame validation passed - Shape: {df.shape}")
    return True

def get_sample_data(data_type: str) -> pd.DataFrame:
    """
    Generate sample data if real data is unavailable
    
    Args:
        data_type (str): Type of sample data ('supply', 'demand', 'flows', 'prices')
    
    Returns:
        pd.DataFrame: Sample data
    """
    # Generate date range for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    if data_type == 'supply':
        data = []
        for date in dates:
            data.append({
                'Date': date,
                'Supply': np.random.uniform(900, 1100),
                'Source': np.random.choice(['Gas Field A', 'Gas Field B', 'LNG Import']),
                'Region': 'Western Australia'
            })
        return pd.DataFrame(data)
    
    elif data_type == 'demand':
        data = []
        for date in dates:
            data.append({
                'Date': date,
                'Demand': np.random.uniform(800, 1000),
                'Sector': np.random.choice(['Industrial', 'Commercial', 'Residential']),
                'Region': 'Western Australia'
            })
        return pd.DataFrame(data)
    
    elif data_type == 'flows':
        data = []
        for date in dates:
            data.append({
                'Date': date,
                'Pipeline_Flow': np.random.uniform(800, 1200),
                'Storage_Level': np.random.uniform(60, 90),
                'Import_Volume': np.random.uniform(0, 100),
                'Export_Volume': np.random.uniform(50, 200)
            })
        return pd.DataFrame(data)
    
    elif data_type == 'prices':
        data = []
        for date in dates:
            data.append({
                'Date': date,
                'Price_GJ': np.random.uniform(10, 15),
                'Market': 'WA Gas Market',
                'Currency': 'AUD'
            })
        return pd.DataFrame(data)
    
    else:
        return pd.DataFrame()
