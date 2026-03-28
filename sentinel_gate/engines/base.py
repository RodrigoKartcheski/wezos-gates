from typing import List

class BaseExecutionEngine:
    """Minimal interface for data execution primitives.

    Concrete engines must implement these methods to support
    different data backends (Pandas, Spark, DuckDB, Polars, etc.).
    """

    def get_row_count(self) -> int:
        """Returns the number of rows in the active dataset."""
        raise NotImplementedError

    def get_columns(self) -> List[str]:
        """Returns the list of column names in the active dataset."""
        raise NotImplementedError

    def has_column(self, column: str) -> bool:
        """Checks if a column exists in the active dataset."""
        return column in self.get_columns()

    def get_dataframe(self):
        """Returns the underlying data object for engine-specific operations."""
        raise NotImplementedError
