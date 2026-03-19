import re
import pandas as pd
from data_profiler.utils.logger import logger

def apply_sql_filter(df: pd.DataFrame, filter_query: str) -> pd.DataFrame:
    """Applies a SQL-like WHERE clause filter to a Pandas DataFrame."""
    if not filter_query:
        return df
        
    logger.info(f"Applying filter: {filter_query}")
    
    # 1. Translate SQL operators to Python/Pandas
    # Use regex to replace '=' with '==' but avoid '!=' or '<=' or '>='
    q = re.sub(r'(?<![<>!])=(?!=)', '==', filter_query)
    q = q.replace("<>", "!=")
    
    # 2. Handle LIKE 'pattern'
    # Example: nome LIKE 'A%' -> nome.str.contains('^A.*$', na=False)
    like_regex = re.compile(r"(\w+)\s+LIKE\s+'([^']+)'", re.IGNORECASE)
    
    def translate_like(match):
        col, pattern = match.groups()
        # Convert SQL LIKE % to regex .* and _ to .
        regex_pattern = pattern.replace("%", ".*").replace("_", ".")
        # Ensure it's anchored
        return f"{col}.str.contains('^{regex_pattern}$', na=False, regex=True)"

    q = like_regex.sub(translate_like, q)
    
    # 3. Handle logical operators (AND/OR)
    q = re.sub(r'\bAND\b', 'and', q, flags=re.IGNORECASE)
    q = re.sub(r'\bOR\b', 'or', q, flags=re.IGNORECASE)
    
    logger.info(f"Translated query: {q}")
    
    try:
        filtered_df = df.query(q, engine='python')
        logger.info(f"Filter applied successfully. Rows remaining: {len(filtered_df)}")
        return filtered_df
    except Exception as e:
        logger.error(f"Error applying filter: {e}")
        return df
