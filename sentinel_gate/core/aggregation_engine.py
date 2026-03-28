import pandas as pd
from typing import List, Dict, Any
from sentinel_gate.utils.logger import logger
from sentinel_gate.utils.sql_utils import apply_sql_filter

class AggregationEngine:
    """Runs group-by validations and metric checks."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.original_row_count = len(df)
        self.results = []

    def apply_filter(self, filter_query: str):
        """Applies a SQL-like filter to the internal dataframe."""
        self.df = apply_sql_filter(self.df, filter_query)
        return self.df

    def validate_group_by(self, group_by_checks: List[Dict[str, Any]]):
        """
        Executes group-by and checks metrics.
        Example rule: {"group_by": ["status"], "metrics": ["count"], "min_count": 10}
        """
        for rule in group_by_checks:
            groups = rule["group_by"]
            metrics = rule.get("metrics", ["count"])
            
            agg_df = self.df.groupby(groups).size().reset_index(name='count')
            # For simplicity, implementing only 'count' validation for now
            # Can be extended to sum, avg, etc.
            
            min_count = rule.get("min_count")
            status = "PASS"
            if min_count is not None:
                if (agg_df['count'] < min_count).any():
                    status = "FAIL"

            self.results.append({
                "type": "group_by_check",
                "groups": groups,
                "status": status,
                "summary": agg_df.to_dict(orient="records")[:10] # Top 10 for report
            })

    def run(self, config: List[Dict[str, Any]], filter_query: str = None):
        logger.info("Running aggregation checks")
        if filter_query:
            self.apply_filter(filter_query)
        if config:
            self.validate_group_by(config)
        return self.results
