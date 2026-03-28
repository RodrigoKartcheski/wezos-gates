import pandas as pd
from typing import List
from sentinel_gate.engines.base import BaseExecutionEngine

class PandasExecutionEngine(BaseExecutionEngine):
    """Concrete execution engine backed by Pandas DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self._df = df

    def get_row_count(self) -> int:
        return len(self._df)

    def get_columns(self) -> List[str]:
        return self._df.columns.tolist()

    def get_dataframe(self) -> pd.DataFrame:
        return self._df

    def set_dataframe(self, df: pd.DataFrame):
        """Replaces the internal working dataframe (used by filters)."""
        self._df = df
