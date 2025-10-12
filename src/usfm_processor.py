import io
import json
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from usfm_grammar import Filter, USFMParser


def parse_usfm(raw_text: str) -> Dict[str, Any]:
    """Parse USFM text and return the USJ structure."""
    parser = USFMParser(raw_text)
    if parser.errors:
        return {"errors": parser.errors}

    usj = parser.to_usj(include_markers=Filter.BCV + Filter.TEXT)
    return {"usj": usj}


def extract_id_h(usfm_text: str) -> Tuple[Optional[str], Optional[str]]:
    r"""Extract the initial \id and \h markers from the start of a USFM text.

    Returns (id, h) where each may be None if not found.
    """
    id_line: Optional[str] = None
    h_line: Optional[str] = None
    head = usfm_text[:2000]
    for line in head.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('\\id') and id_line is None:
            id_line = line[3:].strip()
        elif line.startswith('\\h') and h_line is None:
            h_line = line[2:].strip()
        if id_line is not None and h_line is not None:
            break
    return id_line, h_line


def get_label(sample_text: str, name: str) -> str:
    """Generate a label for a USFM file based on its ID and header markers."""
    id_line, h_line = extract_id_h(sample_text)
    label = ''
    if id_line:
        label += f"{id_line}"
    if h_line:
        if label:
            label += f": {h_line}"
        else:
            label = h_line
    label = label if label else name
    return label


def natural_key(s: str) -> List:
    """Return a key for natural sorting (numbers sorted numerically)."""
    # Split into digit and non-digit parts
    parts = re.split(r'(\d+)', s)
    key = []
    for p in parts:
        if p.isdigit():
            key.append(int(p))
        else:
            key.append(p.lower())
    return key


def extract_usfm_files_from_zip(zip_data: bytes) -> Dict[str, str]:
    """Extract USFM files from a ZIP archive and return a mapping of filename to content."""
    try:
        z = zipfile.ZipFile(io.BytesIO(zip_data))
    except zipfile.BadZipFile:
        raise ValueError("Uploaded file is not a valid ZIP archive.")

    usfm_files: List[str] = [n for n in z.namelist() if not n.endswith('/') and n.lower().endswith('.usfm')]
    
    if not usfm_files:
        raise ValueError("No .usfm files found inside the ZIP archive.")
    
    usfm_files.sort(key=natural_key)
    
    # Build a mapping from filename -> content
    file_contents: Dict[str, str] = {}
    for name in usfm_files:
        try:
            sample = z.read(name)
            # decode with replace to avoid stopping on decode errors
            try:
                content = sample.decode('utf-8')
            except Exception:
                content = sample.decode('utf-8', errors='replace')
            file_contents[name] = content
        except KeyError:
            # Skip missing files
            continue
    
    return file_contents


def get_file_labels(file_contents: Dict[str, str]) -> Dict[str, str]:
    """Generate labels for USFM files based on their content."""
    label_map: Dict[str, str] = {}
    for name, content in file_contents.items():
        label_map[name] = get_label(content, name)
    return label_map


def extract_books_from_usj(usj: Dict[str, Any]) -> List[str]:
    """Extract book codes from a USJ structure."""
    usj_content = usj['content']
    return [x['code'] for x in usj_content if isinstance(x, dict) and x['type'] == 'book']


def extract_chapters_from_usj(usj: Dict[str, Any]) -> List[str]:
    """Extract chapter numbers from a USJ structure."""
    usj_content = usj['content']
    return [x['number'] for x in usj_content if isinstance(x, dict) and x['type'] == 'chapter']


def extract_chapter_content(usj: Dict[str, Any], chapter: str) -> List[Any]:
    """Extract content for a specific chapter from a USJ structure."""
    usj_content = usj['content']
    chapter_text = []
    cur_chapter = None
    cur_verse = None
    
    for item in usj_content:
        if isinstance(item, dict) and item['type'] == 'chapter':
            cur_chapter = item['number']
        elif isinstance(item, dict) and item['type'] == 'verse':
            cur_verse = item['number']
        elif cur_chapter == chapter:
            chapter_text.append(item)
    
    return chapter_text


