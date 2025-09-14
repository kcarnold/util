#!/usr/bin/env python3
"""Simple test for the extract_verses functionality."""

import sys
from pathlib import Path

# Add src to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent / "src"))

from usfm_processor import parse_verse_reference, load_book_abbreviations


def test_parse_verse_reference():
    """Test the verse reference parsing function."""
    print("Testing verse reference parsing...")
    
    # Test cases
    test_cases = [
        ("Psalm 153:2", ("Psalm", "153", "2", None)),
        ("Matthew 1:18-20", ("Matthew", "1", "18", "20")),
        ("Jude 3", ("Jude", None, "3", None)),
        ("1 Samuel 17:4", ("1 Samuel", "17", "4", None)),
        ("2 Corinthians 5:17-21", ("2 Corinthians", "5", "17", "21")),
    ]
    
    for ref, expected in test_cases:
        try:
            result = parse_verse_reference(ref)
            if result == expected:
                print(f"✓ {ref} -> {result}")
            else:
                print(f"✗ {ref} -> {result} (expected {expected})")
        except Exception as e:
            print(f"✗ {ref} -> Error: {e}")


def test_load_book_abbreviations():
    """Test loading book abbreviations."""
    print("\nTesting book abbreviations loading...")
    
    try:
        name_to_id = load_book_abbreviations()
        
        # Test a few expected mappings
        test_books = {
            "genesis": "GEN",
            "matthew": "MAT", 
            "psalm": "PSA",
            "psalms": "PSA",
            "jude": "JUD",
            "1 samuel": "1SA",
            "2 corinthians": "2CO",
        }
        
        for name, expected_id in test_books.items():
            actual_id = name_to_id.get(name)
            if actual_id == expected_id:
                print(f"✓ {name} -> {actual_id}")
            else:
                print(f"✗ {name} -> {actual_id} (expected {expected_id})")
                
        print(f"Total books loaded: {len(name_to_id)}")
        
    except Exception as e:
        print(f"✗ Error loading book abbreviations: {e}")


if __name__ == "__main__":
    test_parse_verse_reference()
    test_load_book_abbreviations()
