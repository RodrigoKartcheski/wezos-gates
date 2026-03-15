from mcp.server.fastmcp import FastMCP
from data_profiler.workflow import run_data_quality_workflow
from data_profiler.core.datasource import DataSource
from data_profiler.core.schema_inference import SchemaInference
from data_profiler.utils.logger import logger
import json

mcp = FastMCP("Data Profiler")

@mcp.tool()
async def load_and_validate(config_json: str) -> str:
    """
    Runs the full validation workflow based on a JSON configuration.
    Returns the final report as a JSON string.
    """
    try:
        config = json.loads(config_json)
        result = run_data_quality_workflow(config)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def infer_dataset_schema(source_type: str, path_or_table: str) -> str:
    """
    Infers the schema of a dataset without running full validation.
    """
    try:
        if source_type == "csv":
            df = DataSource.load_from_csv(path_or_table)
        else:
            # Simplified for BQ; expects "project.dataset.table"
            parts = path_or_table.split(".")
            df = DataSource.load_from_bigquery(parts[0], parts[1], parts[2])
            
        schema = SchemaInference.infer_schema(df)
        return json.dumps(schema, indent=2)
    except Exception as e:
        return f"Error: {str(e)}"

def run_mcp_server():
    """Starts the MCP server."""
    logger.info("Starting MCP Server")
    mcp.run()
