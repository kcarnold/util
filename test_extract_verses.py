#!/usr/bin/env python3
"""Test basic extract_verses functionality."""

import sys
from pathlib import Path

import pytest

# Add src to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent / "src"))

from usfm_processor import parse_verse_reference, load_book_abbreviations


@pytest.mark.parametrize("ref,expected", [
    ("Psalm 153:2", [("Psalm", "153", "2", None)]),
    ("Matthew 1:18-20", [("Matthew", "1", "18", "20")]),
    ("Jude 3", [("Jude", None, "3", None)]),
    ("1 Samuel 17:4", [("1 Samuel", "17", "4", None)]),
    ("2 Corinthians 5:17-21", [("2 Corinthians", "5", "17", "21")]),
])
def test_parse_verse_reference(ref, expected):
    """Test verse reference parsing."""
    assert parse_verse_reference(ref) == expected


@pytest.mark.parametrize("name,expected_id", [
    ("genesis", "GEN"),
    ("matthew", "MAT"),
    ("psalm", "PSA"),
    ("psalms", "PSA"),
    ("jude", "JUD"),
    ("1 samuel", "1SA"),
    ("2 corinthians", "2CO"),
])
def test_book_abbreviation_mapping(name, expected_id):
    """Test book name to abbreviation mapping."""
    abbreviations = load_book_abbreviations()
    assert abbreviations.get(name) == expected_id


def test_total_books_loaded():
    """Should load all 66+ Bible books."""
    abbreviations = load_book_abbreviations()
    assert len(abbreviations) >= 66
