#!/usr/bin/env python3
"""Test SQLite extraction functionality."""

import sys
import tempfile
import zipfile
from pathlib import Path

# Add src to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from preprocess_usfm_to_sqlite import preprocess_usfm_to_sqlite
from usfm_processor import extract_verses


def create_test_zip_with_single_book(source_zip_path: str, book_id: str) -> str:
    """Extract a single book from the source zip and create a test zip."""
    import io

    # Read the source zip
    with zipfile.ZipFile(source_zip_path, 'r') as source_zip:
        # Find the file containing the specified book
        target_file = None
        for name in source_zip.namelist():
            if not name.endswith('/') and name.lower().endswith('.usfm'):
                content = source_zip.read(name).decode('utf-8', errors='replace')
                # Check if this file contains the book
                for line in content[:2000].splitlines():
                    line = line.strip()
                    if line.startswith('\\id'):
                        file_book_id = line[3:].strip().split()[0] if line[3:].strip() else None
                        if file_book_id and file_book_id.upper() == book_id.upper():
                            target_file = (name, content)
                            break
                if target_file:
                    break

        if not target_file:
            raise ValueError(f"Book {book_id} not found in {source_zip_path}")

        # Create a temporary zip with just this book
        temp_zip = tempfile.NamedTemporaryFile(mode='wb', suffix='.zip', delete=False)
        with zipfile.ZipFile(temp_zip, 'w') as test_zip:
            test_zip.writestr(target_file[0], target_file[1])

        temp_zip.close()
        return temp_zip.name


def main():
    """Run tests on SQLite extraction."""
    source_zip = Path.home() / "Documents" / "bible.zip"

    if not source_zip.exists():
        print(f"Error: {source_zip} not found")
        sys.exit(1)

    # Test with a small book (Jude) - single chapter
    print(f"Creating test zip with just the book of Jude...")
    test_zip_jude = create_test_zip_with_single_book(str(source_zip), "JUD")
    print(f"Test zip created: {test_zip_jude}")

    # Test with Matthew chapter 1
    print(f"Creating test zip with just the book of Matthew...")
    test_zip_mat = create_test_zip_with_single_book(str(source_zip), "MAT")
    print(f"Test zip created: {test_zip_mat}")

    # Combine both books into one test zip
    test_zip_path = tempfile.NamedTemporaryFile(mode='wb', suffix='.zip', delete=False).name
    with zipfile.ZipFile(test_zip_path, 'w') as combined_zip:
        with zipfile.ZipFile(test_zip_jude, 'r') as jude_zip:
            for name in jude_zip.namelist():
                combined_zip.writestr(name, jude_zip.read(name))
        with zipfile.ZipFile(test_zip_mat, 'r') as mat_zip:
            for name in mat_zip.namelist():
                combined_zip.writestr(name, mat_zip.read(name))

    print(f"Combined test zip created: {test_zip_path}")

    # Create SQLite database
    temp_db = tempfile.NamedTemporaryFile(mode='wb', suffix='.db', delete=False)
    temp_db.close()
    db_path = temp_db.name

    print(f"\nPreprocessing USFM to SQLite: {db_path}")
    preprocess_usfm_to_sqlite(test_zip_path, db_path)

    print("\n" + "="*60)
    print("Testing extraction from SQLite database")
    print("="*60)

    # Test 1: Single verse
    print("\nTest 1: Single verse (Jude 3)")
    result_sqlite = extract_verses(db_path, "Jude 3")
    print(result_sqlite)

    # Compare with ZIP extraction
    print("\n" + "-"*60)
    print("Comparing with ZIP extraction:")
    result_zip = extract_verses(test_zip_path, "Jude 3")
    print(result_zip)

    if result_sqlite == result_zip:
        print("\n✓ Results match!")
    else:
        print("\n✗ Results differ!")
        print(f"SQLite: {repr(result_sqlite)}")
        print(f"ZIP: {repr(result_zip)}")

    # Test 2: Entire book (single-chapter book)
    print("\n" + "="*60)
    print("Test 2: Entire book (Jude 1)")
    print("="*60)
    result_sqlite = extract_verses(db_path, "Jude 1")
    result_zip = extract_verses(test_zip_path, "Jude 1")

    if result_sqlite == result_zip:
        print("✓ Results match!")
        print(f"Total verses in Jude: {len(result_sqlite.split('--'))}")
    else:
        print("✗ Results differ!")
        print(f"SQLite verses: {len(result_sqlite.split('--'))}")
        print(f"ZIP verses: {len(result_zip.split('--'))}")

    # Test 3: Multi-chapter book verse range
    print("\n" + "="*60)
    print("Test 3: Verse range from Matthew (Matthew 1:18-20)")
    print("="*60)
    result_sqlite = extract_verses(db_path, "Matthew 1:18-20")
    result_zip = extract_verses(test_zip_path, "Matthew 1:18-20")

    print("SQLite result:")
    print(result_sqlite)

    if result_sqlite == result_zip:
        print("\n✓ Results match!")
    else:
        print("\n✗ Results differ!")
        print("\nZIP result:")
        print(result_zip)

    # Cleanup
    Path(test_zip_jude).unlink()
    Path(test_zip_mat).unlink()
    Path(test_zip_path).unlink()
    Path(db_path).unlink()
    print(f"\nCleaned up temporary files")


if __name__ == "__main__":
    main()
