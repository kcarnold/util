# Utility Scripts

A collection of utility scripts for various tasks.

## Scripts

### extract_verses

Extract specific verses from USFM (Unified Standard Format Marker) Bible files.

**Usage:**
```bash
extract_verses <zipfile> <verse_reference>
```

**Examples:**
```bash
# Extract a single verse
extract_verses bible.zip "Psalm 153:2"

# Extract a range of verses
extract_verses bible.zip "Matthew 1:18-20"

# Extract from a single-chapter book (no chapter number needed)
extract_verses bible.zip "Jude 3"
```

**Supported reference formats:**
- `"Book Chapter:Verse"` - Single verse (e.g., "Psalm 153:2")
- `"Book Chapter:StartVerse-EndVerse"` - Verse range (e.g., "Matthew 1:18-20")
- `"Book Verse"` - Single verse from single-chapter book (e.g., "Jude 3")

**Features:**
- Supports full English book names (Genesis, Matthew, Psalms, etc.)
- Handles both singular and plural forms (Psalm/Psalms)
- Automatic detection of single-chapter books
- Returns verses with their verse numbers
- Error handling for invalid references or missing content

**Output format:**
```
18 In the sixth month the angel Gabriel was sent from God to a city of Galilee named Nazareth,
--
19 to a virgin betrothed to a man whose name was Joseph, of the house of David. And the virgin's name was Mary.
--
20 And the angel came to her and said, "Greetings, O favored one, the Lord is with you!"
```

### Other Scripts

- `validate_proclaim` - Validation script for Proclaim files
- `extract_usfm` - Streamlit-based USFM file extractor