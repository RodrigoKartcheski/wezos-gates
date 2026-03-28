import pandas as pd
import os
from sentinel_gate.core.discovery_engine import DiscoveryEngine

# Load the same file the user is using
csv_path = r"C:\Temp\executavel\sentinel_gate\tests\sample_data\sample_data.csv"
df = pd.read_csv(csv_path)

print(f"Dataset Rows: {len(df)}")
print("\nCardinality Analysis (nunique with dropna=False):")
for col in df.columns:
    nunique = df[col].nunique(dropna=False)
    print(f"Column: {col:15} | Unique Values: {nunique}")

print("\n--- Running DiscoveryEngine.detect_primary_keys ---")
engine = DiscoveryEngine(df)
result = engine.detect_primary_keys()

print(f"\nFinal Result: {result}")
