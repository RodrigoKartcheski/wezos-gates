import pandas as pd
from google.cloud import bigquery
from typing import Optional, Dict, Any
from sentinel_gate.utils.logger import logger

class DataSource:
    """Handles data loading from various sources (CSV, BigQuery)."""

    @staticmethod
    def load_from_csv(file_path: str, **kwargs) -> pd.DataFrame:
        """Loads data from a CSV file with optional auto-detection of delimiter."""
        try:
            logger.info(f"Loading CSV from {file_path}")
            # If sep is not provided, use sep=None and engine='python' for auto-detection
            if 'sep' not in kwargs:
                kwargs['sep'] = None
                kwargs['engine'] = 'python'
            return pd.read_csv(file_path, **kwargs)
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise

    @staticmethod
    def load_from_bigquery(
        project: str, 
        dataset: str, 
        table: str, 
        limit: int = 100000,
        where: Optional[str] = None,
        columns: Optional[list] = None
    ) -> pd.DataFrame:
        """Loads data from a BigQuery table."""
        try:
            client = bigquery.Client(project=project)
            cols = ", ".join(columns) if columns else "*"
            query = f"SELECT {cols} FROM `{project}.{dataset}.{table}`"
            if where:
                query += f" WHERE {where}"
            query += f" LIMIT {limit}"
            
            logger.info(f"Executing BQ query: {query}")
            return client.query(query).to_dataframe()
        except Exception as e:
            logger.error(f"Error loading from BigQuery: {e}")
            raise

    @classmethod
    def load_data(cls, source_config: Dict[str, Any]) -> pd.DataFrame:
        """Loads data based on the provided configuration dictionary."""
        source_type = source_config.get("type", "").lower()
        if source_type == "csv":
            csv_kwargs = {k: v for k, v in source_config.items() if k not in ["type", "file"]}
            return cls.load_from_csv(source_config["file"], **csv_kwargs)
        elif source_type == "bigquery":
            return cls.load_from_bigquery(
                project=source_config["project"],
                dataset=source_config["dataset"],
                table=source_config["table"],
                limit=source_config.get("limit", 100000),
                where=source_config.get("where"),
                columns=source_config.get("columns")
            )
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
