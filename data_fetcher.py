import pandas as pd
import os
import logging
from typing import Optional, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_csv(file_path: str, **kwargs) -> pd.DataFrame:
    """
    Fetch CSV data from given path and return DataFrame.

    Args:
        file_path (str): Path to the CSV file.
        **kwargs: Additional kwargs for pd.read_csv.

    Returns:
        pd.DataFrame: Loaded DataFrame, or empty DataFrame if errors occur.
    """
    if not os.path.exists(file_path):
        logger.error(f"❌ File not found: {file_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path, **kwargs)
        logger.info(f"✅ Successfully loaded {file_path} - Shape: {df.shape}")
        return df
    except pd.errors.EmptyDataError:
        logger.error(f"❌ Empty CSV file: {file_path}")
    except pd.errors.ParserError as e:
        logger.error(f"❌ Parse error in {file_path}: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error loading {file_path}: {e}")

    return pd.DataFrame()

def validate_dataframe(df: pd.DataFrame, name: str, required_columns: Optional[List[str]] = None) -> bool:
    """
    Validate the DataFrame is not empty and optionally has required columns.

    Args:
        df (pd.DataFrame): DataFrame to validate.
        name (str): Name identifier for logging.
        required_columns (List[str], optional): List of column names that must be present.

    Returns:
        bool: True if valid, False otherwise.
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