def load_book_abbreviations() -> Dict[str, str]:
    """Load the bible book abbreviations mapping from JSON file."""
    script_dir = Path(__file__).parent
    json_path = script_dir / 'bible_book_abbreviations.json'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create mapping from English name to identifier
    name_to_id = {}
    for book in data:
        name = book['English Name'].lower()
        identifier = book['Identifier']
        name_to_id[name] = identifier
        
        # Add common variations
        if name == "psalms":
            name_to_id["psalm"] = identifier
    
    return name_to_id


def parse_single_verse_reference(ref: str) -> Tuple[str, Optional[str], str, Optional[str]]:
    """Parse a single verse reference into (book, chapter, start_verse, end_verse).

    Supports formats like:
    - "Psalm 153:2" -> ("Psalm", "153", "2", None)
    - "Matthew 1:18-20" -> ("Matthew", "1", "18", "20")
    - "Matthew 6" -> ("Matthew", "6", "1", None) for entire chapter
    - "Jude 3" -> ("Jude", None, "3", None) for single-chapter books
    - "Exodus 15:29-16:2" -> ("Exodus", "15", "29", "16:2") for cross-chapter ranges
    """
    ref = ref.replace('–', '-')  # Normalize dash characters

    # First try to match cross-chapter range: "Book 15:29-16:2"
    cross_chapter_pattern = r'^([A-Za-z0-9\s]+?)\s+(\d+):(\d+)-(\d+):(\d+)$'
    match = re.match(cross_chapter_pattern, ref.strip())
    if match:
        book_name = match.group(1).strip()
        start_chapter = match.group(2)
        start_verse = match.group(3)
        end_chapter = match.group(4)
        end_verse = match.group(5)
        return book_name, start_chapter, start_verse, f"{end_chapter}:{end_verse}"

    # Try to match chapter:verse format first
    chapter_verse_pattern = r'^([A-Za-z0-9\s]+?)\s+(\d+):(\d+)(?:-(\d+))?$'
    match = re.match(chapter_verse_pattern, ref.strip())
    if match:
        book_name = match.group(1).strip()
        chapter = match.group(2)
        start_verse = match.group(3)
        end_verse = match.group(4)  # Could be None for single verse
        return book_name, chapter, start_verse, end_verse

    # Try to match just book and single number
    single_number_pattern = r'^([A-Za-z0-9\s]+?)\s+(\d+)$'
    match = re.match(single_number_pattern, ref.strip())
    if match:
        book_name = match.group(1).strip()
        number = match.group(2)

        # Check if this is a single-chapter book
        single_chapter_books = {
            'obadiah', 'philemon', 'jude', '2 john', '3 john'
        }

        if book_name.lower() in single_chapter_books:
            # For single-chapter books, the number is the verse
            return book_name, None, number, None
        else:
            # For multi-chapter books, the number is the chapter (return entire chapter)
            return book_name, number, "1", None

    raise ValueError(f"Invalid verse reference format: {ref}")


def parse_verse_reference(ref: str) -> List[Tuple[str, Optional[str], str, Optional[str]]]:
    """Parse a verse reference into a list of (book, chapter, start_verse, end_verse) tuples.

    Supports formats like:
    - "Psalm 153:2" -> [("Psalm", "153", "2", None)]
    - "Matthew 1:18-20" -> [("Matthew", "1", "18", "20")]
    - "Exodus 15:1-2,11-15" -> [("Exodus", "15", "1", "2"), ("Exodus", "15", "11", "15")]
    - "Exodus 15:29-16:2" -> [("Exodus", "15", "29", "16:2")]
    """
    ref = ref.strip()

    # Handle comma-separated references
    if ',' in ref:
        parts = [part.strip() for part in ref.split(',')]
        results = []
        base_book = None
        base_chapter = None

        for i, part in enumerate(parts):
            if i == 0:
                # First part should have full book and chapter
                parsed = parse_single_verse_reference(part)
                base_book, base_chapter = parsed[0], parsed[1]
                results.append(parsed)
            else:
                # Subsequent parts might be just verse ranges
                if ':' not in part and base_book and base_chapter:
                    # Just verse range, use base book and chapter
                    full_ref = f"{base_book} {base_chapter}:{part}"
                    results.append(parse_single_verse_reference(full_ref))
                else:
                    # Full reference or chapter:verse
                    if not any(char.isalpha() for char in part):
                        # No book name, use base book
                        full_ref = f"{base_book} {part}"
                        results.append(parse_single_verse_reference(full_ref))
                    else:
                        results.append(parse_single_verse_reference(part))
        return results
    else:
        # Single reference
        return [parse_single_verse_reference(ref)]


