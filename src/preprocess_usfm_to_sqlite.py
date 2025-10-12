#!/usr/bin/env python3
"""Preprocess USFM files from a ZIP archive into a SQLite database for fast verse lookup."""

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

from usfm_processor import (
    extract_usfm_files_from_zip,
    parse_usfm,
)


def create_verses_table(conn: sqlite3.Connection) -> None:
    """Create the verses table with appropriate indexes."""
    cursor = conn.cursor()

    # Create the verses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verses (
            book_id TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (book_id, chapter, verse)
        )
    """)

    # Create index for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_book_chapter_verse
        ON verses(book_id, chapter, verse)
    """)

    conn.commit()


def extract_all_verses_from_usj(usj: Dict[str, Any], book_id: str) -> list[tuple[str, int, int, str]]:
    """Extract all verses from a USJ structure.

    Returns a list of tuples: (book_id, chapter, verse, text)
    """
    usj_content = usj['content']
    verses = []

    cur_chapter = None
    cur_verse = None
    verse_text = ""

    for item in usj_content:
        if isinstance(item, dict):
            if item['type'] == 'chapter':
                cur_chapter = int(item['number'])
                cur_verse = None
                verse_text = ""
            elif item['type'] == 'verse':
                # Save the previous verse if we have one
                if cur_chapter is not None and cur_verse is not None and verse_text:
                    verses.append((book_id, cur_chapter, cur_verse, verse_text.strip()))

                # Start a new verse
                cur_verse = int(item['number'])
                verse_text = ""
            elif cur_chapter is not None and cur_verse is not None:
                # This is content within a verse
                if isinstance(item, str):
                    verse_text += item
                elif 'text' in item:
                    verse_text += item['text']
        elif isinstance(item, str) and cur_chapter is not None and cur_verse is not None:
            # Plain text content
            verse_text += item

    # Don't forget the last verse
    if cur_chapter is not None and cur_verse is not None and verse_text:
        verses.append((book_id, cur_chapter, cur_verse, verse_text.strip()))

    return verses


def preprocess_usfm_to_sqlite(zipfile_path: str, sqlite_path: str, progress_callback=None) -> None:
    """Preprocess USFM files from a ZIP into a SQLite database.

    Args:
        zipfile_path: Path to the ZIP file containing USFM files
        sqlite_path: Path to the output SQLite database file
        progress_callback: Optional callback function(book_name, current, total) for progress updates
    """
    # Read the zip file
    with open(zipfile_path, 'rb') as f:
        zip_data = f.read()

    # Extract USFM files
    print(f"Extracting USFM files from {zipfile_path}...")
    file_contents = extract_usfm_files_from_zip(zip_data)
    total_books = len(file_contents)
    print(f"Found {total_books} USFM files")

    # Create/open SQLite database
    conn = sqlite3.Connection(sqlite_path)
    create_verses_table(conn)

    cursor = conn.cursor()

    # Process each USFM file
    for idx, (filename, content) in enumerate(file_contents.items(), 1):
        # Extract book ID from the content (the \id line)
        id_line = None
        for line in content[:2000].splitlines():
            line = line.strip()
            if line.startswith('\\id'):
                id_line = line[3:].strip().split()[0] if line[3:].strip() else None
                break

        if not id_line:
            print(f"Warning: Could not find \\id marker in {filename}, skipping")
            continue

        book_id = id_line.upper()

        print(f"[{idx}/{total_books}] Processing {book_id} ({filename})...")

        if progress_callback:
            progress_callback(book_id, idx, total_books)

        # Parse the USFM content
        try:
            parsed = parse_usfm(content)
            if 'errors' in parsed:
                print(f"Warning: USFM parsing errors in {filename}: {parsed['errors']}")
                continue

            usj = parsed['usj']

            # Extract all verses
            verses = extract_all_verses_from_usj(usj, book_id)

            # Insert verses into database
            cursor.executemany(
                "INSERT OR REPLACE INTO verses (book_id, chapter, verse, text) VALUES (?, ?, ?, ?)",
                verses
            )

            print(f"  Inserted {len(verses)} verses")

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

    # Commit and close
    conn.commit()
    conn.close()

    print(f"\nPreprocessing complete! Database saved to {sqlite_path}")


def main() -> None:
    """Main entry point for the preprocessing command-line tool."""
    if len(sys.argv) != 3:
        print("Usage: python preprocess_usfm_to_sqlite.py <zipfile> <output.db>", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  python preprocess_usfm_to_sqlite.py bible.zip bible.db", file=sys.stderr)
        sys.exit(1)

    zipfile_path = sys.argv[1]
    sqlite_path = sys.argv[2]

    if not Path(zipfile_path).exists():
        print(f"Error: File not found: {zipfile_path}", file=sys.stderr)
        sys.exit(1)

    try:
        preprocess_usfm_to_sqlite(zipfile_path, sqlite_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
