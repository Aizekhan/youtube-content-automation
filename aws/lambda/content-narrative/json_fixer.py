"""
Advanced JSON Fixer for LLM Responses
Handles common JSON errors from OpenAI/Claude responses
"""
import re
import json


def fix_unterminated_string(json_str, error_pos):
    """Fix unterminated string by finding where it should end"""
    # Find the start of the unterminated string
    start = json_str.rfind('"', 0, error_pos)
    if start == -1:
        return json_str

    # Check if previous char is escape
    if start > 0 and json_str[start - 1] == '\\':
        start = json_str.rfind('"', 0, start - 1)

    # Find next quote or end of reasonable string (next structural char)
    end = error_pos
    while end < len(json_str):
        if json_str[end] in ['"', '\n', ',', '}', ']']:
            if json_str[end] == '"':
                # Found quote, but check if it's escaped
                num_escapes = 0
                check_pos = end - 1
                while check_pos >= 0 and json_str[check_pos] == '\\':
                    num_escapes += 1
                    check_pos -= 1

                # If odd number of escapes, quote is escaped, keep looking
                if num_escapes % 2 == 1:
                    end += 1
                    continue
                break
            else:
                # Hit structural char without closing quote, add quote before it
                return json_str[:end] + '"' + json_str[end:]
        end += 1

    return json_str


def fix_truncated_json(json_str):
    """
    Fix truncated JSON by closing all open structures
    """
    # Count unclosed structures
    open_braces = json_str.count('{') - json_str.count('}')
    open_brackets = json_str.count('[') - json_str.count(']')

    # Check if inside a string (odd number of quotes after last structural char)
    last_struct = max(
        json_str.rfind('{'),
        json_str.rfind('}'),
        json_str.rfind('['),
        json_str.rfind(']'),
        json_str.rfind(',')
    )

    after_struct = json_str[last_struct + 1:] if last_struct >= 0 else json_str
    quotes_after = after_struct.count('"')

    # If odd quotes, we're inside a string - close it
    if quotes_after % 2 == 1:
        # Find last quote
        last_quote = json_str.rfind('"')
        # Check if it's escaped
        if last_quote > 0 and json_str[last_quote - 1] != '\\':
            json_str += '"'

    # Remove any trailing incomplete value
    json_str = re.sub(r',\s*$', '', json_str)

    # Close all open brackets and braces
    json_str += ']' * open_brackets
    json_str += '}' * open_braces

    return json_str


def fix_unescaped_quotes(json_str):
    """
    Fix unescaped quotes inside strings
    This is tricky - we need to identify quotes that should be escaped
    """
    # Pattern: Find strings that contain unescaped quotes
    # Example: "He said "hello"" should be "He said \"hello\""

    result = []
    in_string = False
    escape_next = False
    i = 0

    while i < len(json_str):
        char = json_str[i]

        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"':
            if in_string:
                # Check if this looks like end of string (followed by : , } ] or whitespace)
                next_chars = json_str[i+1:i+10].lstrip()
                if next_chars and next_chars[0] in ':,}]':
                    # This is end of string
                    in_string = False
                    result.append(char)
                else:
                    # This might be an unescaped quote inside string
                    # Escape it
                    result.append('\\')
                    result.append(char)
            else:
                # Starting a string
                in_string = True
                result.append(char)
        else:
            result.append(char)

        i += 1

    return ''.join(result)


def fix_trailing_commas(json_str):
    """Remove trailing commas before ] and }"""
    return re.sub(r',\s*([\]}])', r'\1', json_str)


def fix_newlines_in_strings(json_str):
    """Replace actual newlines in strings with \n"""
    # This is complex, skip for now as SSML can have legitimate newlines
    return json_str


def fix_llm_json(json_str, max_attempts=5):
    """
    Try multiple strategies to fix JSON from LLM response

    Args:
        json_str: Raw JSON string from LLM
        max_attempts: Maximum fix attempts

    Returns:
        Parsed JSON object

    Raises:
        json.JSONDecodeError: If all fix attempts fail
    """

    print(f"🔧 Attempting to parse/fix JSON ({len(json_str)} chars)")

    # Attempt 1: Try parsing as-is
    try:
        result = json.loads(json_str)
        print(f"✅ JSON parsed successfully (no fixes needed)")
        return result
    except json.JSONDecodeError as e:
        print(f"❌ Parse error: {str(e)}")
        original_error = e

    # Attempt 2: Fix trailing commas
    try:
        fixed = fix_trailing_commas(json_str)
        result = json.loads(fixed)
        print(f"✅ JSON fixed with trailing comma removal")
        return result
    except json.JSONDecodeError as e:
        print(f"⚠️  Trailing comma fix didn't work: {str(e)}")

    # Attempt 3: Fix truncated JSON
    try:
        fixed = fix_truncated_json(json_str)
        result = json.loads(fixed)
        print(f"✅ JSON fixed by closing truncated structures")
        return result
    except json.JSONDecodeError as e:
        print(f"⚠️  Truncation fix didn't work: {str(e)}")
        truncated_json = fixed  # Save for later attempt

    # Attempt 4: Fix unterminated string at error position
    try:
        error_pos = original_error.pos if hasattr(original_error, 'pos') else len(json_str) // 2
        fixed = fix_unterminated_string(json_str, error_pos)
        result = json.loads(fixed)
        print(f"✅ JSON fixed by terminating string at pos {error_pos}")
        return result
    except json.JSONDecodeError as e:
        print(f"⚠️  String termination fix didn't work: {str(e)}")

    # Attempt 5: Combined fix (trailing commas + truncation)
    try:
        fixed = fix_trailing_commas(truncated_json)
        result = json.loads(fixed)
        print(f"✅ JSON fixed with combined fixes")
        return result
    except json.JSONDecodeError as e:
        print(f"⚠️  Combined fix didn't work: {str(e)}")

    # Attempt 6: Try to extract JSON from markdown code blocks
    if '```json' in json_str or '```' in json_str:
        print(f"🔍 Detected markdown code blocks, extracting...")
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', json_str, re.DOTALL)
        if json_match:
            try:
                extracted = json_match.group(1).strip()
                result = json.loads(extracted)
                print(f"✅ JSON extracted from markdown code block")
                return result
            except json.JSONDecodeError:
                print(f"⚠️  Extracted JSON still invalid")

    # All attempts failed
    print(f"❌ All {max_attempts} fix attempts failed")
    print(f"Original error: {original_error}")
    print(f"JSON preview (first 200 chars): {json_str[:200]}")
    print(f"JSON preview (last 200 chars): {json_str[-200:]}")

    # Show context around error position
    if hasattr(original_error, 'pos'):
        error_pos = original_error.pos
        start = max(0, error_pos - 100)
        end = min(len(json_str), error_pos + 100)
        print(f"\nContext around error (pos {error_pos}):")
        print(f"... {json_str[start:end]} ...")

    raise original_error


def get_partial_json(json_str):
    """
    Extract whatever valid JSON we can from a broken response
    This is a last resort - returns partial data
    """
    try:
        return fix_llm_json(json_str)
    except json.JSONDecodeError:
        # Try to extract just the story_title and partial scenes
        partial = {"story_title": "Incomplete Generation", "scenes": []}

        # Try to extract title
        title_match = re.search(r'"story_title"\s*:\s*"([^"]+)"', json_str)
        if title_match:
            partial["story_title"] = title_match.group(1)

        return partial
