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
    def load_data(cls, source_config: Dict[str, Any]):
        """Loads data based on the provided configuration dictionary (supports chunking)."""
        source_type = source_config.get("type", "").lower()
        chunk_size = source_config.get("chunk_size")
        
        if source_type == "csv":
            csv_kwargs = {k: v for k, v in source_config.items() if k not in ["type", "file", "chunk_size"]}
            if chunk_size:
                csv_kwargs["chunksize"] = chunk_size
                logger.info(f"Loading CSV in chunks of {chunk_size}")
            return cls.load_from_csv(source_config["file"], **csv_kwargs)
            
        elif source_type == "bigquery":
            # For BQ, we can use to_dataframe_iterable for chunking
            limit = source_config.get("limit", 100000)
            if chunk_size:
                logger.info(f"Loading BigQuery data in chunks of {chunk_size}")
                # Note: This is an abstraction, real BQ chunking is complex
                # but to_dataframe_iterable() works well for smaller chunks.
                return cls.load_from_bigquery_chunked(
                    project=source_config["project"],
                    dataset=source_config["dataset"],
                    table=source_config["table"],
                    chunk_size=chunk_size,
                    limit=limit
                )
            
            return cls.load_from_bigquery(
                project=source_config["project"],
                dataset=source_config["dataset"],
                table=source_config["table"],
                limit=limit,
                where=source_config.get("where"),
                columns=source_config.get("columns")
            )
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    @staticmethod
    def load_from_bigquery_chunked(project: str, dataset: str, table: str, chunk_size: int, limit: int):
        """Mock/Wrapper for BQ chunked loading using page iteration."""
        client = bigquery.Client(project=project)
        query = f"SELECT * FROM `{project}.{dataset}.{table}` LIMIT {limit}"
        query_job = client.query(query)
        # BQ client can result in a RowIterator which we can page through
        results = query_job.result(page_size=chunk_size)
        for page in results.pages:
            yield page.to_dataframe()
