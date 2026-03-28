import sys
import os
sys.path.insert(0, os.path.abspath("."))

print("BOOTSTRAP: sys.path updated")

import pandas as pd
from sentinel_gate.execution.orchestrator import run_data_quality_workflow

if __name__ == "__main__":
    print("MAIN: Starting...")
    test_csv = "debug_parallel.csv"
    df = pd.DataFrame({"id": range(100), "val": [1, 2] * 50})
    df.to_csv(test_csv, index=False)
    
    contract = {
        "source": {
            "type": "csv",
            "file": test_csv,
            "chunk_size": 20,
            "parallel_workers": 2
        },
        "quality_rules": {
            "null_checks": [{"column": "val"}]
        }
    }
    
    print("MAIN: Running workflow...")
    result = run_data_quality_workflow(contract, output_dir="reports_debug")
    print(f"MAIN: Result: {result}")
    
    if os.path.exists(test_csv):
        os.remove(test_csv)
    print("MAIN: Done.")
