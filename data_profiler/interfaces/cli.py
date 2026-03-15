import argparse
import sys
import os
from data_profiler.config.config_parser import ConfigParser
from data_profiler.workflow import run_data_quality_workflow
from data_profiler.utils.logger import logger

def run_cli():
    """Defines and runs the CLI for the data profiler."""
    parser = argparse.ArgumentParser(description="Data Quality & Profiling Tool")
    
    # Execution modes
    parser.add_argument("--config", help="Path to rules.json configuration file")
    parser.add_argument("--mcp", action="store_true", help="Run as MCP server")
    
    # Overrides/Manual mode
    parser.add_argument("--source", choices=["csv", "bigquery"], help="Data source type")
    parser.add_argument("--file", help="Path to CSV file")
    parser.add_argument("--reference", help="Path to reference CSV file (for drift detection)")
    parser.add_argument("--project", help="BigQuery project ID")
    parser.add_argument("--dataset", help="BigQuery dataset ID")
    parser.add_argument("--table", help="BigQuery table name")
    
    # BigQuery Reference
    parser.add_argument("--ref-project", help="Reference BQ project ID")
    parser.add_argument("--ref-dataset", help="Reference BQ dataset ID")
    parser.add_argument("--ref-table", help="Reference BQ table name")
    
    # Validation overrides
    parser.add_argument("--check-nulls", help="Comma separated list of columns to check for nulls")
    parser.add_argument("--group-by", help="Comma separated list of columns for group by")
    parser.add_argument("--output", default="reports", help="Output directory for reports")
    
    # Discovery flags
    parser.add_argument("--check-keys", action="store_true", default=True, help="Attempt to detect primary/composite keys (Enabled by default)")
    parser.add_argument("--check-outliers", help="Comma separated list of columns to check for outliers (or * for all numeric)")
    parser.add_argument("--check-dates", help="Comma separated list of columns to analyze dates (or * for all date types)")
    parser.add_argument("--check-constants", action="store_true", help="Identify columns with constant values")
    parser.add_argument("--check-empty", help="Comma separated list of columns to check for empty strings")

    args = parser.parse_args()

    if args.mcp:
        from data_profiler.interfaces.mcp_server import run_mcp_server
        run_mcp_server()
        return

    # Enforce --source as mandatory (unless in MCP mode)
    if not args.source:
        print("Error: --source [csv|bigquery] is mandatory.")
        parser.print_help()
        sys.exit(1)

    config = {}
    if args.config:
        config = ConfigParser.parse(args.config)
    
    # Merge/Override with CLI flags if provided
    # Source type is now guaranteed to be present from args.source or manual check above
    config.setdefault("source", {})["type"] = args.source
    
    if args.file:
        config["source"]["file"] = args.file
    
    # If BQ flags are passed, they imply 'bigquery' (though source is already set)
    if any([args.project, args.dataset, args.table]):
        config["source"].update({
            "project": args.project or config["source"].get("project"),
            "dataset": args.dataset or config["source"].get("dataset"),
            "table": args.table or config["source"].get("table")
        })

    # Final validation based on source type
    src = config["source"]
    if src["type"] == "csv":
        if not src.get("file"):
            print("Error: --file is required for CSV source (via CLI or config)")
            sys.exit(1)
        if args.reference:
            config["reference"] = {"type": "csv", "file": args.reference}
    elif src["type"] == "bigquery":
        if not all([src.get("project"), src.get("dataset"), src.get("table")]):
            print("Error: BigQuery requires project, dataset, and table")
            sys.exit(1)
        if all([args.ref_project, args.ref_dataset, args.ref_table]):
            config["reference"] = {"type": "bigquery", "project": args.ref_project, "dataset": args.ref_dataset, "table": args.ref_table}
        
    if args.check_nulls:
        config.setdefault("validations", {})["null_checks"] = [{"column": c} for c in args.check_nulls.split(",")]
    
    if args.group_by:
        # Per user request, we treat group_by as a discovery task if possible
        # We also maintain the one in validations if it's there
        disco = config.setdefault("discovery", {})
        disco["group_by"] = [args.group_by.split(",")]

    # Map new discovery/exploratory flags
    config.setdefault("discovery", {})["detect_keys"] = args.check_keys
    
    if args.check_dates:
        config.setdefault("discovery", {})["date_analysis"] = args.check_dates.split(",")
    
    if args.check_outliers:
        config.setdefault("validations", {})["outlier_checks"] = args.check_outliers.split(",")
    if args.check_constants:
        config.setdefault("validations", {})["constant_checks"] = ["*"]
    if args.check_empty:
        config.setdefault("validations", {})["empty_string_checks"] = args.check_empty.split(",")

    if not config:

        parser.print_help()
        sys.exit(1)

    try:
        run_data_quality_workflow(config, output_dir=args.output)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_cli()
