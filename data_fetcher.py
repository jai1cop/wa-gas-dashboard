import pandas as pd
import os
from typing import Optional, Dict, Any
import logging

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
        data_type (str): Type of sample data ('supply', 'demand', 'model')
    
    Returns:
        pd.DataFrame: Sample data
    """
    if data_type == 'supply':
        return pd.DataFrame({
            'product_id': ['P001', 'P002', 'P003'],
            'supply_quantity': [100, 200, 150],
            'location': ['Warehouse A', 'Warehouse B', 'Warehouse C'],
            'date': pd.date_range('2024-01-01', periods=3)
        })
    
    elif data_type == 'demand':
        return pd.DataFrame({
            'product_id': ['P001', 'P002', 'P003'],
            'demand_quantity': [80, 180, 120],
            'region': ['North', 'South', 'East'],
            'date': pd.date_range('2024-01-01', periods=3)
        })
    
    elif data_type == 'model':
        return pd.DataFrame({
            'model_id': ['M001', 'M002', 'M003'],
            'accuracy': [0.85, 0.92, 0.78],
            'model_type': ['Linear', 'Random Forest', 'Neural Network']
        })
    
    else:
        return pd.DataFrame()
