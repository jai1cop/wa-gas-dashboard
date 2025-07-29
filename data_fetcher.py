import pandas as pd
import logging
from typing import Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_dataframe(df: pd.DataFrame, name: str, required_columns: Optional[List[str]] = None) -> bool:
    if df.empty:
        logger.warning(f"{name} DataFrame is empty")
        return False

    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            logger.error(f"{name} missing required columns: {missing_cols}")
            return False

    logger.info(f"{name} DataFrame validation passed - Shape: {df.shape}")
    return True