def find_book_in_usfm_files(book_name: str, file_contents: Dict[str, str], name_to_id: Dict[str, str]) -> str:
    """Find the USFM file that contains the specified book."""
    # Get the 3-letter book identifier
    book_id = name_to_id.get(book_name.lower())
    if not book_id:
        raise ValueError(f"Unknown book name: {book_name}")
    
    # Look for a file that starts with this book ID
    for filename, content in file_contents.items():
        id_line, _ = extract_id_h(content)
        if id_line and id_line.upper().startswith(book_id):
            return filename
    
    raise ValueError(f"Book {book_name} ({book_id}) not found in USFM files")


def extract_verses_from_usj(usj: Dict[str, Any], chapter: Optional[str], start_verse: str, end_verse: Optional[str]) -> List[str]:
    """Extract specific verses from a USJ structure.

    Handles both single-chapter ranges and cross-chapter ranges.
    For cross-chapter ranges, end_verse should be in format "chapter:verse" (e.g., "16:2").
    """
    usj_content = usj['content']

    # Check if this is a cross-chapter range
    is_cross_chapter = end_verse and ':' in end_verse

    if is_cross_chapter:
        # Parse cross-chapter range
        assert end_verse is not None  # We know this from is_cross_chapter check
        end_chapter, end_verse_str = end_verse.split(':')
        start_chapter = chapter or "1"
        start_verse_num = int(start_verse)
        end_verse_num = int(end_verse_str)

        # Collect verses across multiple chapters
        verse_texts = {}  # (chapter, verse) -> text content
        cur_chapter = None
        cur_verse = None

        for item in usj_content:
            if isinstance(item, dict):
                if item['type'] == 'chapter':
                    cur_chapter = item['number']
                elif item['type'] == 'verse':
                    cur_verse = item['number']
                    # Check if this verse is in our range
                    chapter_num = int(cur_chapter) if cur_chapter else 1
                    verse_num = int(cur_verse)
                    start_ch_num = int(start_chapter)
                    end_ch_num = int(end_chapter)

                    in_range = False
                    if chapter_num == start_ch_num and chapter_num == end_ch_num:
                        # Same chapter range
                        in_range = start_verse_num <= verse_num <= end_verse_num
                    elif chapter_num == start_ch_num:
                        # Start chapter
                        in_range = verse_num >= start_verse_num
                    elif chapter_num == end_ch_num:
                        # End chapter
                        in_range = verse_num <= end_verse_num
                    elif start_ch_num < chapter_num < end_ch_num:
                        # Middle chapter
                        in_range = True

                    if in_range:
                        verse_texts[(chapter_num, verse_num)] = ""
                elif cur_chapter and cur_verse:
                    # This is text content
                    chapter_num = int(cur_chapter)
                    verse_num = int(cur_verse)
                    if (chapter_num, verse_num) in verse_texts:
                        if isinstance(item, str):
                            verse_texts[(chapter_num, verse_num)] += item
                        elif 'text' in item:
                            verse_texts[(chapter_num, verse_num)] += item['text']
            elif isinstance(item, str) and cur_chapter and cur_verse:
                # Plain text content
                chapter_num = int(cur_chapter)
                verse_num = int(cur_verse)
                if (chapter_num, verse_num) in verse_texts:
                    verse_texts[(chapter_num, verse_num)] += item

        # Return verses in order with chapter:verse format
        result = []
        for (ch_num, v_num) in sorted(verse_texts.keys()):
            text = verse_texts[(ch_num, v_num)].strip()
            result.append(f"{ch_num}:{v_num} {text}")

        return result

    else:
        # Single chapter range (original logic)
        target_chapter = chapter or "1"

        # Handle entire chapter request (start_verse="1" and end_verse=None)
        if start_verse == "1" and end_verse is None:
            # Collect all verses in the chapter
            cur_chapter = None
            cur_verse = None
            verse_texts = {}  # verse_num -> text content
            collecting = False

            for item in usj_content:
                if isinstance(item, dict):
                    if item['type'] == 'chapter':
                        cur_chapter = item['number']
                        collecting = (cur_chapter == target_chapter)
                    elif item['type'] == 'verse' and collecting:
                        cur_verse = item['number']
                        verse_num = int(cur_verse)
                        verse_texts[verse_num] = ""
                    elif collecting and cur_verse:
                        # This is text content
                        verse_num = int(cur_verse)
                        if isinstance(item, str):
                            verse_texts[verse_num] = verse_texts.get(verse_num, "") + item
                        elif 'text' in item:
                            verse_texts[verse_num] = verse_texts.get(verse_num, "") + item['text']
                elif isinstance(item, str) and collecting and cur_verse:
                    # Plain text content
                    verse_num = int(cur_verse)
                    verse_texts[verse_num] = verse_texts.get(verse_num, "") + item

            # Return all verses found in the chapter
            result = []
            for verse_num in sorted(verse_texts.keys()):
                text = verse_texts[verse_num].strip()
                result.append(f"{verse_num} {text}")

            return result

        else:
            # Handle specific verse range
            start_verse_num = int(start_verse)
            end_verse_num = int(end_verse) if end_verse else start_verse_num

            if start_verse_num > end_verse_num:
                raise ValueError(f"Start verse {start_verse_num} is greater than end verse {end_verse_num}")

            # Navigate through USJ to find the target chapter and verses
            cur_chapter = None
            cur_verse = None
            verse_texts = {}  # verse_num -> text content
            collecting = False

            for item in usj_content:
                if isinstance(item, dict):
                    if item['type'] == 'chapter':
                        cur_chapter = item['number']
                        collecting = (cur_chapter == target_chapter)
                    elif item['type'] == 'verse' and collecting:
                        cur_verse = item['number']
                        # Initialize verse text if we're in the target range
                        verse_num = int(cur_verse)
                        if start_verse_num <= verse_num <= end_verse_num:
                            verse_texts[verse_num] = ""
                    elif collecting and cur_verse:
                        # This is text content
                        verse_num = int(cur_verse)
                        if start_verse_num <= verse_num <= end_verse_num:
                            if isinstance(item, str):
                                verse_texts[verse_num] = verse_texts.get(verse_num, "") + item
                            elif 'text' in item:
                                verse_texts[verse_num] = verse_texts.get(verse_num, "") + item['text']
                elif isinstance(item, str) and collecting and cur_verse:
                    # Plain text content
                    verse_num = int(cur_verse)
                    if start_verse_num <= verse_num <= end_verse_num:
                        verse_texts[verse_num] = verse_texts.get(verse_num, "") + item

            # Verify we found all requested verses
            missing_verses = []
            for verse_num in range(start_verse_num, end_verse_num + 1):
                if verse_num not in verse_texts:
                    missing_verses.append(str(verse_num))

            if missing_verses:
                raise ValueError(f"Verses not found: {', '.join(missing_verses)} in chapter {target_chapter}")

            # Return verses in order with verse numbers
            result = []
            for verse_num in range(start_verse_num, end_verse_num + 1):
                text = verse_texts[verse_num].strip()
                result.append(f"{verse_num} {text}")

            return result


