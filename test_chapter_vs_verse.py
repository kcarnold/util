#!/usr/bin/env python3
"""Test that verse extraction correctly distinguishes between entire chapters and single verses.

This test file specifically addresses the bug where "Psalm 48:1" was returning
the entire Psalm 48 instead of just verse 1.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from usfm_processor import parse_verse_reference, extract_verses


@pytest.mark.parametrize("ref,expected", [
    # Entire chapters should have start_verse=None
    ("Psalm 48", [("Psalm", "48", None, None)]),
    ("Matthew 6", [("Matthew", "6", None, None)]),
    # Single verses should have specific start_verse
    ("Psalm 48:1", [("Psalm", "48", "1", None)]),
    ("Matthew 6:9", [("Matthew", "6", "9", None)]),
    # Verse ranges should have start and end verses
    ("Psalm 48:1-3", [("Psalm", "48", "1", "3")]),
    ("Matthew 6:9-13", [("Matthew", "6", "9", "13")]),
])
def test_parsing_distinguishes_chapter_vs_verse(ref, expected):
    """Test that parsing correctly distinguishes chapter vs verse references."""
    assert parse_verse_reference(ref) == expected


@pytest.fixture
def db_path():
    """Get path to test database."""
    path = Path(__file__).parent / 'bible.db'
    if not path.exists():
        pytest.skip("bible.db not found")
    return str(path)


@pytest.mark.parametrize("ref,expected_count", [
    ("Psalm 48:1", 1),
    ("Psalm 48:1-3", 3),
    ("Matthew 1:1", 1),
])
def test_single_verse_or_range_extraction(db_path, ref, expected_count):
    """Test that specific verse requests return exact counts."""
    result = extract_verses(db_path, ref)
    lines = result.split('\n--\n')
    assert len(lines) == expected_count


@pytest.mark.parametrize("ref,min_verses", [
    ("Psalm 48", 2),
    ("Matthew 1", 10),
])
def test_entire_chapter_extraction(db_path, ref, min_verses):
    """Test that entire chapter requests return multiple verses."""
    result = extract_verses(db_path, ref)
    lines = result.split('\n--\n')
    assert len(lines) >= min_verses


def test_verse_one_differs_from_entire_chapter(db_path):
    """Verify that verse 1 is different from the entire chapter."""
    verse_one = extract_verses(db_path, 'Psalm 48:1')
    entire_chapter = extract_verses(db_path, 'Psalm 48')

    # They should not be equal
    assert verse_one != entire_chapter

    # Verse 1 should be shorter than entire chapter
    assert len(verse_one) < len(entire_chapter)

    # Entire chapter should contain verse 1's content
    assert verse_one.split('\n--\n')[0] in entire_chapter
