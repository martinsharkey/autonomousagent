import json
from typing import Any, Dict, List, Union

def validate_schema(data: Union[Dict[str, Any], List[Any]], schema: Dict[str, Any]) -> bool:
    """Validate data against a JSON schema.
    
    Args:
        data: Input data to validate (dict or list)
        schema: JSON schema to validate against
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        return True
    except (jsonschema.ValidationError, ImportError):
        # Fallback simple validation if jsonschema not available
        return _simple_validation(data, schema)

def _simple_validation(data: Union[Dict[str, Any], List[Any]], schema: Dict[str, Any]) -> bool:
    """Basic schema validation without external dependencies."""
    if "type" in schema:
        expected_type = schema["type"]
        if expected_type == "object" and not isinstance(data, dict):
            return False
        if expected_type == "array" and not isinstance(data, list):
            return False
        if expected_type == "string" and not isinstance(data, str):
            return False
        if expected_type == "number" and not isinstance(data, (int, float)):
            return False
    return True

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """Check if all required fields are present in the data."""
    return all(field in data for field in required_fields)