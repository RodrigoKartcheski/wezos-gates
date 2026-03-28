import pandas as pd
import numpy as np
import re
from datetime import date
from typing import List, Dict, Any, Optional
from sentinel_gate.utils.logger import logger
from sentinel_gate.utils.sql_utils import apply_sql_filter

class DiscoveryEngine:
    """Engine for exploratory data discovery (PK detection, date analysis, etc.)."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.original_row_count = len(df)
        self.results = {}

    def apply_filter(self, filter_query: str):
        """Applies a SQL-like filter to the internal dataframe."""
        self.df = apply_sql_filter(self.df, filter_query)
        return self.df

    def detect_primary_keys(self, colunas_ignoradas: Optional[List[str]] = None, max_search: int = 8) -> Dict[str, Any]:
        """Iteratively detects primary keys or composite keys with detailed history."""
        logger.info("Detecting primary keys via cardinality analysis")
        total_rows = len(self.df)
        total_cols = len(self.df.columns)
        
        if total_rows == 0:
            return {"status": "SKIP", "message": "Zero rows in dataset"}

        if colunas_ignoradas is None:
            colunas_ignoradas = ['dh_upload', 'dh_uploaded_at', 'uploaded_at']

        distinct_counts = []
        for col in self.df.columns:
            if col.lower() in [c.lower() for c in colunas_ignoradas]:
                continue
            nunique = self.df[col].nunique(dropna=False)
            distinct_counts.append({'coluna': col, 'distinct_count': nunique})

        # Sort by highest cardinality first
        distinct_counts.sort(key=lambda x: x['distinct_count'], reverse=True)
        colunas_ordenadas = [item['coluna'] for item in distinct_counts]

        if not colunas_ordenadas:
            return {"status": "FAIL", "message": "No valid columns for PK detection"}

        # Store basic stats
        res = {
            "total_rows": total_rows,
            "total_cols": total_cols,
            "distinct_counts": distinct_counts,
            "composite_history": []
        }

        # 1. Check single columns (Find all candidates)
        candidates = []
        for item in distinct_counts:
            if item['distinct_count'] == total_rows:
                candidates.append(item['coluna'])
        
        if candidates:
            res.update({"status": "PASS", "type": "SINGLE", "columns": candidates, "distinct_count": total_rows})
            self.results["primary_key"] = res
            return res

        # 2. Iterative concatenation (Greedy approach for composite keys)
        colunas_combinadas = []
        max_search = min(len(colunas_ordenadas), max_search)
        for r in range(2, max_search + 1):
            subset_cols = colunas_ordenadas[:r]
            # 4.6 STAFF FIX: Use .ngroups instead of drop_duplicates() to avoid memory explosion
            distinct_combo = self.df.groupby(subset_cols).ngroups
            
            res["composite_history"].append({
                "columns": subset_cols,
                "distinct_count": distinct_combo
            })
            
            if distinct_combo == total_rows:
                res.update({"status": "PASS", "type": "COMPOSITE", "columns": subset_cols, "distinct_count": distinct_combo})
                self.results["primary_key"] = res
                return res

        res.update({"status": "FAIL", "message": f"No unique combination found among top {max_search} columns analyzed."})
        self.results["primary_key"] = res
        return res

    def analyze_dates(self, columns: List[str]) -> Dict[str, Any]:
        """Analyzes latest dates and distribution per day."""
        logger.info(f"Analyzing date columns: {columns}")
        
        # Expand wildcard
        if "*" in columns:
            columns = self.df.columns.tolist()

        date_results = []
        for col in columns:
            if col not in self.df.columns:
                continue
            
            dtype = str(self.df[col].dtype)
            is_date = "datetime64" in dtype or "date" in dtype.lower()
            
            if not is_date:
                # Try soft check if wildcard was used
                if "*" in columns: continue
            
            try:
                temp_series = pd.to_datetime(self.df[col], errors='coerce')
                max_val = temp_series.max()
                
                if pd.isna(max_val):
                    continue

                # Distribution (Top 5 days for summary)
                counts = temp_series.dt.date.value_counts().sort_index(ascending=False).head(10)
                dist = [{"date": str(d), "count": int(c)} for d, c in counts.items()]

                date_results.append({
                    "column": col,
                    "max_date": str(max_val),
                    "distribution": dist
                })
            except Exception as e:
                logger.warning(f"Could not analyze date column {col}: {e}")

        self.results["dates"] = date_results
        return {"date_analysis": date_results}

    def analyze_groups(self, groups: List[Any]) -> List[Dict[str, Any]]:
        """Performs frequency analysis (Group By) on specified columns."""
        logger.info(f"Analyzing discovery groups: {groups}")
        group_results = []
        
        # SQL style: if a list of strings is provided, treat it as ONE group of columns
        if groups and all(isinstance(g, str) for g in groups):
            groups = [groups]
            
        for g in groups:
            # Handle both list of columns or single column
            cols = g if isinstance(g, list) else [g]
            
            # Filter valid columns
            valid_cols = [c for c in cols if c in self.df.columns]
            if not valid_cols:
                continue
                
            try:
                # Top 10 combinations
                counts = self.df[valid_cols].value_counts(dropna=False).head(10)
                
                rows = []
                for idx, count in counts.items():
                    # Format index: handle tuples (multi-column) and scalars (single-column)
                    if isinstance(idx, tuple):
                        val_display = " | ".join([str(v) for v in idx])
                    else:
                        val_display = str(idx)
                        
                    rows.append({
                        "values": val_display,
                        "count": int(count),
                        "percent": round((count / len(self.df)) * 100, 2)
                    })
                
                group_results.append({
                    "columns": valid_cols,
                    "data": rows
                })
            except Exception as e:
                logger.warning(f"Could not analyze group {valid_cols}: {e}")

        self.results["group_analysis"] = group_results
        return group_results

    def check_deduplication(self, columns: List[str], label: str, excluded_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Checks for duplicates considering a specific set of columns."""
        logger.info(f"Checking deduplication for {label}: {columns}")
        
        # Filter valid columns
        valid_cols = [c for c in columns if c in self.df.columns]
        if not valid_cols:
            return {"status": "SKIP", "message": "No valid columns for deduplication check"}
            
        total_rows = len(self.df)
        if total_rows == 0:
            return {"status": "SKIP", "message": "Zero rows in dataset"}

        # count duplicates
        duplicate_count = self.df.duplicated(subset=valid_cols, keep='first').sum()
        
        res = {
            "label": label,
            "columns": valid_cols,
            "excluded_columns": excluded_columns or [],
            "duplicate_count": int(duplicate_count),
            "duplicate_percent": round((duplicate_count / total_rows) * 100, 2),
            "status": "PASS"
        }
        return res

    def run_all(self, contract: Dict[str, Any]):
        """Runs discovery based on contract."""
        # 1. Basic Stats (Always on original data)
        total_rows = len(self.df)
        total_cols = len(self.df.columns)
        self.results["stats"] = {
            "total_rows": total_rows,
            "total_cols": total_cols,
            "total_size_bytes": self.df.memory_usage(deep=True).sum()
        }

        # 0. Handle Filter (New: Information only, not restricting main analysis)
        filter_query = contract.get("filter")
        if filter_query:
            filtered_df = apply_sql_filter(self.df, filter_query)
            self.results["filter"] = filter_query
            self.results["original_row_count"] = total_rows
            self.results["filtered_row_count"] = len(filtered_df)
            # Capture sample of filtered rows (first 10)
            self.results["filtered_sample"] = filtered_df.head(10).to_dict(orient='records')

        # 2. PK Detection
        if contract.get("detect_keys", False):
            self.detect_primary_keys()
        else:
            distinct_counts = []
            for col in self.df.columns:
                distinct_counts.append({'coluna': col, 'distinct_count': self.df[col].nunique(dropna=False)})
            distinct_counts.sort(key=lambda x: x['distinct_count'], reverse=True)
            self.results["primary_key"] = {
                "status": "NOT_RUN",
                "distinct_counts": distinct_counts
            }
        
        # 3. Advanced Deduplication (New)
        dedup_results = []
        
        # Include logic
        includ_cols = contract.get("dedup_include_columns") or contract.get("dedupIncludeColumns")
        if includ_cols:
            dedup_results.append(self.check_deduplication(includ_cols, "Include Columns"))
            
        # Exclude logic
        exclud_cols = contract.get("dedup_exclude_columns") or contract.get("dedupExcludeColumns")
        if exclud_cols:
            all_cols = self.df.columns.tolist()
            target_cols = [c for c in all_cols if c not in exclud_cols]
            dedup_results.append(self.check_deduplication(target_cols, "Exclude Columns", excluded_columns=exclud_cols))
            
        if dedup_results:
            self.results["deduplication"] = dedup_results

            # Semantic Risk Auditor
            max_dup_pct = 0.0
            for dr in dedup_results:
                if dr["status"] == "PASS" and dr["duplicate_percent"] > max_dup_pct:
                    max_dup_pct = dr["duplicate_percent"]
                    
            risk_level = "LOW"
            if max_dup_pct > 20.0:
                risk_level = "HIGH"
            elif max_dup_pct > 5.0:
                risk_level = "MEDIUM"
                
            # False Uniqueness Check: PK is valid but business columns are duplicated
            false_uniqueness = False
            pk_result = self.results.get("primary_key", {})
            # 3.7 BUG FIX: status is 'PASS' for valid PK
            if pk_result.get("status") == "PASS" and max_dup_pct > 0:
                false_uniqueness = True
                
            self.results["semantic_risk"] = {
                "risk_level": risk_level,
                "max_duplicate_percent": max_dup_pct,
                "false_uniqueness": false_uniqueness
            }

        # 4. Discovery Groups
        discovery_groups = contract.get("group_by")
        if discovery_groups:
            self.analyze_groups(discovery_groups)

        date_cols = contract.get("date_analysis")
        if date_cols:
            self.analyze_dates(date_cols if isinstance(date_cols, list) else ["*"])
            
        return self.results
