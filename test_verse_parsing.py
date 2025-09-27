#!/usr/bin/env python3
"""Test script for verse reference parsing functionality."""

from src.usfm_processor import parse_verse_reference

def test_verse_parsing():
    """Test various verse reference formats."""

    test_cases = [
        # Single verse
        ("Psalm 153:2", [("Psalm", "153", "2", None)]),

        # Verse range
        ("Matthew 1:18-20", [("Matthew", "1", "18", "20")]),

        # Single chapter book (verse reference)
        ("Jude 3", [("Jude", None, "3", None)]),

        # Entire chapter for multi-chapter book
        ("Matthew 6", [("Matthew", "6", "1", None)]),

        # Comma-separated references
        ("Exodus 15:1-2,11-15", [
            ("Exodus", "15", "1", "2"),
            ("Exodus", "15", "11", "15")
        ]),

        # Multi-chapter range
        ("Exodus 15:29-16:2", [("Exodus", "15", "29", "16:2")]),

        # Complex comma-separated with different formats
        ("Genesis 1:1,3:5-10", [
            ("Genesis", "1", "1", None),
            ("Genesis", "3", "5", "10")
        ]),
    ]

    for input_ref, expected in test_cases:
        try:
            result = parse_verse_reference(input_ref)
            if result == expected:
                print(f"✅ PASS: {input_ref}")
            else:
                print(f"❌ FAIL: {input_ref}")
                print(f"   Expected: {expected}")
                print(f"   Got:      {result}")
        except Exception as e:
            print(f"❌ ERROR: {input_ref} - {e}")

    print("\nTesting complete!")

if __name__ == "__main__":
    test_verse_parsing()