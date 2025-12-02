"""
Input Size Validation Utility - Week 2.5
Prevents memory exhaustion and DoS attacks by validating request sizes

Usage:
    from shared.input_size_validator import validate_request_size, validate_json_field

    # In lambda_handler:
    validate_request_size(event, max_size_mb=10)
    validate_json_field(event, 'scenes', max_count=100, max_item_size_kb=50)
"""

import json
import sys


class RequestSizeTooLargeError(Exception):
    """Raised when request exceeds size limits"""
    pass


def get_object_size_bytes(obj):
    """
    Calculate approximate size of Python object in bytes

    Args:
        obj: Any Python object (dict, list, str, etc.)

    Returns:
        int: Approximate size in bytes
    """
    if isinstance(obj, str):
        return len(obj.encode('utf-8'))
    elif isinstance(obj, (int, float)):
        return sys.getsizeof(obj)
    elif isinstance(obj, dict):
        return sum(get_object_size_bytes(k) + get_object_size_bytes(v) for k, v in obj.items())
    elif isinstance(obj, (list, tuple)):
        return sum(get_object_size_bytes(item) for item in obj)
    else:
        return sys.getsizeof(obj)


def validate_request_size(event, max_size_mb=10):
    """
    Validate total request size

    Args:
        event (dict): Lambda event object
        max_size_mb (int): Maximum allowed size in megabytes

    Raises:
        RequestSizeTooLargeError: If request exceeds size limit

    Example:
        validate_request_size(event, max_size_mb=10)  # 10MB limit
    """
    max_size_bytes = max_size_mb * 1024 * 1024

    # Calculate size
    try:
        event_size = get_object_size_bytes(event)
    except Exception as e:
        print(f"⚠️ Failed to calculate event size: {e}")
        # Don't fail request if size calculation fails
        return

    if event_size > max_size_bytes:
        error_msg = f"Request too large: {event_size / 1024 / 1024:.2f}MB exceeds limit of {max_size_mb}MB"
        print(f"❌ SECURITY: {error_msg}")
        raise RequestSizeTooLargeError(error_msg)

    print(f"✅ Request size: {event_size / 1024:.2f}KB (limit: {max_size_mb}MB)")


def validate_json_field(event, field_name, max_count=None, max_item_size_kb=None):
    """
    Validate array/list field size and count

    Args:
        event (dict): Lambda event object
        field_name (str): Name of field to validate
        max_count (int, optional): Maximum number of items in array
        max_item_size_kb (int, optional): Maximum size of each item in KB

    Raises:
        RequestSizeTooLargeError: If field exceeds limits

    Example:
        validate_json_field(event, 'scenes', max_count=100, max_item_size_kb=50)
    """
    if field_name not in event:
        return  # Field doesn't exist, skip validation

    field_value = event[field_name]

    # Validate array count
    if max_count and isinstance(field_value, (list, tuple)):
        if len(field_value) > max_count:
            error_msg = f"Field '{field_name}' has {len(field_value)} items, exceeds limit of {max_count}"
            print(f"❌ SECURITY: {error_msg}")
            raise RequestSizeTooLargeError(error_msg)
        print(f"✅ Field '{field_name}' count: {len(field_value)} (limit: {max_count})")

    # Validate item sizes
    if max_item_size_kb and isinstance(field_value, (list, tuple)):
        max_item_bytes = max_item_size_kb * 1024
        for i, item in enumerate(field_value):
            try:
                item_size = get_object_size_bytes(item)
                if item_size > max_item_bytes:
                    error_msg = f"Field '{field_name}[{i}]' size {item_size / 1024:.2f}KB exceeds limit of {max_item_size_kb}KB"
                    print(f"❌ SECURITY: {error_msg}")
                    raise RequestSizeTooLargeError(error_msg)
            except Exception as e:
                print(f"⚠️ Failed to validate item {i} size: {e}")


def validate_string_field(event, field_name, max_length=None):
    """
    Validate string field length

    Args:
        event (dict): Lambda event object
        field_name (str): Name of field to validate
        max_length (int, optional): Maximum string length in characters

    Raises:
        RequestSizeTooLargeError: If string exceeds limit

    Example:
        validate_string_field(event, 'story_title', max_length=500)
    """
    if field_name not in event:
        return  # Field doesn't exist, skip validation

    field_value = event[field_name]

    if not isinstance(field_value, str):
        return  # Not a string, skip validation

    if max_length and len(field_value) > max_length:
        error_msg = f"Field '{field_name}' length {len(field_value)} exceeds limit of {max_length} characters"
        print(f"❌ SECURITY: {error_msg}")
        raise RequestSizeTooLargeError(error_msg)

    print(f"✅ Field '{field_name}' length: {len(field_value)} (limit: {max_length})")


def validate_nested_depth(obj, max_depth=10, current_depth=0):
    """
    Validate JSON nesting depth to prevent stack overflow

    Args:
        obj: Object to validate
        max_depth (int): Maximum nesting depth
        current_depth (int): Current depth (internal use)

    Raises:
        RequestSizeTooLargeError: If nesting exceeds limit

    Example:
        validate_nested_depth(event, max_depth=10)
    """
    if current_depth > max_depth:
        error_msg = f"JSON nesting depth {current_depth} exceeds limit of {max_depth}"
        print(f"❌ SECURITY: {error_msg}")
        raise RequestSizeTooLargeError(error_msg)

    if isinstance(obj, dict):
        for value in obj.values():
            validate_nested_depth(value, max_depth, current_depth + 1)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            validate_nested_depth(item, max_depth, current_depth + 1)


# Preset validation profiles for common Lambda patterns

def validate_api_request(event, max_size_mb=1):
    """
    Validate typical API Gateway/Function URL request

    Args:
        event (dict): Lambda event object
        max_size_mb (int): Maximum request size in MB
    """
    validate_request_size(event, max_size_mb=max_size_mb)
    validate_nested_depth(event, max_depth=10)


def validate_content_generation_request(event, max_size_mb=10, max_scenes=100):
    """
    Validate content generation request (narrative, audio, etc.)

    Args:
        event (dict): Lambda event object
        max_size_mb (int): Maximum request size in MB
        max_scenes (int): Maximum number of scenes
    """
    validate_request_size(event, max_size_mb=max_size_mb)
    validate_nested_depth(event, max_depth=15)
    validate_json_field(event, 'scenes', max_count=max_scenes, max_item_size_kb=50)
    validate_string_field(event, 'story_title', max_length=500)
    validate_string_field(event, 'selected_topic', max_length=500)


def validate_data_save_request(event, max_size_mb=20):
    """
    Validate data save request (large payloads)

    Args:
        event (dict): Lambda event object
        max_size_mb (int): Maximum request size in MB
    """
    validate_request_size(event, max_size_mb=max_size_mb)
    validate_nested_depth(event, max_depth=20)