def extract_verses_from_sqlite(db_path: str, book_name: str, chapter: Optional[str], start_verse: str, end_verse: Optional[str], name_to_id: Dict[str, str]) -> List[str]:
    """Extract verses from a SQLite database.

    Args:
        db_path: Path to the SQLite database
        book_name: Name of the book
        chapter: Chapter number (or None for single-chapter books)
        start_verse: Starting verse number
        end_verse: Ending verse (or None for single verse, or "chapter:verse" for cross-chapter)

    Returns:
        List of formatted verse strings
    """
    # Get the book ID
    book_id = name_to_id.get(book_name.lower())
    if not book_id:
        raise ValueError(f"Unknown book name: {book_name}")

    conn = sqlite3.Connection(db_path)
    cursor = conn.cursor()

    # Check if this is a cross-chapter range
    is_cross_chapter = end_verse and ':' in end_verse

    if is_cross_chapter:
        # Parse cross-chapter range
        assert end_verse is not None
        end_chapter_str, end_verse_str = end_verse.split(':')
        start_chapter = int(chapter or "1")
        end_chapter = int(end_chapter_str)
        start_verse_num = int(start_verse)
        end_verse_num = int(end_verse_str)

        # Query verses across chapters
        cursor.execute("""
            SELECT chapter, verse, text
            FROM verses
            WHERE book_id = ?
              AND (
                (chapter = ? AND verse >= ?) OR
                (chapter > ? AND chapter < ?) OR
                (chapter = ? AND verse <= ?)
              )
            ORDER BY chapter, verse
        """, (book_id.upper(), start_chapter, start_verse_num, start_chapter, end_chapter, end_chapter, end_verse_num))

        verses = cursor.fetchall()
        conn.close()

        return [f"{ch}:{v} {text}" for ch, v, text in verses]

    else:
        # Single chapter range
        target_chapter = int(chapter or "1")

        if start_verse == "1" and end_verse is None:
            # Entire chapter
            cursor.execute("""
                SELECT verse, text
                FROM verses
                WHERE book_id = ? AND chapter = ?
                ORDER BY verse
            """, (book_id.upper(), target_chapter))
        else:
            # Specific verse range
            start_verse_num = int(start_verse)
            end_verse_num = int(end_verse) if end_verse else start_verse_num

            cursor.execute("""
                SELECT verse, text
                FROM verses
                WHERE book_id = ? AND chapter = ? AND verse >= ? AND verse <= ?
                ORDER BY verse
            """, (book_id.upper(), target_chapter, start_verse_num, end_verse_num))

        verses = cursor.fetchall()
        conn.close()

        if not verses:
            raise ValueError(f"Verses not found in chapter {target_chapter}")

        return [f"{v} {text}" for v, text in verses]


