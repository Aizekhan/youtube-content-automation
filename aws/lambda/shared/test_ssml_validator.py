"""
Tests for SSML Validator
Run with: python test_ssml_validator.py
"""

import sys
import os

# Add shared directory to path
sys.path.insert(0, os.path.dirname(__file__))
from ssml_validator import SSMLValidator, validate_ssml, fix_ssml, validate_and_fix_ssml


def test_valid_ssml():
    """Test that valid SSML passes validation"""
    print("\n=== Test 1: Valid SSML ===")

    valid_ssml = """<speak>
        <prosody rate="fast" pitch="+5%">
            Hello world! This is a test.
        </prosody>
        <break time="500ms"/>
        <emphasis level="strong">Important message!</emphasis>
    </speak>"""

    is_valid, warnings, errors = validate_ssml(valid_ssml)

    print(f"SSML: {valid_ssml[:50]}...")
    print(f"Valid: {is_valid}")
    print(f"Warnings: {warnings}")
    print(f"Errors: {errors}")

    assert is_valid, "Valid SSML should pass validation"
    print("PASSED")


def test_missing_speak_wrapper():
    """Test SSML without <speak> wrapper"""
    print("\n=== Test 2: Missing <speak> wrapper ===")

    invalid_ssml = "Hello world! This is a test."

    is_valid, warnings, errors = validate_ssml(invalid_ssml)

    print(f"SSML: {invalid_ssml}")
    print(f"Valid: {is_valid}")
    print(f"Warnings: {warnings}")
    print(f"Errors: {errors}")

    assert not is_valid, "SSML without <speak> wrapper should be invalid"
    assert any("speak" in err.lower() for err in errors), "Should have error about <speak> tag"
    print("PASSED")


def test_single_quote_attributes():
    """Test SSML with single quotes in attributes"""
    print("\n=== Test 3: Single quotes in attributes ===")

    ssml_with_single_quotes = """<speak>
        <prosody rate='fast' pitch='+5%'>
            Hello world!
        </prosody>
    </speak>"""

    # Validate (should have warnings)
    is_valid, warnings, errors = validate_ssml(ssml_with_single_quotes)

    print(f"Original SSML: {ssml_with_single_quotes[:50]}...")
    print(f"Warnings: {warnings}")

    assert len(warnings) > 0, "Should have warning about single quotes"

    # Fix
    fixed = fix_ssml(ssml_with_single_quotes)
    print(f"Fixed SSML: {fixed[:50]}...")

    assert 'rate="fast"' in fixed, "Should have double quotes after fix"
    assert "rate='" not in fixed, "Should not have single quotes after fix"
    print("PASSED")


def test_unsupported_tags():
    """Test SSML with unsupported tags"""
    print("\n=== Test 4: Unsupported tags ===")

    ssml_with_unsupported = """<speak>
        <div>This is a div tag</div>
        <span class="test">This is a span tag</span>
        Hello world!
    </speak>"""

    is_valid, warnings, errors = validate_ssml(ssml_with_unsupported)

    print(f"Original SSML: {ssml_with_unsupported[:50]}...")
    print(f"Valid: {is_valid}")
    print(f"Errors: {errors}")

    assert not is_valid, "SSML with unsupported tags should be invalid"
    assert any("unsupported" in err.lower() for err in errors), "Should have error about unsupported tags"

    # Fix (should remove unsupported tags)
    fixed = fix_ssml(ssml_with_unsupported)
    print(f"Fixed SSML: {fixed}")

    assert "<div>" not in fixed, "Should not have <div> after fix"
    assert "<span" not in fixed, "Should not have <span> after fix"
    assert "This is a div tag" in fixed, "Should keep text content"
    print("PASSED")


def test_invalid_prosody_rate():
    """Test SSML with invalid prosody rate value"""
    print("\n=== Test 5: Invalid prosody rate ===")

    ssml_invalid_rate = """<speak>
        <prosody rate="super-fast">
            Hello world!
        </prosody>
    </speak>"""

    is_valid, warnings, errors = validate_ssml(ssml_invalid_rate)

    print(f"SSML: {ssml_invalid_rate[:50]}...")
    print(f"Warnings: {warnings}")

    assert len(warnings) > 0, "Should have warning about invalid rate"
    assert any("rate" in warn.lower() for warn in warnings), "Warning should mention 'rate'"
    print("PASSED")


def test_invalid_break_time():
    """Test SSML with break time without units"""
    print("\n=== Test 6: Break time without units ===")

    ssml_no_units = """<speak>
        Hello world!
        <break time="500"/>
        Goodbye!
    </speak>"""

    # Fix should add 'ms' suffix
    fixed = fix_ssml(ssml_no_units)

    print(f"Original: {ssml_no_units}")
    print(f"Fixed: {fixed}")

    assert 'time="500ms"' in fixed, "Should add 'ms' suffix to time value"
    print("PASSED")


def test_nested_speak_tags():
    """Test SSML with nested <speak> tags (not allowed)"""
    print("\n=== Test 7: Nested <speak> tags ===")

    nested_speak = """<speak>
        Hello!
        <speak>
            Nested speak tag
        </speak>
    </speak>"""

    is_valid, warnings, errors = validate_ssml(nested_speak)

    print(f"SSML: {nested_speak[:50]}...")
    print(f"Valid: {is_valid}")
    print(f"Errors: {errors}")

    assert not is_valid, "Nested <speak> tags should be invalid"
    assert any("nested" in err.lower() for err in errors), "Should have error about nested <speak>"
    print("PASSED")


