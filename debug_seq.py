import sys
import os
import traceback
import pandas as pd

# Path injection
sys.path.insert(0, os.path.abspath("."))

if __name__ == "__main__":
    print("DEBUG: BEGIN")
    from sentinel_gate.execution.orchestrator import run_data_quality_workflow
    
    test_csv = "debug_seq.csv"
    df = pd.DataFrame({"id": range(100), "val": range(100)})
    df.to_csv(test_csv, index=False)
    print("DEBUG: CSV CREATED")
    
    contract = {
        "source": {
            "type": "csv",
            "file": test_csv,
            "chunk_size": 20,
            "parallel_workers": 2
        },
        "quality_rules": {
            "null_checks": [{"column": "id"}]
        }
    }
    
    try:
        print("DEBUG: CALLING WORKFLOW (PARALLEL)")
        result = run_data_quality_workflow(contract, output_dir="reports_debug_parallel")
        print(f"DEBUG: SUCCESS: {result['mode']} mode, score: {result['scores']['final_score']}")
    except Exception:
        traceback.print_exc()
    finally:
        if os.path.exists(test_csv):
            os.remove(test_csv)
    print("DEBUG: END")
