"""DynamoDB serialization/deserialization helpers."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict


def serialize_for_dynamo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Python types to DynamoDB-compatible types.

    Converts floats to Decimal, datetimes to ISO strings, etc.
    """
    result = {}
    for key, value in data.items():
        result[key] = _convert_value(value)
    return result


def _convert_value(value: Any) -> Any:
    """Recursively convert a value for DynamoDB storage."""
    if isinstance(value, float):
        return Decimal(str(value))
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _convert_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_convert_value(item) for item in value]
    return value


def deserialize_from_dynamo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert DynamoDB types back to Python types.

    Converts Decimal back to float, etc.
    """
    result = {}
    for key, value in data.items():
        result[key] = _unconvert_value(value)
    return result


def _unconvert_value(value: Any) -> Any:
    """Recursively convert a DynamoDB value back to Python."""
    if isinstance(value, Decimal):
        if value == int(value):
            return int(value)
        return float(value)
    elif isinstance(value, dict):
        return {k: _unconvert_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_unconvert_value(item) for item in value]
    return value


def calculate_ttl(days: int) -> int:
    """Calculate TTL epoch timestamp for DynamoDB TTL attribute."""
    future = datetime.now(timezone.utc) + timedelta(days=days)
    return int(future.timestamp())
