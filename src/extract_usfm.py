import subprocess
import sys
from pathlib import Path
import io
import re
import zipfile

import streamlit as st
from usfm_grammar import Filter, USFMParser
from typing import Any, Dict, List, Optional, Tuple


@st.cache_data
def parse_usfm(raw_text: str) -> Dict[str, Any]:
    """Parse USFM text and return the USJ structure.

    Cached by streamlit to avoid re-parsing the same text repeatedly.
    """
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


def get_label(sample_text, name):
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


def main():
    """Entry point for the extract_usfm console script."""
    # Get the path to this script
    script_path = Path(__file__)
    
    # Launch streamlit with this script
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(script_path)
    ] + sys.argv[1:])


def streamlit_app():
    file = st.file_uploader("Upload USFM file or ZIP (drag & drop supported)", type=["usfm", "zip"])
    if file is None:
        st.stop()

    def _natural_key(s: str):
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

    # If a ZIP was uploaded, list .usfm files and let the user choose one
    filename_lower = getattr(file, "name", "").lower()
    if filename_lower.endswith('.zip'):
        data = file.read()
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            st.write("Uploaded file is not a valid ZIP archive.")
            st.stop()

        usfm_files: List[str] = [n for n in z.namelist() if not n.endswith('/') and n.lower().endswith('.usfm')]
        if not usfm_files:
            st.write("No .usfm files found inside the ZIP archive.")
            st.stop()
        usfm_files.sort(key=_natural_key)
        # Build a mapping from filename -> label showing extracted \id and \h
        label_map: Dict[str, str] = {}
        for name in usfm_files:
            try:
                sample = z.read(name)
            except KeyError:
                label_map[name] = f"{name} (missing)"
                continue
            # decode with replace to avoid stopping selection creation on decode errors
            try:
                sample_text = sample.decode('utf-8')
            except Exception:
                sample_text = sample.decode('utf-8', errors='replace')
            label_map[name] = get_label(sample_text, name)

        # Show the selectbox displaying labels but returning the actual filename
        chosen = st.selectbox("Select book", usfm_files, format_func=lambda n: label_map.get(n, str(n)))
        try:
            raw = z.read(chosen).decode("utf-8")
        except KeyError:
            st.write("Selected file not found in ZIP archive.")
            st.stop()
        except UnicodeDecodeError:
            st.write("Selected file could not be decoded as UTF-8.")
            st.stop()
    else:
        raw = file.read().decode("utf-8")
        # Show extracted markers for single uploaded files
        st.info(get_label(raw, getattr(file, 'name', 'uploaded file')))
    result = parse_usfm(raw)
    if "errors" in result:
        st.write("Errors in USFM file:")
        for error in result["errors"]:
            st.write(error)
        st.stop()

    usj: Dict[str, Any] = result["usj"]
    usj_content = usj['content']

    books = [x['code'] for x in usj_content if isinstance(x, dict) and x['type'] == 'book']
    st.write(','.join(books))

    chapters = [x['number'] for x in usj_content if isinstance(x, dict) and x['type'] == 'chapter']
    chapter = st.selectbox("Select chapter", chapters)
    st.write(chapter)

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

    st.code('\n--\n'.join(f'{i} {text.strip()}' for i, text in enumerate(chapter_text, start=1)))

if __name__ == "__main__":

    if 'streamlit' in sys.modules:
        streamlit_app()
    else:
        main()
