import subprocess
import sys
from pathlib import Path

import streamlit as st
from usfm_grammar import Filter, USFMParser


def main():
    """Entry point for the extract_usfm console script."""
    # Get the path to this script
    script_path = Path(__file__)
    
    # Launch streamlit with this script
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(script_path)
    ] + sys.argv[1:])


def streamlit_app():
    file = st.file_uploader("Upload USFM file", type=["usfm"])
    if file is None:
        st.stop()

    parser = USFMParser(file.read().decode("utf-8"))
    if parser.errors:
        st.write("Errors in USFM file:")
        for error in parser.errors:
            st.write(error)
        st.stop()

    usj = parser.to_usj(include_markers=Filter.BCV+Filter.TEXT)

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
