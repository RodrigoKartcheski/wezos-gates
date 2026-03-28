import unittest
import pandas as pd
import os
import json
import time
from sentinel_gate.execution.orchestrator import run_data_quality_workflow

class TestParallelExecution(unittest.TestCase):
    def setUp(self):
        self.test_csv = "parallel_test_data.csv"
        # Create a CSV with 200 rows
        df = pd.DataFrame({
            "id": range(200),
            "val": [10, 20, 30, 40, 50] * 40,
            "status": ["ATIVO", "INATIVO"] * 100,
            "email": ["test@example.com"] * 180 + [None] * 20
        })
        df.to_csv(self.test_csv, index=False)

    def tearDown(self):
        try:
            if os.path.exists(self.test_csv):
                os.remove(self.test_csv)
        except:
            pass

    def test_parallel_workflow(self):
        contract = {
            "source": {
                "type": "csv",
                "file": self.test_csv,
                "chunk_size": 40, # 5 chunks
                "parallel_workers": 2
            },
            "quality_rules": {
                "null_checks": [
                    {"column": "email", "max_percent": 15}
                ],
                "numeric_checks": [
                    {"column": "val", "min": 0}
                ]
            }
        }
        
        start_time = time.time()
        result = run_data_quality_workflow(contract, output_dir="reports_parallel")
        end_time = time.time()
        
        print(f"\nParallel Workflow took {end_time - start_time:.2f} seconds")
        self.assertEqual(result["mode"], "chunked")
        self.assertGreater(result["scores"]["final_score"], 0)

if __name__ == "__main__":
    unittest.main()
