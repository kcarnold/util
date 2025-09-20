import subprocess
import sys
from pathlib import Path
import io
import zipfile

import streamlit as st
from typing import Any, Dict, List

from .usfm_processor import (
    parse_usfm,
    extract_usfm_files_from_zip,
    get_file_labels,
    get_label,
    extract_books_from_usj,
    extract_chapters_from_usj,
    extract_chapter_content,
)


@st.cache_data
def cached_parse_usfm(raw_text: str) -> Dict[str, Any]:
    """Parse USFM text and return the USJ structure.

    Cached by streamlit to avoid re-parsing the same text repeatedly.
    """
    return parse_usfm(raw_text)


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

    # If a ZIP was uploaded, list .usfm files and let the user choose one
    filename_lower = getattr(file, "name", "").lower()
    if filename_lower.endswith('.zip'):
        data = file.read()
        try:
            file_contents = extract_usfm_files_from_zip(data)
        except ValueError as e:
            st.write(str(e))
            st.stop()

        label_map = get_file_labels(file_contents)
        usfm_files = list(file_contents.keys())

        # Show the selectbox displaying labels but returning the actual filename
        print('\n'.join(label_map.keys()))
        chosen = st.selectbox("Select book", usfm_files, format_func=lambda n: label_map.get(n, str(n)))
        raw = file_contents[chosen]
    else:
        raw = file.read().decode("utf-8")
        # Show extracted markers for single uploaded files
        st.info(get_label(raw, getattr(file, 'name', 'uploaded file')))
    
    result = cached_parse_usfm(raw)
    if "errors" in result:
        st.write("Errors in USFM file:")
        for error in result["errors"]:
            st.write(error)
        st.stop()

    usj: Dict[str, Any] = result["usj"]

    books = extract_books_from_usj(usj)
    st.write(','.join(books))

    chapters = extract_chapters_from_usj(usj)
    chapter = st.selectbox("Select chapter", chapters)
    st.write(chapter)

    chapter_text = extract_chapter_content(usj, chapter)

    st.code('\n--\n'.join(f'{i} {text.strip()}' for i, text in enumerate(chapter_text, start=1)))

if __name__ == "__main__":

    if 'streamlit' in sys.modules:
        streamlit_app()
    else:
        main()
