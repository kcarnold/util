import io
import json
import re
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


def parse_verse_reference(ref: str) -> Tuple[str, Optional[str], str, Optional[str]]:
    """Parse a verse reference into (book, chapter, start_verse, end_verse).
    
    Supports formats like:
    - "Psalm 153:2" -> ("Psalm", "153", "2", None)
    - "Matthew 1:18-20" -> ("Matthew", "1", "18", "20")
    - "Jude 3" -> ("Jude", None, "3", None)
    """
    # Pattern to match book name followed by optional chapter:verse or just verse
    pattern = r'^([A-Za-z0-9\s]+?)\s+(?:(\d+):)?(\d+)(?:-(\d+))?$'
    match = re.match(pattern, ref.strip())
    
    if not match:
        raise ValueError(f"Invalid verse reference format: {ref}")
    
    book_name = match.group(1).strip()
    chapter = match.group(2)  # Could be None for single-chapter books
    start_verse = match.group(3)
    end_verse = match.group(4)  # Could be None for single verse
    
    return book_name, chapter, start_verse, end_verse


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
    """Extract specific verses from a USJ structure."""
    usj_content = usj['content']
    
    # If no chapter specified, assume single-chapter book (chapter "1")
    target_chapter = chapter or "1"
    
    # Convert verse numbers to integers for range comparison
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


def extract_verses(zipfile_path: str, ref: str) -> str:
    """Extract verses from a USFM zip file based on a verse reference.
    
    Args:
        zipfile_path: Path to the ZIP file containing USFM files
        ref: Verse reference like "Psalm 153:2", "Matthew 1:18-20", or "Jude 3"
    
    Returns:
        Formatted string with verse numbers and text
    """
    # Load the book abbreviations
    name_to_id = load_book_abbreviations()
    
    # Read the zip file
    with open(zipfile_path, 'rb') as f:
        zip_data = f.read()
    
    # Extract USFM files
    file_contents = extract_usfm_files_from_zip(zip_data)
    
    # Parse the verse reference
    book_name, chapter, start_verse, end_verse = parse_verse_reference(ref)
    
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
    
    return '\n--\n'.join(verse_lines)


def main():
    """Main entry point for the extract_verses command-line tool."""
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: extract_verses <zipfile> <verse_reference>", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  extract_verses bible.zip 'Psalm 153:2'", file=sys.stderr)
        print("  extract_verses bible.zip 'Matthew 1:18-20'", file=sys.stderr)
        print("  extract_verses bible.zip 'Jude 3'", file=sys.stderr)
        sys.exit(1)
    
    zipfile_path = sys.argv[1]
    verse_ref = sys.argv[2]
    
    try:
        result = extract_verses(zipfile_path, verse_ref)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python usfm_processor.py <zipfile> <verse_reference>", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python usfm_processor.py bible.zip 'Psalm 153:2'", file=sys.stderr)
        print("  python usfm_processor.py bible.zip 'Matthew 1:18-20'", file=sys.stderr)
        print("  python usfm_processor.py bible.zip 'Jude 3'", file=sys.stderr)
        sys.exit(1)
    
    zipfile_path = sys.argv[1]
    verse_ref = sys.argv[2]
    
    try:
        result = extract_verses(zipfile_path, verse_ref)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
