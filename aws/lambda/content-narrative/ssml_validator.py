"""
SSML Validator for AWS Polly
Validates and fixes SSML according to AWS Polly specifications

AWS Polly SSML Support:
https://docs.aws.amazon.com/polly/latest/dg/supportedtags.html

Supported Tags:
- speak: Root element (required)
- break: Pause in speech
- emphasis: Emphasis level
- lang: Language switch
- mark: Custom tag for tracking
- p: Paragraph
- phoneme: Phonetic pronunciation
- prosody: Volume, rate, pitch control
- s: Sentence
- say-as: Interpret text in specific way
- sub: Substitute text
- w: Word with optional part-of-speech
"""

import re
import html
from typing import Dict, List, Tuple


class SSMLValidationError(Exception):
    """Custom exception for SSML validation errors"""
    pass


class SSMLValidator:
    """Validates and fixes SSML for AWS Polly"""

    # AWS Polly supported SSML tags
    SUPPORTED_TAGS = {
        'speak', 'break', 'emphasis', 'lang', 'mark', 'p',
        'phoneme', 'prosody', 's', 'say-as', 'sub', 'w'
    }

    # Prosody valid attribute values
    PROSODY_RATE_VALUES = {
        'x-slow', 'slow', 'medium', 'fast', 'x-fast',
        # Also supports percentage: "50%", "100%", "150%", etc.
    }

    PROSODY_PITCH_VALUES = {
        'x-low', 'low', 'medium', 'high', 'x-high',
        # Also supports: "+n%" or "-n%", e.g., "+5%", "-10%"
    }

    PROSODY_VOLUME_VALUES = {
        'silent', 'x-soft', 'soft', 'medium', 'loud', 'x-loud',
        # Also supports: "+ndB" or "-ndB", e.g., "+6dB", "-3dB"
    }

    # Break valid attribute values
    BREAK_STRENGTH_VALUES = {
        'none', 'x-weak', 'weak', 'medium', 'strong', 'x-strong'
    }

    # Emphasis valid attribute values
    EMPHASIS_LEVEL_VALUES = {
        'strong', 'moderate', 'reduced'
    }

    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator

        Args:
            strict_mode: If True, raise errors instead of auto-fixing
        """
        self.strict_mode = strict_mode
        self.warnings = []
        self.errors = []

    def validate(self, ssml_text: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate SSML text

        Returns:
            (is_valid, warnings, errors)
        """
        self.warnings = []
        self.errors = []

        try:
            # 1. Check if text is wrapped in <speak> tags
            if not ssml_text.strip().startswith('<speak'):
                self.errors.append("SSML must start with <speak> tag")

            if not ssml_text.strip().endswith('</speak>'):
                self.errors.append("SSML must end with </speak> tag")

            # 2. Check for single quotes in attributes (AWS Polly requires double quotes)
            if self._has_single_quote_attributes(ssml_text):
                self.warnings.append("Attributes should use double quotes, not single quotes")

            # 3. Check for unsupported tags
            unsupported = self._find_unsupported_tags(ssml_text)
            if unsupported:
                self.errors.append(f"Unsupported tags found: {', '.join(unsupported)}")

            # 4. Check for unclosed tags
            unclosed = self._find_unclosed_tags(ssml_text)
            if unclosed:
                self.errors.append(f"Unclosed tags found: {', '.join(unclosed)}")

            # 5. Check for invalid attribute values
            invalid_attrs = self._validate_attributes(ssml_text)
            if invalid_attrs:
                self.warnings.extend(invalid_attrs)

            # 6. Check for special characters that need escaping
            if self._has_unescaped_special_chars(ssml_text):
                self.warnings.append("Text contains unescaped special characters (&, <, >, ', \")")

            # 7. Check for nested <speak> tags (not allowed)
            if ssml_text.count('<speak') > 1:
                self.errors.append("Nested <speak> tags are not allowed")

            is_valid = len(self.errors) == 0
            return is_valid, self.warnings, self.errors

        except Exception as e:
            self.errors.append(f"Validation exception: {str(e)}")
            return False, self.warnings, self.errors

    def fix(self, ssml_text: str) -> str:
        """
        Auto-fix common SSML issues

        Returns:
            Fixed SSML text
        """
        original = ssml_text

        # 1. Ensure <speak> wrapper
        ssml_text = self._ensure_speak_wrapper(ssml_text)

        # 2. Fix single quotes to double quotes in attributes
        ssml_text = self._fix_attribute_quotes(ssml_text)

        # 3. Escape special characters in text content
        ssml_text = self._escape_special_chars(ssml_text)

        # 4. Remove unsupported tags (replace with their content)
        ssml_text = self._remove_unsupported_tags(ssml_text)

        # 5. Fix common attribute value issues
        ssml_text = self._fix_attribute_values(ssml_text)

        if original != ssml_text:
            self.warnings.append("SSML was auto-fixed")

        return ssml_text

    def validate_and_fix(self, ssml_text: str) -> Tuple[str, bool, List[str], List[str]]:
        """
        Validate and auto-fix SSML

        Returns:
            (fixed_ssml, is_valid, warnings, errors)
        """
        # First fix
        fixed_ssml = self.fix(ssml_text)

        # Then validate
        is_valid, warnings, errors = self.validate(fixed_ssml)

        return fixed_ssml, is_valid, warnings, errors

    # Helper methods

    def _ensure_speak_wrapper(self, text: str) -> str:
        """Ensure text is wrapped in <speak> tags"""
        text = text.strip()
        if not text.startswith('<speak'):
            text = f'<speak>{text}</speak>'
        return text

    def _has_single_quote_attributes(self, text: str) -> bool:
        """Check if attributes use single quotes"""
        # Pattern: attribute='value'
        pattern = r'\w+\s*=\s*\'[^\']*\''
        return bool(re.search(pattern, text))

    def _fix_attribute_quotes(self, text: str) -> str:
        """Replace single quotes with double quotes in attributes"""
        # Fix common attributes
        text = text.replace("rate='", 'rate="').replace("'", '"', 1)
        text = text.replace("pitch='", 'pitch="').replace("'", '"', 1)
        text = text.replace("volume='", 'volume="').replace("'", '"', 1)
        text = text.replace("time='", 'time="').replace("'", '"', 1)
        text = text.replace("strength='", 'strength="').replace("'", '"', 1)
        text = text.replace("level='", 'level="').replace("'", '"', 1)

        # More robust approach: find all attribute='value' and replace
        def replace_quotes(match):
            return match.group(0).replace("'", '"')

        text = re.sub(r'\w+\s*=\s*\'[^\']*\'', replace_quotes, text)

        return text

    def _find_unsupported_tags(self, text: str) -> List[str]:
        """Find tags that are not supported by AWS Polly"""
        # Extract all tags
        tag_pattern = r'</?(\w+)[\s>]'
        all_tags = set(re.findall(tag_pattern, text))

        # Find unsupported ones
        unsupported = all_tags - self.SUPPORTED_TAGS
        return list(unsupported)

    def _remove_unsupported_tags(self, text: str) -> str:
        """Remove unsupported tags but keep their content"""
        unsupported = self._find_unsupported_tags(text)

        for tag in unsupported:
            # Remove opening and closing tags but keep content
            text = re.sub(f'<{tag}[^>]*>', '', text)
            text = re.sub(f'</{tag}>', '', text)

        return text

    def _find_unclosed_tags(self, text: str) -> List[str]:
        """Find tags that are not properly closed"""
        # This is a simplified check
        # For production, use proper XML parser

        # Self-closing tags don't need closing
        self_closing = {'break', 'mark'}

        stack = []
        unclosed = []

        # Find all tags
        tag_pattern = r'<(/?)(\w+)(?:\s[^>]*)?(/?)'
        for match in re.finditer(tag_pattern, text):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2)
            is_self_closing = match.group(3) == '/' or tag_name in self_closing

            if is_closing:
                # Closing tag
                if stack and stack[-1] == tag_name:
                    stack.pop()
                else:
                    unclosed.append(tag_name)
            elif not is_self_closing:
                # Opening tag
                stack.append(tag_name)

        # Any remaining in stack are unclosed
        unclosed.extend(stack)

        return list(set(unclosed))

    def _validate_attributes(self, text: str) -> List[str]:
        """Validate attribute values"""
        warnings = []

        # Check prosody rate
        rate_pattern = r'<prosody[^>]*rate=["\']([^"\']+)["\']'
        for match in re.finditer(rate_pattern, text):
            rate = match.group(1)
            if not self._is_valid_rate(rate):
                warnings.append(f"Invalid prosody rate value: {rate}")

        # Check prosody pitch
        pitch_pattern = r'<prosody[^>]*pitch=["\']([^"\']+)["\']'
        for match in re.finditer(pitch_pattern, text):
            pitch = match.group(1)
            if not self._is_valid_pitch(pitch):
                warnings.append(f"Invalid prosody pitch value: {pitch}")

        # Check prosody volume
        volume_pattern = r'<prosody[^>]*volume=["\']([^"\']+)["\']'
        for match in re.finditer(volume_pattern, text):
            volume = match.group(1)
            if not self._is_valid_volume(volume):
                warnings.append(f"Invalid prosody volume value: {volume}")

        # Check break strength
        strength_pattern = r'<break[^>]*strength=["\']([^"\']+)["\']'
        for match in re.finditer(strength_pattern, text):
            strength = match.group(1)
            if strength not in self.BREAK_STRENGTH_VALUES:
                warnings.append(f"Invalid break strength value: {strength}")

        # Check break time format
        time_pattern = r'<break[^>]*time=["\']([^"\']+)["\']'
        for match in re.finditer(time_pattern, text):
            time_val = match.group(1)
            if not self._is_valid_time(time_val):
                warnings.append(f"Invalid break time value: {time_val}")

        return warnings

    def _is_valid_rate(self, rate: str) -> bool:
        """Check if rate value is valid"""
        if rate in self.PROSODY_RATE_VALUES:
            return True
        # Check percentage format
        if re.match(r'^\d+%$', rate):
            return True
        return False

    def _is_valid_pitch(self, pitch: str) -> bool:
        """Check if pitch value is valid"""
        if pitch in self.PROSODY_PITCH_VALUES:
            return True
        # Check +/-n% format
        if re.match(r'^[+-]\d+%$', pitch):
            return True
        return False

    def _is_valid_volume(self, volume: str) -> bool:
        """Check if volume value is valid"""
        if volume in self.PROSODY_VOLUME_VALUES:
            return True
        # Check +/-ndB format
        if re.match(r'^[+-]\d+dB$', volume):
            return True
        return False

    def _is_valid_time(self, time_val: str) -> bool:
        """Check if time value is valid (e.g., '500ms', '1s')"""
        return bool(re.match(r'^\d+(ms|s)$', time_val))

    def _fix_attribute_values(self, text: str) -> str:
        """Fix common attribute value issues"""
        # Example: fix 'fast' to 'medium' if needed
        # This is conservative - we don't change values unless clearly wrong

        # Fix time values without units (assume milliseconds)
        def fix_time(match):
            time_val = match.group(1)
            if time_val.isdigit():
                return f'time="{time_val}ms"'
            return match.group(0)

        text = re.sub(r'time=["\'](\d+)["\']', fix_time, text)

        return text

    def _has_unescaped_special_chars(self, text: str) -> bool:
        """Check for unescaped special characters in text content"""
        # Remove all tags first
        text_only = re.sub(r'<[^>]+>', '', text)

        # Check for &, <, > that are not part of entities
        if '&' in text_only and not re.search(r'&\w+;', text_only):
            return True
        if '<' in text_only or '>' in text_only:
            return True

        return False

    def _escape_special_chars(self, text: str) -> str:
        """Escape special characters in text content (not in tags)"""
        # This is tricky - we need to escape text but not tag content
        # For now, we'll do basic escaping

        # Split by tags
        parts = re.split(r'(<[^>]+>)', text)

        escaped_parts = []
        for part in parts:
            if part.startswith('<'):
                # This is a tag, don't escape
                escaped_parts.append(part)
            else:
                # This is text content, escape if needed
                # Only escape if not already escaped
                if '&' in part and not re.search(r'&\w+;', part):
                    part = part.replace('&', '&amp;')
                if '<' in part:
                    part = part.replace('<', '&lt;')
                if '>' in part:
                    part = part.replace('>', '&gt;')
                escaped_parts.append(part)

        return ''.join(escaped_parts)


