"""
SentinelGate Validation Engine (v3.0)

Production-grade validation engine with:
- ResultCollector for decoupled result management
- AST-validated expression evaluation
- State immutability (original DataFrame never mutated)
- Rule registry for extensible execution
- Execution context for Airflow/observability correlation
- Regex caching for high-throughput performance
"""
import pandas as pd
import numpy as np
import re
import ast
import copy
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Callable
from sentinel_gate.utils.logger import logger
from sentinel_gate.utils.sql_utils import apply_sql_filter
from sentinel_gate.engines.pandas_engine import PandasExecutionEngine


# ---------------------------------------------------------------------------
# 1. Strong Typing — ValidationResult dataclass
# ---------------------------------------------------------------------------
@dataclass
class ValidationResult:
    """Standardized output contract for every validation check."""
    rule_id: str
    type: str
    status: str
    severity: str
    mandatory: bool
    execution_id: str
    column: Optional[str] = None
    columns: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Returns a clean dict, omitting None fields."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------------------
# 2. Result Layer Decoupling — ResultCollector
# ---------------------------------------------------------------------------
class ResultCollector:
    """Centralized, decoupled result handler. Engine never touches raw lists."""

    _SEVERITY_WEIGHTS = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.1}

    def __init__(self):
        self._results: List[ValidationResult] = []

    def add(self, result: ValidationResult):
        self._results.append(result)

    @property
    def results(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._results]

    def summary(self) -> Dict[str, Any]:
        total = len(self._results)
        counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
        total_weight = 0.0
        pass_weight = 0.0

        for r in self._results:
            counts[r.status] = counts.get(r.status, 0) + 1
            w = self._SEVERITY_WEIGHTS.get(r.severity, 0.5)
            total_weight += w
            if r.status == "PASS":
                pass_weight += w

        return {
            "total_checks": total,
            "pass": counts["PASS"],
            "fail": counts["FAIL"],
            "warn": counts["WARN"],
            "skip": counts["SKIP"],
            "score": round((pass_weight / total_weight) * 100, 2) if total_weight > 0 else 0.0
        }


# ---------------------------------------------------------------------------
# 3. AST Whitelist — Secure Expression Evaluation
# ---------------------------------------------------------------------------
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare,
    ast.BoolOp, ast.Name, ast.Load, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.And, ast.Or, ast.Not,
)


def _validate_expression(equation: str):
    """Parse and walk the AST tree, blocking any node that is not in the whitelist."""
    try:
        tree = ast.parse(equation, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}") from e

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(
                f"Forbidden expression node: {type(node).__name__}. "
                f"Only arithmetic/comparison operators are allowed."
            )