def extract_verses(zipfile_path: str, ref: str) -> str:
    """Extract verses from a USFM zip file or SQLite database based on a verse reference.

    Args:
        zipfile_path: Path to the ZIP file containing USFM files or SQLite database (.db, .sqlite)
        ref: Verse reference like "Psalm 153:2", "Matthew 1:18-20", "Jude 3",
             "Exodus 15:1-2,11-15", or "Exodus 15:29-16:2"

    Returns:
        Formatted string with verse numbers and text
    """
    # Load the book abbreviations
    name_to_id = load_book_abbreviations()

    # Parse the verse reference(s)
    parsed_refs = parse_verse_reference(ref)

    # Detect file type by extension
    file_path = Path(zipfile_path)
    is_sqlite = file_path.suffix.lower() in ['.db', '.sqlite', '.sqlite3']

    all_verse_lines = []

    if is_sqlite:
        # Extract verses from SQLite database
        for book_name, chapter, start_verse, end_verse in parsed_refs:
            verse_lines = extract_verses_from_sqlite(
                zipfile_path, book_name, chapter, start_verse, end_verse, name_to_id
            )
            all_verse_lines.extend(verse_lines)
    else:
        # Extract verses from ZIP file (original implementation)
        # Read the zip file
        with open(zipfile_path, 'rb') as f:
            zip_data = f.read()

        # Extract USFM files
        file_contents = extract_usfm_files_from_zip(zip_data)

        for book_name, chapter, start_verse, end_verse in parsed_refs:
            # Find the appropriate USFM file
            filename = find_book_in_usfm_files(book_name, file_contents, name_to_id)
            usfm_content = file_contents[filename]

            # Parse the USFM content
            parsed = parse_usfm(usfm_content)
            if 'errors' in parsed:
                raise ValueError(f"USFM parsing errors: {parsed['errors']}")

            usj = parsed['usj']

            # Extract the requested verses
            verse_lines = extract_verses_from_usj(usj, chapter, start_verse, end_verse)
            all_verse_lines.extend(verse_lines)

    return '\n--\n'.join(all_verse_lines)


def main() -> None:
    """Main entry point for the extract_verses command-line tool."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: extract_verses <zipfile_or_database> <verse_reference>", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  # From ZIP file (slower, parses USFM each time):", file=sys.stderr)
        print("  extract_verses bible.zip 'Psalm 153:2'", file=sys.stderr)
        print("  extract_verses bible.zip 'Matthew 1:18-20'", file=sys.stderr)
        print("  extract_verses bible.zip 'Jude 3'", file=sys.stderr)
        print("  extract_verses bible.zip 'Exodus 15:1-2,11-15'", file=sys.stderr)
        print("  extract_verses bible.zip 'Exodus 15:29-16:2'", file=sys.stderr)
        print("\n  # From SQLite database (faster, requires preprocessing):", file=sys.stderr)
        print("  extract_verses bible.db 'Matthew 1:18-20'", file=sys.stderr)
        print("\nTip: Use 'preprocess_usfm bible.zip bible.db' to create a fast SQLite database", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    verse_ref = sys.argv[2]

    try:
        result = extract_verses(file_path, verse_ref)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
