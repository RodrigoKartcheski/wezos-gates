from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, model_validator, RootModel

class SourceConfig(BaseModel):
    type: str = Field(..., pattern="^(csv|bigquery)$")
    file: Optional[str] = None
    project: Optional[str] = None
    dataset: Optional[str] = None
    table: Optional[str] = None
    sep: str = ","
    encoding: str = "utf-8"
    chunk_size: Optional[int] = None

    @model_validator(mode="after")
    def validate_source_dependencies(self):
        if self.type == "csv" and not self.file:
            raise ValueError("Field 'file' is required for CSV source")
        if self.type == "bigquery" and not self.table:
            raise ValueError("Field 'table' is required for BigQuery source")
        return self

class BaseRule(BaseModel):
    mandatory: bool = True
    id: Optional[str] = None

class NullCheck(BaseRule):
    column: str
    max_percent: float = 0.0

class DomainCheck(BaseRule):
    column: str
    allowed_values: Optional[List[Any]] = None
    forbidden_values: Optional[List[Any]] = None
    regex: Optional[str] = None

class NumericCheck(BaseRule):
    column: str
    min: Optional[float] = None
    max: Optional[float] = None
    allow_negative: bool = True

class VolumeCheck(BaseRule):
    min_rows: Optional[int] = None
    max_rows: Optional[int] = None

class ComparisonCheck(BaseRule):
    equation: str

class LookupCheck(BaseRule):
    column: str
    reference_source: Dict[str, Any] # Can be CSV or BQ
    reference_column: str

class UnitCheck(BaseRule):
    column: str
    unit: str
    min_magnitude: Optional[float] = None
    max_magnitude: Optional[float] = None

class TimestampCheck(BaseRule):
    column: str
    format_type: str = "iso_timezone"

class ValidationRules(BaseModel):
    primary_key: Optional[Union[List[str], Dict[str, Any]]] = None
    null_checks: Optional[List[NullCheck]] = None
    domain_checks: Optional[List[DomainCheck]] = None
    numeric_checks: Optional[List[NumericCheck]] = None
    volume_checks: Optional[VolumeCheck] = None
    constant_checks: Optional[Union[List[str], Dict[str, Any]]] = None
    outlier_checks: Optional[Union[List[str], Dict[str, Any]]] = None
    empty_string_checks: Optional[Union[List[str], Dict[str, Any]]] = None
    duplicate_check: bool = False
    schema_type_checks: Optional[Dict[str, str]] = Field(None, alias="schema")
    date_checks: Optional[List[Dict[str, Any]]] = None
    comparison_checks: Optional[List[ComparisonCheck]] = None
    lookup_checks: Optional[List[LookupCheck]] = None
    unit_checks: Optional[List[UnitCheck]] = None
    timestamp_checks: Optional[List[TimestampCheck]] = None

class DiscoveryConfig(BaseModel):
    filter: Optional[str] = None
    detect_keys: bool = False
    group_by: Optional[List[Union[str, List[str]]]] = None
    date_analysis: Optional[List[str]] = None
    dedupIncludeColumns: Optional[List[str]] = None
    dedupExcludeColumns: Optional[List[str]] = None

class ProfilingConfig(BaseModel):
    title: Optional[str] = None
    filter: Optional[str] = None

class SentinelConfig(BaseModel):
    source: SourceConfig
    validations: Optional[ValidationRules] = None
    discovery: Optional[DiscoveryConfig] = None
    profiling: Optional[ProfilingConfig] = None
    reference: Optional[SourceConfig] = None