# ---------------------------------------------------------------------------
# 4. Validation Engine (Orchestrates Rules against Execution Engine)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 5. Validation Engine
# ---------------------------------------------------------------------------
class ValidationEngine:
    """Enterprise-grade engine for running data quality validations."""

    def __init__(self, df: pd.DataFrame):
        # State Immutability: original df is stored read-only; all ops use engine
        self._original_df = df
        self._working_df = df.copy()
        self.original_row_count = len(df)

        # Execution engine (Pandas-first, prepared for future multi-engine)
        self.engine = PandasExecutionEngine(self._working_df)

        # Execution context for Airflow/observability correlation
        self._execution_id = str(uuid.uuid4())[:8]

        # Decoupled result layer
        self._collector = ResultCollector()

        # Caches
        self._ref_cache: Dict[str, pd.DataFrame] = {}
        self._regex_cache: Dict[str, re.Pattern] = {}

    @property
    def results(self) -> List[Dict[str, Any]]:
        """Backward-compatible results access (delegates to collector)."""
        return self._collector.results

    # ------------------------------------------------------------------
    def _resolve_status(self, passed: bool, mandatory: bool) -> Tuple[str, str]:
        """Returns (status, severity) tuple."""
        if passed:
            return "PASS", "LOW"
        if not mandatory:
            return "WARN", "MEDIUM"
        return "FAIL", "HIGH"

    def _build_result(
        self,
        *,
        check_type: str,
        passed: bool,
        mandatory: bool = True,
        rule_id: Optional[str] = None,
        column: Optional[str] = None,
        columns: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> ValidationResult:
        """Central result builder. ALL checks MUST use this."""
        status, severity = self._resolve_status(passed, mandatory)
        result = ValidationResult(
            rule_id=rule_id or f"{column or 'global'}_{check_type}",
            type=check_type,
            status=status,
            severity=severity,
            mandatory=mandatory,
            execution_id=self._execution_id,
            column=column,
            columns=columns,
            metrics=metrics,
            message=message,
        )
        self._collector.add(result)
        return result

    def _get_compiled_regex(self, pattern: str) -> re.Pattern:
        """Cached regex compilation — compile once, use many."""
        if pattern not in self._regex_cache:
            self._regex_cache[pattern] = re.compile(pattern)
        return self._regex_cache[pattern]

    @staticmethod
    def _get_contract_key(contract: Dict[str, Any], *keys):
        """Backward-compatible contract key lookup."""
        for k in keys:
            if k in contract:
                return contract[k]
        return None

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------
    def _has_column(self, col: str) -> bool:
        """Delegates column existence check to the execution engine."""
        return self.engine.has_column(col)

    def apply_filter(self, filter_query: str):
        """Applies a SQL-like filter to the WORKING dataframe (never mutates original)."""
        self._working_df = apply_sql_filter(self._working_df, filter_query)
        self.engine.set_dataframe(self._working_df)
        return self._working_df

    # ------------------------------------------------------------------
    # Validation Methods
    # ------------------------------------------------------------------
    def validate_nulls(self, config: List[Dict[str, Any]]):
        """Checks for null values based on max_percent threshold."""
        df = self._working_df
        for rule in config:
            col = rule["column"]
            mandatory = rule.get("mandatory", True)
            max_percent = rule.get("max_percent", 0)

            if not self._has_column(col):
                logger.error(f"[{self._execution_id}] Column '{col}' not found for null_check")
                self._build_result(
                    check_type="null_check", passed=False, mandatory=mandatory,
                    rule_id=rule.get("id"), column=col,
                    message="Column not found"
                )
                continue

            null_mask = df[col].isnull()
            if pd.api.types.is_string_dtype(df[col]):
                null_mask = null_mask | (df[col].astype(str).str.strip() == "")

            null_count = int(null_mask.sum())
            row_count = self.engine.get_row_count()
            null_percent = (null_count / row_count) * 100 if row_count > 0 else 0

            effective_threshold = max_percent
            if 0 < max_percent <= 1.0:
                logger.debug(f"[{self._execution_id}] Treating max_percent {max_percent} as {max_percent*100}% for column {col}")
                effective_threshold = max_percent * 100

            self._build_result(
                check_type="null_check",
                passed=null_percent <= effective_threshold,
                mandatory=mandatory,
                rule_id=rule.get("id", f"{col}_null_check"),
                column=col,
                metrics={
                    "null_count": null_count,
                    "null_percent": f"{null_percent:.2f}%",
                    "threshold": f"{effective_threshold}%",
                },
            )

    def validate_uniqueness(self, primary_key_config: Any):
        """Checks for duplicate rows based on primary key(s)."""
        if not primary_key_config:
            return

        df = self._working_df
        rtype = "primary_key_check"
        if isinstance(primary_key_config, list):
            primary_keys = primary_key_config
            mandatory = True
        else:
            primary_keys = primary_key_config.get("columns", [])
            mandatory = primary_key_config.get("mandatory", True)
            rtype = primary_key_config.get("type", "primary_key_check")

        missing_cols = [c for c in primary_keys if not self._has_column(c)]
        if missing_cols:
            logger.error(f"[{self._execution_id}] Columns {missing_cols} not found for uniqueness check")
            self._build_result(
                check_type=rtype, passed=False, mandatory=mandatory,
                columns=primary_keys,
                message=f"Columns not found: {missing_cols}"
            )
            return

        duplicate_count = int(df.duplicated(subset=primary_keys).sum())
        row_count = self.engine.get_row_count()
        dup_pct = f"{(duplicate_count / row_count * 100):.2f}%" if row_count > 0 else "0.00%"

        self._build_result(
            check_type=rtype,
            passed=duplicate_count == 0,
            mandatory=mandatory,
            columns=primary_keys,
            metrics={"duplicate_count": duplicate_count, "duplicate_percent": dup_pct},
        )

    def validate_domain(self, domain_checks: List[Dict[str, Any]]):
        """Checks if values are within allowed_values or match a regex."""
        df = self._working_df
        for rule in domain_checks:
            col = rule["column"]
            allowed = rule.get("allowed_values")
            forbidden = rule.get("forbidden_values")
            regex = rule.get("regex")
            mandatory = rule.get("mandatory", True)

            if not self._has_column(col):
                logger.error(f"[{self._execution_id}] Column '{col}' not found for domain_check")
                self._build_result(
                    check_type="domain_check", passed=False, mandatory=mandatory,
                    rule_id=rule.get("id"), column=col,
                    message="Column not found"
                )
                continue

            if allowed is not None and forbidden is not None:
                logger.warning(f"[{self._execution_id}] Both allowed and forbidden values for '{col}'")

            invalid_rows = pd.Series(False, index=df.index)

            # Exclude NaN from domain checks (handled by null_check)
            if allowed is not None:
                invalid_rows = invalid_rows | ((~df[col].isin(allowed)) & df[col].notna())
            # Fixed: forbidden is not None (empty list [] is valid)
            if forbidden is not None:
                invalid_rows = invalid_rows | df[col].isin(forbidden)
            if regex:
                compiled = self._get_compiled_regex(regex)
                invalid_rows = invalid_rows | (~df[col].astype(str).str.match(compiled, na=False))

            invalid_count = int(invalid_rows.sum())
            self._build_result(
                check_type="domain_check",
                passed=invalid_count == 0,
                mandatory=mandatory,
                rule_id=rule.get("id", f"{col}_domain_check"),
                column=col,
                metrics={
                    "invalid_count": invalid_count,
                    "regex_used": regex,
                    "forbidden_values": list(forbidden) if forbidden else None,
                },
            )

    def validate_numeric(self, numeric_checks: List[Dict[str, Any]]):
        """Checks min, max, and negative values for numeric columns."""
        df = self._working_df
        for rule in numeric_checks:
            col = rule["column"]
            min_val = rule.get("min")
            max_val = rule.get("max")
            allow_negative = rule.get("allow_negative", True)
            mandatory = rule.get("mandatory", True)

            if not self._has_column(col):
                logger.error(f"[{self._execution_id}] Column '{col}' not found for numeric_check")
                self._build_result(
                    check_type="numeric_check", passed=False, mandatory=mandatory,
                    rule_id=rule.get("id"), column=col,
                    message="Column not found"
                )
                continue

            series = pd.to_numeric(df[col], errors='coerce')
            conversion_fails = int((series.isna() & df[col].notna()).sum())

            invalid_rows = pd.Series(False, index=df.index)
            if min_val is not None:
                invalid_rows = invalid_rows | (series < min_val)
            if max_val is not None:
                invalid_rows = invalid_rows | (series > max_val)
            if not allow_negative:
                invalid_rows = invalid_rows | (series < 0)

            invalid_count = int(invalid_rows.sum()) + conversion_fails
            self._build_result(
                check_type="numeric_check",
                passed=invalid_count == 0,
                mandatory=mandatory,
                rule_id=rule.get("id", f"{col}_numeric_check"),
                column=col,
                metrics={"invalid_count": invalid_count},
            )

    def validate_volume(self, volume_config: Dict[str, Any]):
        """Checks total row count against min/max thresholds."""
        df = self._working_df
        row_count = self.engine.get_row_count()
        min_rows = volume_config.get("min_rows")
        max_rows = volume_config.get("max_rows")
        mandatory = volume_config.get("mandatory", True)

        passed = True
        if min_rows is not None and row_count < min_rows:
            passed = False
        if max_rows is not None and row_count > max_rows:
            passed = False

        self._build_result(
            check_type="volume_check",
            passed=passed,
            mandatory=mandatory,
            metrics={"row_count": row_count, "min_rows": min_rows, "max_rows": max_rows},
        )

    def validate_constants(self, columns: List[str]):
        """Identifies columns that have only one unique value."""
        df = self._working_df
        if "*" in columns:
            columns = self.engine.get_columns()

        for col in columns:
            if not self._has_column(col):
                continue
            nunique = df[col].nunique(dropna=False)
            if nunique == 1:
                val = df[col].iloc[0]
                self._build_result(
                    check_type="constant_check",
                    passed=False,  # Constants are always a warning
                    mandatory=False,
                    column=col,
                    metrics={"value": str(val)},
                )

    def validate_outliers(self, outlier_config: Any):
        """Detects numeric outliers using Z-Score > 3 or IQR method."""
        df = self._working_df
        if isinstance(outlier_config, list):
            columns = outlier_config
            mandatory = True
            method = "z-score"
        else:
            columns = outlier_config.get("columns", [])
            mandatory = outlier_config.get("mandatory", True)
            method = outlier_config.get("method", "z-score")

        if "*" in columns:
            # Future: this type-based filter may be delegated to other execution engines
            columns = df.select_dtypes(include=['number']).columns.tolist()

        for col in columns:
            if not self._has_column(col) or not pd.api.types.is_numeric_dtype(df[col]):
                continue

            outlier_mask = pd.Series(False, index=df.index)

            if method == "z-score":
                mean = df[col].mean()
                std = df[col].std()
                if std > 0 and not np.isnan(std):
                    outlier_mask = np.abs((df[col] - mean) / std) > 3
            elif method == "iqr":
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                outlier_mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)

            outlier_count = int(outlier_mask.sum())
            if outlier_count > 0:
                examples = df.loc[outlier_mask, col].unique()[:5].tolist()
                self._build_result(
                    check_type="outlier_check",
                    passed=False,
                    mandatory=mandatory,
                    column=col,
                    metrics={"method": method, "count": outlier_count, "examples": examples},
                )

    def validate_empty_strings(self, empty_config: Any):
        """Detects strings that are just whitespace or truly empty."""
        df = self._working_df
        if isinstance(empty_config, list):
            columns = empty_config
            mandatory = True
        else:
            columns = empty_config.get("columns", [])
            mandatory = empty_config.get("mandatory", True)

        if "*" in columns:
            # Future: this type-based filter may be delegated to other execution engines
            columns = df.select_dtypes(include=['object']).columns.tolist()

        for col in columns:
            if not self._has_column(col):
                continue

            invalid_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
            empty_count = int(invalid_mask.sum())

            if empty_count > 0:
                self._build_result(
                    check_type="empty_string_check",
                    passed=False,
                    mandatory=mandatory,
                    column=col,
                    metrics={"empty_count": empty_count},
                )

    def validate_duplicate_rows(self, enabled: bool):
        """Checks for duplicate rows in the entire dataset."""
        if not enabled:
            return

        df = self._working_df
        duplicate_count = int(df.duplicated().sum())

        self._build_result(
            check_type="duplicate_row_check",
            passed=duplicate_count == 0,
            mandatory=True,
            metrics={"duplicate_count": duplicate_count},
        )

    def validate_schema_types(self, schema_config: Dict[str, str]):
        """Checks if column types match the expected schema."""
        df = self._working_df
        type_checkers = {
            "int": lambda c: pd.api.types.is_integer_dtype(df[c]),
            "float": lambda c: pd.api.types.is_float_dtype(df[c]),
            "string": lambda c: pd.api.types.is_string_dtype(df[c]) or str(df[c].dtype) == "category",
            "date": lambda c: pd.api.types.is_datetime64_any_dtype(df[c]),
        }

        for col, expected_type in schema_config.items():
            if not self._has_column(col):
                continue

            checker = type_checkers.get(expected_type)
            is_valid = checker(col) if checker else False

            self._build_result(
                check_type="schema_type_check",
                passed=is_valid,
                mandatory=True,
                column=col,
                metrics={"expected": expected_type, "actual": str(df[col].dtype)},
            )

    def validate_date_formats(self, date_config: List[Dict[str, Any]]):
        """Checks if date strings match the specified format."""
        df = self._working_df
        for rule in date_config:
            col = rule["column"]
            fmt = rule.get("format", "%Y-%m-%d")
            mandatory = rule.get("mandatory", True)

            if not self._has_column(col):
                continue

            series = df[col].astype(str)

            def is_valid_date(val):
                if pd.isna(val) or val == "nan" or not val.strip():
                    return True
                try:
                    pd.to_datetime(val, format=fmt)
                    return True
                except Exception:
                    return False

            valid_mask = series.map(is_valid_date)
            invalid_count = int((~valid_mask).sum())

            self._build_result(
                check_type="date_check",
                passed=invalid_count == 0,
                mandatory=mandatory,
                rule_id=rule.get("id", f"{col}_date_check"),
                column=col,
                metrics={"invalid_count": invalid_count, "format": fmt},
            )

    def validate_comparison(self, comparison_checks: List[Dict[str, Any]]):
        """Cross-column validation using AST-validated expressions."""
        df = self._working_df
        for rule in comparison_checks:
            equation = rule.get("equation")
            mandatory = rule.get("mandatory", True)
            if not equation:
                continue

            try:
                if not isinstance(equation, str):
                    raise ValueError(f"Equation must be a string, got {type(equation).__name__}")

                # AST WHITELIST: validate before execution
                _validate_expression(equation)

                valid_mask = df.eval(equation, engine='python')

                if not pd.api.types.is_bool_dtype(valid_mask):
                    actual_type = getattr(valid_mask, "dtype", type(valid_mask).__name__)
                    raise ValueError(f"Expression '{equation}' did not return a boolean mask (got {actual_type})")

                invalid_count = int((~valid_mask).sum())
                self._build_result(
                    check_type="comparison_check",
                    passed=invalid_count == 0,
                    mandatory=mandatory,
                    rule_id=rule.get("id", f"comparison_{equation[:30]}"),
                    metrics={"invalid_count": invalid_count},
                )
            except Exception as e:
                logger.error(f"[{self._execution_id}] Comparison failed | eq='{equation}' | error={e}")
                self._build_result(
                    check_type="comparison_check",
                    passed=False,
                    mandatory=mandatory,
                    rule_id=rule.get("id", f"comparison_{equation[:30]}"),
                    message=str(e),
                )

    def validate_lookup(self, lookup_checks: List[Dict[str, Any]]):
        """Validates if column values exist in an external reference dataset."""
        from sentinel_gate.execution.datasource import DataSource

        df = self._working_df
        for rule in lookup_checks:
            col = rule["column"]
            ref_config = rule["reference_source"]
            ref_col = rule["reference_column"]
            mandatory = rule.get("mandatory", True)

            try:
                # Cached reference loading
                ref_key = str(ref_config)
                if ref_key in self._ref_cache:
                    ref_df = self._ref_cache[ref_key]
                else:
                    ref_df = DataSource.load_data(ref_config)
                    self._ref_cache[ref_key] = ref_df

                if not self._has_column(col):
                    raise KeyError(f"Source column '{col}' not found in dataset")
                if ref_col not in ref_df.columns:
                    raise KeyError(f"Reference column '{ref_col}' not found in source '{ref_key}'")

                # Hybrid membership testing: set() for < 1M, direct isin for larger
                if len(ref_df) < 1_000_000:
                    valid_values = set(ref_df[ref_col])
                    invalid_mask = ~df[col].isin(valid_values)
                else:
                    invalid_mask = ~df[col].isin(ref_df[ref_col])

                invalid_count = int(invalid_mask.sum())
                ref_label = f"{ref_config.get('table') or os.path.basename(ref_config.get('file', 'ref'))}.{ref_col}"

                self._build_result(
                    check_type="lookup_check",
                    passed=invalid_count == 0,
                    mandatory=mandatory,
                    rule_id=rule.get("id", f"{col}_lookup_check"),
                    column=col,
                    metrics={"reference": ref_label, "invalid_count": invalid_count},
                )
            except Exception as e:
                cols_available = list(ref_df.columns) if 'ref_df' in dir() else []
                logger.error(f"[{self._execution_id}] Lookup failed | col={col} | ref={ref_config} | error={e} | ref_cols={cols_available}")
                self._build_result(
                    check_type="lookup_check",
                    passed=False,
                    mandatory=mandatory,
                    rule_id=rule.get("id", f"{col}_lookup_check"),
                    column=col,
                    message=f"Validation failed: {str(e)}",
                )

    def validate_units(self, unit_checks: List[Dict[str, Any]]):
        """Checks if values are within expected magnitudes for given units."""
        df = self._working_df
        for rule in unit_checks:
            col = rule["column"]
            unit = rule.get("unit", "unknown")
            min_mag = rule.get("min_magnitude")
            max_mag = rule.get("max_magnitude")
            mandatory = rule.get("mandatory", True)

            if not self._has_column(col):
                continue

            invalid_rows = pd.Series(False, index=df.index)
            if min_mag is not None:
                invalid_rows = invalid_rows | (df[col] < min_mag)
            if max_mag is not None:
                invalid_rows = invalid_rows | (df[col] > max_mag)

            invalid_count = int(invalid_rows.sum())
            self._build_result(
                check_type="unit_check",
                passed=invalid_count == 0,
                mandatory=mandatory,
                rule_id=rule.get("id", f"{col}_unit_check"),
                column=col,
                metrics={"unit": unit, "invalid_count": invalid_count},
            )

    def validate_timestamps(self, timestamp_checks: List[Dict[str, Any]]):
        """Validates timestamp formats (Unix vs ISO with Timezone indicators)."""
        df = self._working_df
        for rule in timestamp_checks:
            col = rule["column"]
            t_type = rule.get("format_type", "iso_timezone")
            mandatory = rule.get("mandatory", True)

            if not self._has_column(col):
                continue

            invalid_count = 0
            series = df[col]

            if t_type == "iso_timezone":
                tz_regex = self._get_compiled_regex(r'.*(?:[Z]|[+-]\d{2}:?\d{2})$')
                invalid_count = int((~series.astype(str).str.contains(tz_regex, na=False)).sum())
            elif t_type in ["unix_seconds", "unix_millis"]:
                num_series = pd.to_numeric(series, errors='coerce')
                if t_type == "unix_seconds":
                    valid_range = (num_series > 946684800) & (num_series < 4102444800)
                else:
                    valid_range = (num_series > 946684800000) & (num_series < 4102444800000)
                invalid_count = int((~(num_series.notnull() & valid_range)).sum())

            self._build_result(
                check_type="timestamp_check",
                passed=invalid_count == 0,
                mandatory=mandatory,
                rule_id=rule.get("id", f"{col}_timestamp_check"),
                column=col,
                metrics={"format_expected": t_type, "invalid_count": invalid_count},
            )

    # ------------------------------------------------------------------
    # 8. Rule Registry & Orchestration
    # ------------------------------------------------------------------
    def run_all(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Runs all data quality rules specified in the contract block.

        Uses a rule registry for clean, extensible execution.
        Returns { "summary": {...}, "results": [...] }
        """
        logger.info(f"[{self._execution_id}] Running all validations")

        # Reset state for safe re-runs
        self._collector = ResultCollector()
        self._working_df = self._original_df.copy()
        self.engine = PandasExecutionEngine(self._working_df)

        # Immutable contract
        local_contract = copy.deepcopy(contract)

        # Apply filter (on working df only)
        filter_query = local_contract.get("filter")
        if filter_query:
            self.apply_filter(filter_query)

        # --- Primary Key (special handling for legacy format) ---
        pk_config = self._get_contract_key(local_contract, "primary_key")
        if pk_config is not None:
            if isinstance(pk_config, list):
                self.validate_uniqueness({"columns": pk_config, "type": "primary_key_check", "mandatory": True})
            else:
                self.validate_uniqueness({**pk_config, "type": "primary_key_check"})

        # --- Uniqueness (special handling for list of checks) ---
        uq_checks = self._get_contract_key(local_contract, "uniqueness_checks")
        if uq_checks:
            for check in uq_checks:
                self.validate_uniqueness({**check, "type": "uniqueness_check"})

        # --- Rule Registry: maps contract key → validation method ---
        _RULE_REGISTRY: List[Tuple[Tuple[str, ...], Callable]] = [
            (("null_checks",),                  self.validate_nulls),
            (("domain_checks",),                self.validate_domain),
            (("numeric_checks",),               self.validate_numeric),
            (("volume_checks",),                self.validate_volume),
            (("constant_checks",),              self.validate_constants),
            (("outlier_checks",),               self.validate_outliers),
            (("empty_string_checks",),          self.validate_empty_strings),
            (("duplicate_row_check", "duplicate_check"),  self.validate_duplicate_rows),
            (("schema_check", "schema"),        self.validate_schema_types),
            (("date_checks",),                  self.validate_date_formats),
            (("comparison_checks",),            self.validate_comparison),
            (("lookup_checks",),                self.validate_lookup),
            (("unit_checks",),                  self.validate_units),
            (("timestamp_checks",),             self.validate_timestamps),
        ]

        for keys, func in _RULE_REGISTRY:
            cfg = self._get_contract_key(local_contract, *keys)
            if cfg is not None:
                func(cfg)

        return {
            "summary": self._collector.summary(),
            "results": self._collector.results,
        }
