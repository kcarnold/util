import subprocess
import sys
from pathlib import Path
import io
import re
import zipfile

import streamlit as st
from usfm_grammar import Filter, USFMParser
from typing import Any, Dict, List


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
        chosen = st.selectbox("Select .usfm file from ZIP", usfm_files)
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
