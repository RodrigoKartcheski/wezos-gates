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
            mandatory = rule.get("mandatory", True)
            max_percent = rule.get("max_percent", 0)
            
            # Count actual nulls (NaN)
            null_mask = self.df[col].isnull()
            
            # Also count empty strings or whitespace-only strings as null
            if self.df[col].dtype == 'object':
                null_mask |= self.df[col].apply(lambda x: str(x).strip() == "" if pd.notnull(x) else False)
            
            null_count = null_mask.sum()
            null_percent = (null_count / len(self.df)) * 100
            
            # Smart threshold: if max_percent is <= 1.0 and null_percent is > 1.0, 
            # assume user meant fraction (e.g. 0.2 for 20%)
            effective_threshold = max_percent
            if max_percent <= 1.0 and max_percent > 0:
                 # If user expects 0.2 to be 20%, but it's exactly 0.2%, it's ambiguous.
                 # However, given the user request "0.2 (20%)", I'll honor the 0-1 range.
                 effective_threshold = max_percent * 100

            status = "PASS" if null_percent <= effective_threshold else "FAIL"
            if not mandatory and status == "FAIL":
                status = "WARN"
            
            self.results.append({
                "type": "null_check",
                "column": col,
                "status": status,
                "null_count": int(null_count),
                "null_percent": f"{null_percent:.2f}%",
                "threshold": f"{effective_threshold}%",
                "mandatory": mandatory
            })

    def validate_uniqueness(self, primary_key_config: Any):
        """Checks for duplicate rows based on primary key(s)."""
        if not primary_key_config:
            return

        rtype = "primary_key"
        # Support both old format [cols] and new format {"columns": [cols], "mandatory": bool}
        if isinstance(primary_key_config, list):
            primary_keys = primary_key_config
            mandatory = True
        else:
            primary_keys = primary_key_config.get("columns", [])
            mandatory = primary_key_config.get("mandatory", True)
            rtype = primary_key_config.get("type", "primary_key_check")

        duplicates = self.df.duplicated(subset=primary_keys).sum()
        status = "PASS" if duplicates == 0 else "FAIL"
        if not mandatory and status == "FAIL":
            status = "WARN"

        self.results.append({
            "type": rtype,
            "columns": primary_keys,
            "status": status,
            "mandatory": mandatory,
            "duplicate_count": int(duplicates)
        })

    def validate_domain(self, domain_checks: List[Dict[str, Any]]):
        """Checks if values are within allowed_values or match a regex."""
        for rule in domain_checks:
            col = rule["column"]
            allowed = rule.get("allowed_values")
            forbidden = rule.get("forbidden_values")
            regex = rule.get("regex")
            mandatory = rule.get("mandatory", True)

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
            if not mandatory and status == "FAIL":
                status = "WARN"

            self.results.append({
                "type": "domain_check",
                "column": col,
                "status": status,
                "mandatory": mandatory,
                "invalid_count": int(invalid_count)
            })

    def validate_numeric(self, numeric_checks: List[Dict[str, Any]]):
        """Checks min, max, and negative values for numeric columns."""
        for rule in numeric_checks:
            col = rule["column"]
            min_val = rule.get("min")
            max_val = rule.get("max")
            allow_negative = rule.get("allow_negative", True)
            mandatory = rule.get("mandatory", True)

            invalid_rows = pd.Series([False] * len(self.df), index=self.df.index)

            if min_val is not None:
                invalid_rows |= (self.df[col] < min_val)
            if max_val is not None:
                invalid_rows |= (self.df[col] > max_val)
            if not allow_negative:
                invalid_rows |= (self.df[col] < 0)

            invalid_count = invalid_rows.sum()
            status = "PASS" if invalid_count == 0 else "FAIL"
            if not mandatory and status == "FAIL":
                status = "WARN"

            self.results.append({
                "type": "numeric_check",
                "column": col,
                "status": status,
                "mandatory": mandatory,
                "invalid_count": int(invalid_count)
            })

    def validate_volume(self, volume_config: Dict[str, Any]):
        """Checks total row count against min/max thresholds."""
        row_count = len(self.df)
        min_rows = volume_config.get("min_rows")
        max_rows = volume_config.get("max_rows")
        mandatory = volume_config.get("mandatory", True)

        status = "PASS"
        if min_rows is not None and row_count < min_rows:
            status = "FAIL"
        if max_rows is not None and row_count > max_rows:
            status = "FAIL"

        if not mandatory and status == "FAIL":
            status = "WARN"

        self.results.append({
            "type": "volume_check",
            "status": status,
            "mandatory": mandatory,
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

    def validate_outliers(self, outlier_config: Any):
        """Detects numeric outliers using Z-Score > 3."""
        if isinstance(outlier_config, list):
            columns = outlier_config
            mandatory = True
        else:
            columns = outlier_config.get("columns", [])
            mandatory = outlier_config.get("mandatory", True)

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
                status = "FAIL" if mandatory else "WARN"
                self.results.append({
                    "type": "outlier_check",
                    "column": col,
                    "status": status,
                    "mandatory": mandatory,
                    "count": len(outliers),
                    "examples": outliers.unique()[:5].tolist()
                })

    def validate_empty_strings(self, empty_config: Any):
        """Detects strings that are just whitespace or truly empty."""
        if isinstance(empty_config, list):
            columns = empty_config
            mandatory = True
        else:
            columns = empty_config.get("columns", [])
            mandatory = empty_config.get("mandatory", True)

        if "*" in columns:
            columns = self.df.select_dtypes(include=['object']).columns.tolist()

        for col in columns:
            if col not in self.df.columns: continue
            # Count: NaN/None + truly empty strings + whitespace-only strings
            def is_empty_or_null(x):
                if pd.isna(x):
                    return True
                if isinstance(x, str) and not x.strip():
                    return True
                return False
            empty_count = self.df[col].apply(is_empty_or_null).sum()
            if empty_count > 0:
                status = "FAIL" if mandatory else "WARN"
                self.results.append({
                    "type": "empty_string_check",
                    "column": col,
                    "status": status,
                    "mandatory": mandatory,
                    "count": int(empty_count)
                })

    def validate_duplicate_rows(self, enabled: bool):
        """Checks for duplicate rows in the entire dataset."""
        if not enabled:
            return
        
        duplicate_count = self.df.duplicated().sum()
        status = "PASS" if duplicate_count == 0 else "FAIL"
        
        self.results.append({
            "type": "duplicate_row_check",
            "status": status,
            "duplicate_count": int(duplicate_count)
        })

    def validate_schema_types(self, schema_config: Dict[str, str]):
        """Checks if column types match the expected schema."""
        for col, expected_type in schema_config.items():
            if col not in self.df.columns:
                continue
            
            actual_dtype = str(self.df[col].dtype)
            is_valid = False
            
            if expected_type == "int":
                is_valid = "int" in actual_dtype or "float" in actual_dtype
            elif expected_type == "string":
                is_valid = actual_dtype in ["object", "string", "category"]
            elif expected_type == "date":
                is_valid = "datetime" in actual_dtype or actual_dtype == "object"
            
            status = "PASS" if is_valid else "FAIL"
            
            self.results.append({
                "type": "schema_type_check",
                "column": col,
                "status": status,
                "expected": expected_type,
                "actual": actual_dtype
            })
        
    def validate_date_formats(self, date_config: List[Dict[str, Any]]):
        """Checks if date strings match the specified format."""
        for rule in date_config:
            col = rule["column"]
            fmt = rule.get("format", "%Y-%m-%d")
            mandatory = rule.get("mandatory", True)
            
            if col not in self.df.columns:
                continue
                
            # Treat everything as string for parsing test
            series = self.df[col].astype(str)
            
            # Helper to check format
            def is_valid_date(val):
                if pd.isna(val) or val == "nan" or not val.strip():
                    return True # Handled by null_check
                try:
                    pd.to_datetime(val, format=fmt)
                    return True
                except:
                    return False
            
            valid_mask = series.map(is_valid_date)
            invalid_count = (~valid_mask).sum()
            
            status = "PASS" if invalid_count == 0 else "FAIL"
            if not mandatory and status == "FAIL":
                status = "WARN"
                
            self.results.append({
                "type": "date_check",
                "column": col,
                "status": status,
                "mandatory": mandatory,
                "invalid_count": int(invalid_count),
                "format": fmt
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
            # Support legacy primary_key format
            pk_config = validations_config["primary_key"]
            if isinstance(pk_config, list):
                self.validate_uniqueness({"columns": pk_config, "type": "primary_key_check", "mandatory": True})
            else:
                pk_config["type"] = "primary_key_check"
                self.validate_uniqueness(pk_config)
                
        if "uniqueness_checks" in validations_config:
            for check in validations_config["uniqueness_checks"]:
                check["type"] = "uniqueness_check"
                self.validate_uniqueness(check)
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
        if "duplicate_check" in validations_config:
            self.validate_duplicate_rows(validations_config["duplicate_check"])
        if "schema" in validations_config:
            self.validate_schema_types(validations_config["schema"])
        if "date_checks" in validations_config:
            self.validate_date_formats(validations_config["date_checks"])
        
        return self.results
