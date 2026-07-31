import pandas as pd

def validate_data(df: pd.DataFrame, required_columns: list) -> bool:
    """Validate if DataFrame contains all required columns."""
    return all(col in df.columns for col in required_columns)

def validate_types(df: pd.DataFrame, column_types: dict) -> bool:
    """Validate if DataFrame columns match specified types."""
    return all(df[col].dtype == dtype for col, dtype in column_types.items())