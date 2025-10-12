# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A collection of utility scripts, primarily focused on:
1. **Bible text processing**: USFM (Unified Standard Format Marker) parsing and verse extraction
2. **Proclaim presentation validation**: Validating Faithlife Proclaim presentation files for church services

## Development Setup

This project uses `uv` for Python dependency management. Python 3.12+ is required.

### Running Scripts

All scripts are defined as console entry points in [pyproject.toml](pyproject.toml):

```bash
# Extract verses from USFM files
uv run extract_verses <zipfile_or_database> <verse_reference>

# Preprocess USFM ZIP to SQLite for faster lookups
uv run preprocess_usfm <zipfile> <output.db>

# Launch Streamlit GUI for USFM extraction
uv run extract_usfm

# Validate Proclaim presentations (launches GUI by default)
uv run validate_proclaim
uv run validate_proclaim --cli  # CLI mode
```

### Testing

Tests are simple Python scripts that can be run directly:

```bash
# Test verse parsing functionality
uv run python test_extract_verses.py

# Test verse parsing patterns
uv run python test_verse_parsing.py

# Test SQLite extraction
uv run python test_sqlite_extraction.py
```

## Code Architecture

### USFM Processing System ([src/usfm_processor.py](src/usfm_processor.py))

Core module that handles USFM Bible text parsing and verse extraction. Key architectural elements:

- **Dual backend system**: Supports both ZIP files (slower, on-demand parsing) and SQLite databases (faster, preprocessed)
- **Reference parsing**: Complex regex-based parsing supporting multiple reference formats:
  - Single verses: "Psalm 153:2"
  - Verse ranges: "Matthew 1:18-20"
  - Cross-chapter ranges: "Exodus 15:29-16:2"
  - Comma-separated ranges: "Exodus 15:1-2,11-15"
  - Single-chapter books: "Jude 3"
  - Entire chapters: "Matthew 1"
- **Book name resolution**: Uses [bible_book_abbreviations.json](src/bible_book_abbreviations.json) to map English book names to 3-letter USFM identifiers
- **USJ intermediate format**: USFM files are parsed into USJ (Unified Scripture JSON) format using the `usfm-grammar` library

### Proclaim Validation System ([src/validate_proclaim.py](src/validate_proclaim.py))

Validates Faithlife Proclaim presentation files stored in SQLite format. Key architectural elements:

- **Database location**: Default path is `~/Library/Application Support/Proclaim/Data/5sos6hqf.xyd/PresentationManager/PresentationManager.db`
- **Validation modes**:
  - GUI (default): Tkinter-based interface with tree view for items and details pane
  - CLI: Rich-formatted terminal output
- **Multi-threaded design**: Background threads handle database queries and USFM lookups to keep GUI responsive
- **Validation checks**:
  - SongLyrics: Checks for missing translations, transition settings, media IDs
  - Content: Checks for missing translations, searches for prior similar content
  - BiblePassage: Cross-references with USFM database if available
- **Virtual screens**: Presentations can have multiple output screens (main, green screen, translation). Validation ensures content exists for expected screens.
- **USFM integration**: Can optionally load USFM Bible text to compare passage text in presentations with canonical references

### Import Organization

All modules in `src/` can import from each other using direct imports:
- `validate_proclaim.py` imports from `usfm_processor` to extract verses
- `extract_usfm.py` (Streamlit GUI) imports from `usfm_processor` for parsing
- Test files add `src/` to `sys.path` before importing

### Data Files

- [src/bible_book_abbreviations.json](src/bible_book_abbreviations.json): Maps English Bible book names to standard 3-letter USFM identifiers
- `bible.db`: SQLite database with preprocessed USFM verses (not in repo, created via `preprocess_usfm`)

## Common Development Tasks

### Adding Support for New Verse Reference Formats

Modify [parse_single_verse_reference()](src/usfm_processor.py#L163) in `usfm_processor.py`. The function returns `(book_name, chapter, start_verse, end_verse)` tuples.

### Modifying Proclaim Validation Rules

- Add validation logic to the appropriate function in `validate_proclaim.py`:
  - `validate_songlyrics()` for song items
  - `validate_plaintext()` for content slides
  - `validate_biblepassage()` for scripture passages
- Validation results are collected in `ValidationResult` objects with warnings, info, and debug messages

### Working with USFM Files

USFM files use marker-based format (e.g., `\id`, `\h`, `\c`, `\v`). The `usfm-grammar` library handles parsing to USJ format. All verse extraction logic works with the USJ intermediate representation, not raw USFM.
