import io
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
