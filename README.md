# Utility Scripts

A collection of utility scripts for various tasks.

## Scripts

### extract_verses

Extract specific verses from USFM (Unified Standard Format Marker) Bible files.

**Usage:**
```bash
extract_verses <zipfile_or_database> <verse_reference>
```

**Examples:**
```bash
# Extract from ZIP file (slower, parses USFM each time)
extract_verses bible.zip "Psalm 153:2"
extract_verses bible.zip "Matthew 1:18-20"
extract_verses bible.zip "Jude 3"

# Extract from SQLite database (faster, preprocessed)
extract_verses bible.db "Psalm 153:2"
extract_verses bible.db "Matthew 1:18-20"
```

**Performance Optimization:**

For faster verse extraction, preprocess your USFM ZIP file into a SQLite database:

```bash
# Preprocess once
preprocess_usfm bible.zip bible.db

# Then extract verses instantly
extract_verses bible.db "Matthew 1:18-20"
```

The SQLite database provides **significantly faster** verse extraction by avoiding USFM parsing on every request.

**Supported reference formats:**
- `"Book Chapter:Verse"` - Single verse (e.g., "Psalm 153:2")
- `"Book Chapter:StartVerse-EndVerse"` - Verse range (e.g., "Matthew 1:18-20")
- `"Book Verse"` - Single verse from single-chapter book (e.g., "Jude 3")
- `"Book Chapter"` - Entire chapter (e.g., "Matthew 1")
- `"Book Chapter:StartVerse-EndChapter:EndVerse"` - Cross-chapter range (e.g., "Exodus 15:29-16:2")

**Features:**
- Supports full English book names (Genesis, Matthew, Psalms, etc.)
- Handles both singular and plural forms (Psalm/Psalms)
- Automatic detection of single-chapter books
- Returns verses with their verse numbers
- Error handling for invalid references or missing content
- Dual backend support (ZIP or SQLite) with automatic detection

**Output format:**
```
18 In the sixth month the angel Gabriel was sent from God to a city of Galilee named Nazareth,
--
19 to a virgin betrothed to a man whose name was Joseph, of the house of David. And the virgin's name was Mary.
--
20 And the angel came to her and said, "Greetings, O favored one, the Lord is with you!"
```

### preprocess_usfm

Preprocess USFM files from a ZIP archive into a SQLite database for fast verse lookups.

**Usage:**
```bash
preprocess_usfm <zipfile> <output.db>
```

**Example:**
```bash
preprocess_usfm bible.zip bible.db
```

**What it does:**
- Extracts and parses all USFM files from the ZIP archive
- Stores all verses in a SQLite database with indexes for fast lookups
- Displays progress as it processes each book

This is a one-time operation. Once created, the SQLite database can be used with `extract_verses` for instant verse lookups.

### Other Scripts

- `validate_proclaim` - Validation script for Proclaim files
- `extract_usfm` - Streamlit-based USFM file extractor