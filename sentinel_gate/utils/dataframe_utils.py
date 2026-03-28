import pandas as pd
from typing import List, Optional

def get_column_types(df: pd.DataFrame) -> dict:
    """Returns a dictionary mapping column names to their pandas types."""
    return df.dtypes.apply(lambda x: x.name).to_dict()

def sample_dataframe(df: pd.DataFrame, sample_size: Optional[int] = None) -> pd.DataFrame:
    """Samples the dataframe if sample_size is provided."""
    if sample_size and len(df) > sample_size:
        return df.sample(n=sample_size)
    return df
