import pandas as pd

def validate_data(df: pd.DataFrame, required_columns: list) -> bool:
    """Check if DataFrame contains all required columns."""
    return all(col in df.columns for col in required_columns)

def validate_types(df: pd.DataFrame, type_spec: dict) -> bool:
    """Validate DataFrame column types against specification."""
    return all(df[col].dtype == dtype for col, dtype in type_spec.items())