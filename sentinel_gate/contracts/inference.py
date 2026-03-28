import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sentinel_gate.utils.logger import logger

class SchemaInference:
    """Logic for inferring data types from a DataFrame, especially for RAW layers."""

    @staticmethod
    def infer_column_type(series: pd.Series) -> str:
        """Infers the type of a single column."""
        # Remove nulls for type detection
        clean_series = series.dropna()
        if clean_series.empty:
            return "string"

        # 1. Detect Boolean
        if clean_series.dtype == 'bool':
            return "boolean"
        
        # Try converting strings to boolean if it looks like boolean
        if clean_series.dtype == 'object':
            unique_vals = clean_series.unique()
            if set(unique_vals).issubset({'True', 'False', 'true', 'false', 'T', 'F', '1', '0'}):
                return "boolean"

        # 2. Detect Integer
        try:
            if np.array_equal(clean_series, clean_series.astype(int)):
                return "integer"
        except (ValueError, TypeError, OverflowError):
            pass

        # 3. Detect Float
        try:
            pd.to_numeric(clean_series, errors='raise')
            return "float"
        except (ValueError, TypeError):
            pass

        # 4. Detect Datetime
        try:
            pd.to_datetime(clean_series, errors='raise')
            return "datetime"
        except (ValueError, TypeError):
            pass

        # 5. Detect Categorical (heuristic: low cardinality)
        if clean_series.dtype == 'object' or clean_series.dtype == 'category':
            # Less than 10% unique values or less than 20 unique values for small datasets
            if len(clean_series.unique()) < 20 or len(clean_series.unique()) / len(clean_series) < 0.1:
                return "categorical"

        # 6. Fallback String
        return "string"

    @classmethod
    def infer_schema(cls, df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
        """Infers types for all columns in a DataFrame."""
        logger.info("Inferring schema types")
        inferred_schema = {}
        for col in df.columns:
            source_type = str(df[col].dtype)
            inferred_type = cls.infer_column_type(df[col])
            inferred_schema[col] = {
                "source_type": source_type,
                "inferred_type": inferred_type
            }
        return inferred_schema