def validate_ssml(ssml_text: str, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate SSML

    Args:
        ssml_text: SSML text to validate
        strict: If True, raise errors instead of auto-fixing

    Returns:
        (is_valid, warnings, errors)
    """
    validator = SSMLValidator(strict_mode=strict)
    return validator.validate(ssml_text)


def fix_ssml(ssml_text: str) -> str:
    """
    Convenience function to auto-fix SSML

    Args:
        ssml_text: SSML text to fix

    Returns:
        Fixed SSML text
    """
    validator = SSMLValidator()
    return validator.fix(ssml_text)


def validate_and_fix_ssml(ssml_text: str) -> Tuple[str, bool, List[str], List[str]]:
    """
    Convenience function to validate and auto-fix SSML

    Args:
        ssml_text: SSML text to validate and fix

    Returns:
        (fixed_ssml, is_valid, warnings, errors)
    """
    validator = SSMLValidator()
    return validator.validate_and_fix(ssml_text)


# Example usage
if __name__ == '__main__':
    # Test SSML
    test_ssml = """<speak>
        <prosody rate='fast' pitch='+5%'>
            Hello world! This is a test.
        </prosody>
        <break time='500ms'/>
        <emphasis level='strong'>Important message!</emphasis>
    </speak>"""

    print("Original SSML:")
    print(test_ssml)
    print("\n" + "="*50 + "\n")

    # Validate and fix
    fixed, is_valid, warnings, errors = validate_and_fix_ssml(test_ssml)

    print("Fixed SSML:")
    print(fixed)
    print("\n" + "="*50 + "\n")

    print(f"Is valid: {is_valid}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
