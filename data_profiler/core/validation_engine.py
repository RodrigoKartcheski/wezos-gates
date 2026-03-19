import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List, Optional
from data_profiler.utils.logger import logger
from data_profiler.utils.sql_utils import apply_sql_filter

class ValidationEngine:
    """Engine for running data quality validations on a DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.original_row_count = len(df)
        self.results = []

    def apply_filter(self, filter_query: str):
        """Applies a SQL-like filter to the internal dataframe."""
        self.df = apply_sql_filter(self.df, filter_query)
        return self.df

    def validate_nulls(self, config: List[Dict[str, Any]]):
        """Checks for null values based on max_percent threshold."""
        for rule in config:
            col = rule["column"]
            max_percent = rule.get("max_percent", 0)
            null_count = self.df[col].isnull().sum()
            null_percent = (null_count / len(self.df)) * 100
            
            status = "PASS" if null_percent <= max_percent else "FAIL"
            self.results.append({
                "type": "null_check",
                "column": col,
                "status": status,
                "null_count": int(null_count),
                "null_percent": f"{null_percent:.2f}%",
                "threshold": f"{max_percent}%"
            })

    def validate_uniqueness(self, primary_keys: List[str]):
        """Checks if the specified primary keys (or composite) are unique."""
        if not primary_keys:
            return

        duplicates = self.df.duplicated(subset=primary_keys).sum()
        status = "PASS" if duplicates == 0 else "FAIL"
        self.results.append({
            "type": "uniqueness_check",
            "columns": primary_keys,
            "status": status,
            "duplicate_count": int(duplicates)
        })

    def validate_domain(self, domain_checks: List[Dict[str, Any]]):
        """Checks if values are within allowed_values or match a regex."""
        for rule in domain_checks:
            col = rule["column"]
            allowed = rule.get("allowed_values")
            forbidden = rule.get("forbidden_values")
            regex = rule.get("regex")

            invalid_rows = pd.Series([False] * len(self.df), index=self.df.index)

            if allowed:
                invalid_rows |= ~self.df[col].isin(allowed)
            if forbidden:
                invalid_rows |= self.df[col].isin(forbidden)
            if regex:
                # convert to string for regex check if needed
                invalid_rows |= ~self.df[col].astype(str).str.match(regex, na=False)

            invalid_count = invalid_rows.sum()
            status = "PASS" if invalid_count == 0 else "FAIL"
            self.results.append({
                "type": "domain_check",
                "column": col,
                "status": status,
                "invalid_count": int(invalid_count)
            })

    def validate_numeric(self, numeric_checks: List[Dict[str, Any]]):
        """Checks min, max, and negative values for numeric columns."""
        for rule in numeric_checks:
            col = rule["column"]
            min_val = rule.get("min")
            max_val = rule.get("max")
            allow_negative = rule.get("allow_negative", True)

            invalid_rows = pd.Series([False] * len(self.df), index=self.df.index)

            if min_val is not None:
                invalid_rows |= (self.df[col] < min_val)
            if max_val is not None:
                invalid_rows |= (self.df[col] > max_val)
            if not allow_negative:
                invalid_rows |= (self.df[col] < 0)

            invalid_count = invalid_rows.sum()
            status = "PASS" if invalid_count == 0 else "FAIL"
            self.results.append({
                "type": "numeric_check",
                "column": col,
                "status": status,
                "invalid_count": int(invalid_count)
            })

    def validate_volume(self, volume_config: Dict[str, Any]):
        """Checks total row count against min/max thresholds."""
        row_count = len(self.df)
        min_rows = volume_config.get("min_rows")
        max_rows = volume_config.get("max_rows")

        status = "PASS"
        if min_rows is not None and row_count < min_rows:
            status = "FAIL"
        if max_rows is not None and row_count > max_rows:
            status = "FAIL"

        self.results.append({
            "type": "volume_check",
            "status": status,
            "row_count": row_count,
            "min_rows": min_rows,
            "max_rows": max_rows
        })

    def validate_constants(self, columns: List[str]):
        """Identifies columns that have only one unique value."""
        if "*" in columns:
            columns = self.df.columns.tolist()

        for col in columns:
            if col not in self.df.columns: continue
            nunique = self.df[col].nunique(dropna=False)
            if nunique == 1:
                val = self.df[col].iloc[0]
                self.results.append({
                    "type": "constant_check",
                    "column": col,
                    "status": "WARN",
                    "value": str(val)
                })

    def validate_outliers(self, columns: List[str]):
        """Detects numeric outliers using Z-Score > 3."""
        if "*" in columns:
            columns = self.df.select_dtypes(include=['number']).columns.tolist()

        for col in columns:
            if col not in self.df.columns or not pd.api.types.is_numeric_dtype(self.df[col]):
                continue
            
            mean = self.df[col].mean()
            std = self.df[col].std()
            if std == 0: continue

            outliers = self.df[np.abs((self.df[col] - mean) / std) > 3][col]
            if not outliers.empty:
                self.results.append({
                    "type": "outlier_check",
                    "column": col,
                    "status": "FAIL",
                    "count": len(outliers),
                    "examples": outliers.unique()[:5].tolist()
                })

    def validate_empty_strings(self, columns: List[str]):
        """Detects strings that are just whitespace or truly empty."""
        if "*" in columns:
            columns = self.df.select_dtypes(include=['object']).columns.tolist()

        for col in columns:
            if col not in self.df.columns: continue
            empty_count = self.df[col].apply(lambda x: isinstance(x, str) and not str(x).strip()).sum()
            if empty_count > 0:
                self.results.append({
                    "type": "empty_string_check",
                    "column": col,
                    "status": "FAIL",
                    "count": int(empty_count)
                })

    def run_all(self, validations_config: Dict[str, Any]):
        """Runs all validations specified in the config."""
        logger.info("Running all validations")
        
        # 0. Apply Filter (New)
        filter_query = validations_config.get("filter")
        if filter_query:
            self.apply_filter(filter_query)

        if "null_checks" in validations_config:
            self.validate_nulls(validations_config["null_checks"])
        if "primary_key" in validations_config:
            self.validate_uniqueness(validations_config["primary_key"])
        if "domain_checks" in validations_config:
            self.validate_domain(validations_config["domain_checks"])
        if "numeric_checks" in validations_config:
            self.validate_numeric(validations_config["numeric_checks"])
        if "volume_checks" in validations_config:
            self.validate_volume(validations_config["volume_checks"])
        
        # New checks from user request
        if "constant_checks" in validations_config:
            self.validate_constants(validations_config["constant_checks"])
        if "outlier_checks" in validations_config:
            self.validate_outliers(validations_config["outlier_checks"])
        if "empty_string_checks" in validations_config:
            self.validate_empty_strings(validations_config["empty_string_checks"])
        
        return self.results
