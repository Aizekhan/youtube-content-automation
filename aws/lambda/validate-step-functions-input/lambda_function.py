"""
Step Functions Input Validation Lambda - Week 3.1 + Week 5 Update
Validates input before starting expensive workflow operations

Purpose:
- Fail fast on invalid inputs (saves time & money)
- Consistent validation across all Step Functions
- Clear error messages for debugging

Usage:
Add as first state in Step Functions workflow

IMPORTANT: This validator runs BEFORE channels are fetched.
It validates the initial trigger, not per-channel content generation.
"""

import json
from datetime import datetime


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


def validate_required_field(event, field_name, field_type=str):
    """
    Validate that required field exists and has correct type

    Args:
        event: Lambda event object
        field_name: Name of required field
        field_type: Expected Python type (default: str)

    Raises:
        ValidationError: If field missing or wrong type
    """
    if field_name not in event:
        raise ValidationError(f"Missing required field: '{field_name}'")

    value = event[field_name]

    if not isinstance(value, field_type):
        raise ValidationError(
            f"Field '{field_name}' must be {field_type.__name__}, "
            f"got {type(value).__name__}"
        )

    # Additional validation for strings
    if field_type == str and not value.strip():
        raise ValidationError(f"Field '{field_name}' cannot be empty")

    return value


def validate_user_id(event):
    """Validate user_id format"""
    user_id = validate_required_field(event, 'user_id', str)

    # user_id should be from Cognito (format: UUID or similar)
    if len(user_id) < 10:
        raise ValidationError(f"Invalid user_id format: too short ({len(user_id)} chars)")

    return user_id


def validate_content_generation_input(event):
    """
    Validate input for content generation workflow (Multi-tenant)

    This validator runs at the START of the workflow, BEFORE channels are fetched.
    It validates the initial trigger input, not the per-channel content generation.

    Required fields:
    - user_id: User identifier (string)

    Optional fields:
    - trigger_type: Type of trigger (manual, scheduled, etc.)
    - trigger_time: Timestamp of trigger
    - force: Force generation even if recently generated (boolean)
    - requested_channels: List of specific channel IDs or null for all (list or null)

    Note: channel_id and selected_topic are NOT validated here because they
    don't exist yet at the initial trigger stage. They are populated later
    when the workflow fetches channels and generates content for each channel.
    """
    errors = []

    # Validate required fields
    try:
        user_id = validate_user_id(event)
        print(f"[OK] user_id valid: {user_id}")
    except ValidationError as e:
        errors.append(str(e))

    # Validate optional fields if present
    trigger_type = event.get('trigger_type')
    if trigger_type:
        print(f"[OK] trigger_type: {trigger_type}")

    requested_channels = event.get('requested_channels')
    if requested_channels is not None:
        if isinstance(requested_channels, list):
            print(f"[OK] requested_channels: {len(requested_channels)} channels")
        else:
            errors.append("requested_channels must be a list or null")
    else:
        print(f"[OK] requested_channels: null (will fetch all active channels)")

    force = event.get('force', False)
    print(f"[OK] force: {force}")

    if errors:
        error_message = "Input validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValidationError(error_message)

    print(f"[SUCCESS] All validation passed for user {user_id}")
    return event


def lambda_handler(event, context):
    """
    Main Lambda handler - validates Step Functions input

    Returns:
        Original event if valid

    Raises:
        ValidationError: If input is invalid (will fail Step Functions)
    """
    print("=" * 80)
    print("Step Functions Input Validation - Week 5 Fixed")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)[:500]}")

    try:
        # Validate input
        validated_event = validate_content_generation_input(event)

        # Add validation metadata
        validated_event['validation'] = {
            'validated_at': datetime.utcnow().isoformat() + 'Z',
            'validator_version': '2.0',
            'status': 'passed'
        }

        print(f"[SUCCESS] Validation PASSED")
        return validated_event

    except ValidationError as e:
        error_message = str(e)
        print(f"[ERROR] Validation FAILED: {error_message}")

        # Return error in Step Functions format
        return {
            'validation': {
                'status': 'failed',
                'error': error_message,
                'validated_at': datetime.utcnow().isoformat() + 'Z'
            },
            'error': error_message,
            'original_event': event
        }

    except Exception as e:
        # Unexpected error
        error_message = f"Validation error: {str(e)}"
        print(f"[ERROR] Unexpected error: {error_message}")
        import traceback
        traceback.print_exc()

        return {
            'validation': {
                'status': 'error',
                'error': error_message,
                'validated_at': datetime.utcnow().isoformat() + 'Z'
            },
            'error': error_message,
            'original_event': event
        }