def test_valid_percentage_values():
    """Test SSML with valid percentage values for rate and pitch"""
    print("\n=== Test 8: Valid percentage values ===")

    valid_percentages = """<speak>
        <prosody rate="150%" pitch="-10%">
            Hello world!
        </prosody>
    </speak>"""

    is_valid, warnings, errors = validate_ssml(valid_percentages)

    print(f"SSML: {valid_percentages[:50]}...")
    print(f"Valid: {is_valid}")
    print(f"Warnings: {warnings}")
    print(f"Errors: {errors}")

    assert is_valid, "Valid percentage values should pass"
    print("PASSED")


def test_valid_time_formats():
    """Test SSML with valid time formats"""
    print("\n=== Test 9: Valid time formats ===")

    valid_times = """<speak>
        Hello!
        <break time="500ms"/>
        World!
        <break time="1s"/>
        Goodbye!
    </speak>"""

    is_valid, warnings, errors = validate_ssml(valid_times)

    print(f"SSML: {valid_times[:50]}...")
    print(f"Valid: {is_valid}")
    print(f"Warnings: {warnings}")

    # Should have no warnings about time format
    time_warnings = [w for w in warnings if "time" in w.lower()]
    assert len(time_warnings) == 0, "Should not have warnings about valid time formats"
    print("PASSED")


def test_emphasis_levels():
    """Test SSML with all valid emphasis levels"""
    print("\n=== Test 10: Valid emphasis levels ===")

    valid_emphasis = """<speak>
        <emphasis level="strong">Strong emphasis</emphasis>
        <emphasis level="moderate">Moderate emphasis</emphasis>
        <emphasis level="reduced">Reduced emphasis</emphasis>
    </speak>"""

    is_valid, warnings, errors = validate_ssml(valid_emphasis)

    print(f"SSML: {valid_emphasis[:50]}...")
    print(f"Valid: {is_valid}")
    print(f"Errors: {errors}")

    assert is_valid or len(errors) == 0, "Valid emphasis levels should pass"
    print("PASSED")


def test_complex_nested_ssml():
    """Test complex nested SSML structure"""
    print("\n=== Test 11: Complex nested SSML ===")

    complex_ssml = """<speak>
        <p>
            <s>
                <prosody rate="fast" pitch="+5%">
                    <emphasis level="strong">
                        Important announcement!
                    </emphasis>
                </prosody>
            </s>
            <break time="500ms"/>
            <s>
                Thank you for listening.
            </s>
        </p>
    </speak>"""

    is_valid, warnings, errors = validate_ssml(complex_ssml)

    print(f"SSML: {complex_ssml[:50]}...")
    print(f"Valid: {is_valid}")
    print(f"Warnings: {warnings}")
    print(f"Errors: {errors}")

    assert is_valid or len(errors) == 0, "Complex nested structure should pass"
    print("PASSED")


def test_auto_fix_all_issues():
    """Test auto-fix with multiple issues"""
    print("\n=== Test 12: Auto-fix multiple issues ===")

    messy_ssml = """<prosody rate='super-fast' pitch='+5%'>
        Hello world!
        <div>Unsupported tag</div>
        <break time='500'/>
    </prosody>"""

    print(f"Original (messy): {messy_ssml[:50]}...")

    # Fix
    fixed = fix_ssml(messy_ssml)

    print(f"Fixed: {fixed[:100]}...")

    # Check fixes
    assert fixed.startswith('<speak'), "Should add <speak> wrapper"
    assert 'rate="super-fast"' in fixed, "Should fix single quotes"
    assert '<div>' not in fixed, "Should remove unsupported tags"
    assert 'time="500ms"' in fixed, "Should add time units"

    # Validate fixed version
    is_valid, warnings, errors = validate_ssml(fixed)
    print(f"After fix - Valid: {is_valid}, Warnings: {len(warnings)}, Errors: {len(errors)}")

    assert is_valid or len(errors) == 0, "Fixed SSML should have no errors"
    print("PASSED")


def test_real_world_example():
    """Test with real-world SSML from content generation"""
    print("\n=== Test 13: Real-world example ===")

    real_world_ssml = """<speak>
        <prosody rate="medium">
            <p>
                In the year 2045, humanity discovered something extraordinary.
                <break time="800ms"/>
                A signal from deep space, not random noise, but a message.
            </p>
            <p>
                <emphasis level="strong">
                    The question was not if we were alone anymore.
                </emphasis>
                <break time="500ms"/>
                The question was: are we ready?
            </p>
        </prosody>
    </speak>"""

    # Validate and fix
    fixed, is_valid, warnings, errors = validate_and_fix_ssml(real_world_ssml)

    print(f"Original: {real_world_ssml[:100]}...")
    print(f"Valid: {is_valid}")
    print(f"Warnings: {warnings}")
    print(f"Errors: {errors}")

    if fixed != real_world_ssml:
        print(f"Fixed: {fixed[:100]}...")

    assert is_valid or len(errors) == 0, "Real-world SSML should pass or be fixable"
    print("PASSED")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running SSML Validator Tests")
    print("=" * 60)

    tests = [
        test_valid_ssml,
        test_missing_speak_wrapper,
        test_single_quote_attributes,
        test_unsupported_tags,
        test_invalid_prosody_rate,
        test_invalid_break_time,
        test_nested_speak_tags,
        test_valid_percentage_values,
        test_valid_time_formats,
        test_emphasis_levels,
        test_complex_nested_ssml,
        test_auto_fix_all_issues,
        test_real_world_example,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed out of {len(tests)} total")
    print("=" * 60)

    if failed == 0:
        print("All tests passed!")
    else:
        print(f"{failed} test(s) failed")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
