import pandas as pd
import unittest
from sentinel_gate.core.schema_inference import SchemaInference
from sentinel_gate.core.validation_engine import ValidationEngine
from sentinel_gate.core.aggregation_engine import AggregationEngine

class TestDataQualityCore(unittest.TestCase):

    def setUp(self):
        # Create a sample dataframe for testing
        data = {
            'id': [1, 2, 3, 4],
            'valor': [10.5, 20.0, None, 15.2],
            'status': ['A', 'A', 'B', 'C'],
            'data': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-12-01']
        }
        self.df = pd.DataFrame(data)

    def test_schema_inference(self):
        inferred = SchemaInference.infer_schema(self.df)
        self.assertEqual(inferred['id']['inferred_type'], 'integer')
        self.assertEqual(inferred['valor']['inferred_type'], 'float')
        self.assertEqual(inferred['status']['inferred_type'], 'categorical')
        self.assertEqual(inferred['data']['inferred_type'], 'datetime')

    def test_validation_nulls(self):
        engine = ValidationEngine(self.df)
        # Test max 25% nulls on 'valor' (1/4 is 25%, so should pass)
        engine.validate_nulls([{"column": "valor", "max_percent": 30}])
        self.assertEqual(engine.results[0]['status'], 'PASS')
        
        # Test max 0% nulls on 'valor' (should fail)
        engine.results = []
        engine.validate_nulls([{"column": "valor", "max_percent": 0}])
        self.assertEqual(engine.results[0]['status'], 'FAIL')

    def test_validation_uniqueness(self):
        engine = ValidationEngine(self.df)
        engine.validate_uniqueness(['id'])
        self.assertEqual(engine.results[0]['status'], 'PASS')
        
        # Add a duplicate
        df_dup = pd.concat([self.df, self.df.iloc[[0]]])
        engine_dup = ValidationEngine(df_dup)
        engine_dup.validate_uniqueness(['id'])
        self.assertEqual(engine_dup.results[0]['status'], 'FAIL')

    def test_validation_numeric(self):
        engine = ValidationEngine(self.df)
        engine.validate_numeric([{"column": "id", "min": 1, "max": 10}])
        self.assertEqual(engine.results[0]['status'], 'PASS')
        
        engine.results = []
        engine.validate_numeric([{"column": "id", "min": 2}]) # 1 is less than 2
        self.assertEqual(engine.results[0]['status'], 'FAIL')

    def test_aggregation_count(self):
        engine = AggregationEngine(self.df)
        # Group by status, min count 1 (all status have at least 1)
        results = engine.run([{"group_by": ["status"], "min_count": 1}])
        self.assertEqual(results[0]['status'], 'PASS')
        
        # Min count 3 (only 'A' has 2, so should fail)
        results = engine.run([{"group_by": ["status"], "min_count": 3}])
        self.assertEqual(results[1]['status'], 'FAIL')

if __name__ == '__main__':
    unittest.main()
