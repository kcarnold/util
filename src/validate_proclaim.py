#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "lxml",
#     "rich",
# ]
# ///
import difflib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import argparse
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading

from lxml import etree
from rich import print as rprint


@dataclass
class ValidationResult:
    """Result of validating a single item."""
    item_type: str
    title: str
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    debug: List[str] = field(default_factory=list)
    prior_matches: List[Dict[str, Any]] = field(default_factory=list)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def add_info(self, message: str):
        self.info.append(message)

    def add_debug(self, message: str):
        self.debug.append(message)

    def has_issues(self) -> bool:
        return bool(self.warnings)


@dataclass
class PresentationValidation:
    """Result of validating an entire presentation."""
    presentation_id: str
    title: str
    date_given: str
    items: List[ValidationResult] = field(default_factory=list)

    def add_item(self, item: ValidationResult):
        self.items.append(item)

    def get_items_with_issues(self) -> List[ValidationResult]:
        return [item for item in self.items if item.has_issues()]

    def has_any_issues(self) -> bool:
        return any(item.has_issues() for item in self.items)


expected_main_media_id = '"b0a6c8b2-ea84-4d21-a2fd-a31ddd00412b"'
expected_greenscreen_media_id = '"aadb60bc-6e4f-4e56-bff9-325b0f26dd0a"'


def decode_richtextXML(xml):
    # _richtextfield:Lyrics <Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I love You Lord" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Oh Your mercy never fails me" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my days" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I’ve been held in Your hands" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="From the moment that I wake up" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Until I lay my head" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I will sing of the goodness of God" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been faithful" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been so, so good" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="With every breath that I am able" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I will sing of the goodness of God" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I love Your voice" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="You have led me through the fire" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="In darkest night" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="You are close like no other" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I’ve known You as a father" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I’ve known You as a friend" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I have lived in the goodness of God" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been faithful" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been so, so good" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="With every breath that I am able" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I will sing of the goodness of God" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Your goodness is running after" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="It’s running after me" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Your goodness is running after" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="It’s running after me" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="With my life laid down" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I’m surrendered now" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I give You everything" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Your goodness is running after" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="It’s running after me" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Your goodness is running after" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="It’s running after me" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Your goodness is running after" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="It’s running after me" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="With my life laid down" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I’m surrendered now" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I give You everything" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="Your goodness is running after" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="It’s running after me" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been faithful" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been so, so good" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="With every breath that I am able" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I will sing of the goodness of God" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" /><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been faithful" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="All my life You have been so, so good" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="With every breath that I am able" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I will sing of the goodness of God" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0"><Run Text="I will sing of the goodness of God" /></Paragraph><Paragraph Language="en-US" Margin="0,0,0,0" />

    # parse that XML: each Paragraph Run Text is a line
    """"
    Decode the rich text XML from Proclaim into plain text.

    The basic XML format is:
    <Paragraph Language="en-US" Margin="0,0,0,0">
        <Run Text="I love You Lord" />
    </Paragraph>
    <Paragraph Language="en-US" Margin="0,0,0,0">
        <Run Text="Oh Your mercy never fails me" />
    </Paragraph>
    etc.

    Each Paragraph contains one or more Run elements, each with a Text attribute (and maybe formatting attributes?).
    """
    result = ''

    root = etree.fromstring('<Song>' + xml + '</Song>', parser=None)
    for paragraph in root:
        runs = paragraph.findall('Run')
        for run in runs:
            result += run.attrib['Text'] + ' '
        result += '\n'
    return result



def warn(item_name, message):
    rprint(f"[bold red]***Warning***[/bold red]: {item_name}: {message}")


def look_for_prior_occurrences_functional(text, conn) -> List[Dict[str, Any]]:
    """
    Search all ServiceItems of kind 'Content' in all presentations since 2024-01-01
    for content with high overlap to the given text (after decoding richtextXML, lowercasing, and normalizing whitespace).
    Return the 2 highest-overlap items (presentation date, item title, first 100 chars), unless both ratios are < 0.5.
    """
    def normalize(s):
        return ' '.join(s.lower().split())

    norm_text = normalize(text)

    rows = conn.execute(
        '''
        SELECT p.DateGiven, si.Title, si.Content
        FROM ServiceItems si
        JOIN Presentations p ON si.PresentationId = p.PresentationId
        WHERE si.ServiceItemKind = 'Content'
          AND p.DateGiven > "2024-01-01"
        ''').fetchall()

    matches = []
    for date_given, item_title, content_json in rows:
        try:
            content = json.loads(content_json)
            if '_richtextfield:Main Content' not in content:
                continue
            item_text = decode_richtextXML(content['_richtextfield:Main Content'])
            norm_item_text = normalize(item_text)
            ratio = difflib.SequenceMatcher(None, norm_text, norm_item_text).ratio()
            matches.append({
                'ratio': ratio,
                'date_given': date_given,
                'title': item_title,
                'text': item_text,
                'snippet': item_text.strip().replace('\n', ' ')[:100]
            })
        except Exception:
            continue

    # Sort by ratio descending and keep only matches with ratio >= 0.5
    matches.sort(reverse=True, key=lambda x: x['ratio'])
    return [m for m in matches if m['ratio'] >= 0.5][:2]


def split_into_sections(text):
    """Split the text into sections based on blank lines or --."""
    sections = ['']
    for line in text.strip().split('\n'):
        line_stripped = line.strip()
        if line_stripped == '' or line_stripped == '--':
            sections.append('')
        else:
            sections[-1] += line + '\n'
    return [section.strip() for section in sections if section.strip() != '' and not (section.startswith('{Credits}') or section.startswith('{Source}'))]


def get_first_line(text):
    """Get the first non-empty line from the text."""
    return text.strip().split('\n')[0].strip()


# def split_into_song_sections(text) -> Dict[str, str]:
#     """
#     Split the song text into sections. A blank line followed by one of the following, or a line in {braces}, marks a section:
#     Verse, Chorus, Pre-chorus, Bridge, Tag, Title, Interlude

#     From the Proclaim documentation:
    
#     Verse Tag  Shorthands
#     Verse 	  	V, V1, 1
#     Chorus 	  	C1
#     Pre-chorus 	  	P1
#     Bridge 	  	B
#     Tag 	  	T
#     Title 	  	T (if Tag is not present)
#     Interlude 	  	I
#     Blank 	  	B (Bridge prioritizes over blank)
#     [Custom] 	  	First letter of custom tag
#     """

#     sections = {}
#     current_section = None
#     for line in text.strip().split('\n'):


def get_slides_for_song(item, content_key=None) -> List[str]:
    """Get the slides for a given item."""
    assert item_kind == "SongLyrics", f"Item kind is not SongLyrics: {item_kind}"
    if content_key is None:
        content_key = '_richtextfield:Lyrics'
    content = decode_richtextXML(item[content_key])
    # TODO: handle sequence markers

    # if item.get('CustomOrderSlides', '') == 'true':
    #     sequence = item['CustomOrderSequence']


    return split_into_sections(content)


def assert_translation_ok(original_slides, translation_slides):
    if original_slides == translation_slides:
        warn(title, "Original and translation slides are identical")
        return
    if len(original_slides) == len(translation_slides):
        return
    warn(title, f"Number of slides in original ({len(original_slides)}) and translation ({len(translation_slides)}) do not match")
    # print the first line of each slide, for debug
    for i in range(max(len(original_slides), len(translation_slides))):
        original_slide = original_slides[i] if i < len(original_slides) else ''
        translation_slide = translation_slides[i] if i < len(translation_slides) else ''
        print(f"Slide {i:>2d}: {get_first_line(original_slide):>50} | {get_first_line(translation_slide):50}")


def validate_songlyrics_functional(title: str, content: dict) -> ValidationResult:
    """Validate the SongLyrics item."""
    result = ValidationResult(item_type="SongLyrics", title=title)

    if not content.get('_richtextfield:Lyrics'):
        result.add_warning(f"Missing _richtextfield:Lyrics")
        return result

    # check transitions
    transition_info = (content.get('UseCustomTransition'), content.get('CustomTransitionKind'), content.get('CustomTransitionDuration'))
    if transition_info != ('true', 'LyricScrolling', '0'):
        result.add_warning(f"Unexpected transition info: {transition_info}")

    # Find the translations output
    translations = [key for key in content if key.startswith("slideOutput") and key.endswith("RichTextXml")]
    if len(translations) != 1:
        result.add_warning(f"Expected one translation, found {len(translations)}")
        return result
    translation_key = translations[0]

    try:
        original_slides = get_slides_for_song(content)
        translation_slides = get_slides_for_song(content, translation_key)

        # Check slide count match
        if original_slides != translation_slides:
            if len(original_slides) != len(translation_slides):
                result.add_warning(f"Number of slides in original ({len(original_slides)}) and translation ({len(translation_slides)}) do not match")
                result.add_debug("Slide comparison:")
                for i in range(max(len(original_slides), len(translation_slides))):
                    original_slide = original_slides[i] if i < len(original_slides) else ''
                    translation_slide = translation_slides[i] if i < len(translation_slides) else ''
                    result.add_debug(f"Slide {i:>2d}: {get_first_line(original_slide):>50} | {get_first_line(translation_slide):50}")
        elif original_slides == translation_slides:
            result.add_warning("Original and translation slides are identical")
    except Exception as e:
        result.add_warning(f"Error validating slides: {e}")

    # Check media IDs
    if content.get('slideOutput:0:MediaId') != expected_main_media_id:
        result.add_warning(f"Expected main media ID {expected_main_media_id}, found {content.get('slideOutput:0:MediaId')}")
    if content.get('slideOutput:1:MediaId') != expected_greenscreen_media_id:
        result.add_warning(f"Expected green-screen media ID {expected_greenscreen_media_id}, found {content.get('slideOutput:1:MediaId')}")

    return result


def validate_songlyrics(content):
    """Validate the SongLyrics item."""
    assert content.get('_richtextfield:Lyrics'), f"Missing _richtextfield:Lyrics in {title}"

    # check transitions
    transition_info = (content.get('UseCustomTransition'), content.get('CustomTransitionKind'), content.get('CustomTransitionDuration'))
    if transition_info != ('true', 'LyricScrolling', '0'):
        warn(title, f"Unexpected transition info: {transition_info}")

    # Find the translations output
    translations = [key for key in content if key.startswith("slideOutput") and key.endswith("RichTextXml")]
    if len(translations) != 1:
        warn(title, f"Expected one translation, found {len(translations)}")
        return
    translation_key = translations[0]

    original_slides = get_slides_for_song(content)
    translation_slides = get_slides_for_song(content, translation_key)
    assert_translation_ok(original_slides, translation_slides)

    #print(content.keys())
    if content.get('slideOutput:0:MediaId') != expected_main_media_id:
        warn(title, f"Expected main media ID {expected_main_media_id}, found {content.get('slideOutput:0:MediaId')}")
    if content.get('slideOutput:1:MediaId') != expected_greenscreen_media_id:
        warn(title, f"Expected green-screen media ID {expected_greenscreen_media_id}, found {content.get('slideOutput:1:MediaId')}")



def validate_plaintext_functional(title: str, content: dict, key: str, greenscreen_screen_idx: Optional[int], translation_screen_idx: int, conn) -> ValidationResult:
    """Validate plaintext content items functionally."""
    result = ValidationResult(item_type="Content", title=title)

    if key not in content:
        result.add_warning(f"Missing {key}")
        return result

    main_content = decode_richtextXML(content[key])
    if main_content.strip() == '':
        # image-only slide
        result.add_info("Image-only slide")
        return result

    if greenscreen_screen_idx is not None:
        greenscreen_key = f'slideOutput:{greenscreen_screen_idx-1}:RichTextXml'
        if greenscreen_key in content:
            result.add_warning("Unexpected greenscreen content")

    translation_key = f'slideOutput:{translation_screen_idx-1}:RichTextXml'
    if translation_key not in content:
        result.add_warning("Missing translation")
        # Look for prior occurrences
        prior_matches = look_for_prior_occurrences_functional(main_content, conn)
        result.prior_matches = prior_matches
        if prior_matches:
            result.add_info(f"Found {len(prior_matches)} similar prior items")
        return result

    translation_content = decode_richtextXML(content[translation_key])
    main_slides = split_into_sections(main_content)
    translation_slides = split_into_sections(translation_content)

    # Check slide alignment
    if main_slides == translation_slides:
        result.add_warning("Original and translation slides are identical")
    elif len(main_slides) != len(translation_slides):
        result.add_warning(f"Number of slides in original ({len(main_slides)}) and translation ({len(translation_slides)}) do not match")
        result.add_debug("Slide comparison:")
        for i in range(max(len(main_slides), len(translation_slides))):
            original_slide = main_slides[i] if i < len(main_slides) else ''
            translation_slide = translation_slides[i] if i < len(translation_slides) else ''
            result.add_debug(f"Slide {i:>2d}: {get_first_line(original_slide):>50} | {get_first_line(translation_slide):50}")

    return result


def validate_plaintext(content, key):
    assert key in content, f"Missing {key} in {title}"
    main_content = decode_richtextXML(content[key])
    if main_content.strip() == '':
        # image-only slide
        return
    if greenscreen_screen_idx is not None:
        greenscreen_key = f'slideOutput:{greenscreen_screen_idx-1}:RichTextXml'
        if greenscreen_key in content:
            warn(title, "Unexpected greenscreen content")
    translation_key = f'slideOutput:{translation_screen_idx-1}:RichTextXml'
    if translation_key not in content:
        warn(title, f"Missing translation")
        look_for_prior_occurrences(main_content)
        return
    translation_content = decode_richtextXML(content[translation_key])
    main_slides = split_into_sections(main_content)
    translation_slides = split_into_sections(translation_content)
    assert_translation_ok(main_slides, translation_slides)


def look_for_prior_occurrences(text):
    """
    Search all ServiceItems of kind 'Content' in all presentations since 2024-01-01
    for content with high overlap to the given text (after decoding richtextXML, lowercasing, and normalizing whitespace).
    Print the 2 highest-overlap items (presentation date, item title, first 100 chars), unless both ratios are < 0.5.
    """
    # Normalize input text
    def normalize(s):
        return ' '.join(s.lower().split())

    norm_text = normalize(text)

    # Use a single SQL query with a join
    rows = conn.execute(
        '''
        SELECT Presentations.DateGiven, ServiceItems.Title, ServiceItems.Content
        FROM ServiceItems
        JOIN Presentations ON ServiceItems.PresentationId = Presentations.PresentationId
        WHERE ServiceItems.ServiceItemKind = 'Content'
          AND Presentations.DateGiven > "2024-01-01"
          AND Presentations.Title NOT LIKE "INCORRECT%"
        ''').fetchall()

    matches = []
    for date_given, item_title, content_json in rows:
        try:
            content = json.loads(content_json)
            if '_richtextfield:Main Content' not in content:
                continue
            item_text = decode_richtextXML(content['_richtextfield:Main Content'])
            norm_item_text = normalize(item_text)
            ratio = difflib.SequenceMatcher(None, norm_text, norm_item_text).ratio()
            matches.append((ratio, date_given, item_title, item_text))
        except Exception:
            continue

    # Sort by ratio descending
    matches.sort(reverse=True, key=lambda x: x[0])
    # Only keep matches with ratio >= 0.5
    top_matches = [m for m in matches if m[0] >= 0.5][:2]
    if not top_matches:
        return
    rprint("[bold yellow]Prior similar Content items:[/bold yellow]")
    for ratio, date_given, item_title, item_text in top_matches:
        snippet = item_text.strip().replace('\n', ' ')[:100]
        rprint(f"[bold]{date_given}[/bold] [dim]{item_title}[/dim] (similarity: {ratio:.2f}): {snippet}")
    return

def validate_biblepassage_functional(title: str, content: dict, greenscreen_screen_idx: Optional[int], translation_screen_idx: int, conn) -> ValidationResult:
    """Validate Bible passage content functionally."""
    result = ValidationResult(item_type="BiblePassage", title=title)

    bible_ref = content.get('_textfield:BibleReference')
    if bible_ref:
        result.add_info(f"Bible reference: {bible_ref}")
    else:
        result.add_warning("Missing Bible reference")

    # Validate the passage content using the plaintext validation
    passage_result = validate_plaintext_functional(title, content, "_richtextfield:Passage", greenscreen_screen_idx, translation_screen_idx, conn)

    # Merge the results
    result.warnings.extend(passage_result.warnings)
    result.info.extend(passage_result.info)
    result.debug.extend(passage_result.debug)
    result.prior_matches = passage_result.prior_matches

    return result


def validate_biblepassage(content):
    print(content.get('_textfield:BibleReference'))
    validate_plaintext(content, key="_richtextfield:Passage")


class ProclaimValidator:
    """Class to handle database connections and presentation validation."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            proclaim_data = Path('~/Library/Application Support/Proclaim/Data/5sos6hqf.xyd/').expanduser()
            self.db_path = str(proclaim_data / 'PresentationManager' / 'PresentationManager.db')
        else:
            self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Connect to the Proclaim database."""
        self.conn = sqlite3.connect(self.db_path)

    def disconnect(self):
        """Disconnect from the database."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_presentations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent presentations."""
        if not self.conn:
            self.connect()

        assert self.conn is not None
        presentations = self.conn.execute(
            '''
            SELECT
                PresentationId, DateGiven, Title, Content
                FROM Presentations
                WHERE DateGiven > "2024-01-01" AND Title NOT LIKE "INCORRECT%"
                ORDER BY DateGiven DESC
                LIMIT ?
            ;''', (limit,)).fetchall()

        return [
            {
                'id': row[0],
                'date_given': row[1],
                'title': row[2],
                'content': json.loads(row[3])
            }
            for row in presentations
        ]

    def get_virtual_screens(self, presentation_content: dict) -> List[Dict[str, Any]]:
        """Get virtual screens for a presentation."""
        virtual_screens = json.loads(presentation_content.get('VirtualScreens', '[]'))
        return [screen for screen in virtual_screens if screen['outputKind'] in ["Slides", "SlidesAlternateContent"]]

    def get_screen_indices(self, presentation_content: dict) -> tuple[Optional[int], int]:
        """Get greenscreen and translation screen indices."""
        virtual_screens = self.get_virtual_screens(presentation_content)

        greenscreen_screen_idx = next((i for i, screen in enumerate(virtual_screens) if screen['name'] == 'Green Screen'), None)

        # Find translation screen
        translation_screen_idx = [i for i, screen in enumerate(virtual_screens) if any(lang in screen['name'] for lang in ['French', 'Haitian'])]
        if len(translation_screen_idx) != 1:
            raise ValueError(f"Expected one translation screen, found {len(translation_screen_idx)}")

        return greenscreen_screen_idx, translation_screen_idx[0]

    def validate_presentation(self, presentation_id: str) -> PresentationValidation:
        """Validate a single presentation by ID."""
        if not self.conn:
            self.connect()

        assert self.conn is not None
        # Get presentation info
        presentation_row = self.conn.execute(
            '''
            SELECT PresentationId, DateGiven, Title, Content
            FROM Presentations
            WHERE PresentationId = ?
            ''', (presentation_id,)).fetchone()

        if not presentation_row:
            raise ValueError(f"Presentation {presentation_id} not found")

        pres_id, date_given, title, content_json = presentation_row
        presentation_content = json.loads(content_json)

        result = PresentationValidation(
            presentation_id=pres_id,
            title=title,
            date_given=date_given
        )

        try:
            greenscreen_screen_idx, translation_screen_idx = self.get_screen_indices(presentation_content)
        except ValueError as e:
            # If we can't determine screen indices, create a warning item
            error_result = ValidationResult(item_type="Configuration", title="Screen Configuration")
            error_result.add_warning(str(e))
            result.add_item(error_result)
            return result

        # Get all service items for this presentation
        service_items = self.conn.execute(
            '''
            SELECT Title, Content, ServiceItemKind
            FROM ServiceItems
            WHERE PresentationId = ?
            ''', (presentation_id,)).fetchall()

        for item_title, content_json, item_kind in service_items:
            # Skip certain items
            if item_title.lower() in ['blank', 'ncf slide', 'offering slide']:
                continue

            content = json.loads(content_json)

            if item_kind == "SongLyrics":
                item_result = validate_songlyrics_functional(item_title, content)
            elif item_kind == "Content":
                item_result = validate_plaintext_functional(item_title, content, "_richtextfield:Main Content", greenscreen_screen_idx, translation_screen_idx, self.conn)
            elif item_kind == "BiblePassage":
                item_result = validate_biblepassage_functional(item_title, content, greenscreen_screen_idx, translation_screen_idx, self.conn)
            elif item_kind in ["Grouping", "ImageSlideshow"]:
                # Skip these item types
                continue
            else:
                # Unknown item kind
                item_result = ValidationResult(item_type=item_kind, title=item_title)
                item_result.add_warning(f"Unknown item kind: {item_kind}")

            result.add_item(item_result)

        return result


class ValidateProclaimGUI:
    """Tkinter GUI for Proclaim presentation validation."""

    def __init__(self):
        self.validator = ProclaimValidator()
        self.root = tk.Tk()
        self.root.title("Proclaim Presentation Validator")
        self.root.geometry("1000x700")

        self.setup_ui()
        self.presentations = []
        self.current_validation = None

    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top frame for presentation selection and refresh
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Presentation selection
        ttk.Label(top_frame, text="Presentation:").pack(side=tk.LEFT)
        self.presentation_var = tk.StringVar()
        self.presentation_combo = ttk.Combobox(top_frame, textvariable=self.presentation_var, state="readonly", width=50)
        self.presentation_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.presentation_combo.bind('<<ComboboxSelected>>', self.on_presentation_selected)

        # Refresh button
        self.refresh_btn = ttk.Button(top_frame, text="Refresh", command=self.refresh_presentations)
        self.refresh_btn.pack(side=tk.LEFT)

        # Validate button
        self.validate_btn = ttk.Button(top_frame, text="Validate", command=self.validate_selected_presentation)
        self.validate_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(top_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT)

        # Results area
        results_frame = ttk.LabelFrame(main_frame, text="Validation Results")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Create scrolled text widget for results
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, font=('Courier', 10))
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def refresh_presentations(self):
        """Refresh the list of presentations."""
        def refresh_thread():
            try:
                self.root.after(0, lambda: self.set_status("Loading presentations..."))

                # Create a new validator instance for this thread
                thread_validator = ProclaimValidator()
                thread_validator.connect()
                presentations = thread_validator.get_presentations(20)
                thread_validator.disconnect()

                # Update combo box on main thread
                self.root.after(0, lambda: self.update_presentation_combo_with_data(presentations))
            except Exception as e:
                error_msg = f"Error loading presentations: {e}"
                self.root.after(0, lambda: self.set_status(error_msg))
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))

        # Run in background thread
        threading.Thread(target=refresh_thread, daemon=True).start()

    def update_presentation_combo_with_data(self, presentations):
        """Update the presentation combo box with loaded presentations."""
        try:
            self.presentations = presentations
            combo_values = [f"{p['date_given']} - {p['title']}" for p in self.presentations]
            self.presentation_combo['values'] = combo_values
            if combo_values:
                self.presentation_combo.current(0)
            self.set_status(f"Loaded {len(self.presentations)} presentations")
        except Exception as e:
            self.set_status(f"Error updating combo: {e}")

    def on_presentation_selected(self, event=None):
        """Handle presentation selection."""
        pass  # We'll validate on button click instead

    def validate_selected_presentation(self):
        """Validate the currently selected presentation."""
        if not self.presentations:
            messagebox.showwarning("Warning", "No presentations loaded. Please refresh first.")
            return

        selected_index = self.presentation_combo.current()
        if selected_index < 0:
            messagebox.showwarning("Warning", "Please select a presentation.")
            return

        selected_presentation = self.presentations[selected_index]

        def validate_thread():
            try:
                self.root.after(0, lambda: self.set_status("Validating presentation..."))
                self.root.after(0, lambda: self.clear_results())

                # Create a new validator instance for this thread
                thread_validator = ProclaimValidator()
                thread_validator.connect()
                validation_result = thread_validator.validate_presentation(selected_presentation['id'])
                thread_validator.disconnect()

                # Store result and display on main thread
                self.current_validation = validation_result
                self.root.after(0, lambda: self.display_results(validation_result))
                self.root.after(0, lambda: self.set_status("Validation complete"))

            except Exception as e:
                error_msg = f"Error validating presentation: {e}"
                self.root.after(0, lambda: self.set_status(error_msg))
                self.root.after(0, lambda: messagebox.showerror("Validation Error", error_msg))

        # Run validation in background thread
        threading.Thread(target=validate_thread, daemon=True).start()

    def display_results(self, validation: PresentationValidation):
        """Display validation results in the text widget."""
        self.clear_results()

        # Header
        self.append_result(f"Presentation: {validation.title}")
        self.append_result(f"Date: {validation.date_given}")
        self.append_result(f"ID: {validation.presentation_id}")
        self.append_result("=" * 80)

        # Summary
        items_with_issues = validation.get_items_with_issues()
        total_items = len(validation.items)
        self.append_result(f"Total items: {total_items}")
        self.append_result(f"Items with issues: {len(items_with_issues)}")

        if not items_with_issues:
            self.append_result("\n✅ No issues found!")
            return

        self.append_result(f"\n⚠️  Found issues in {len(items_with_issues)} items:")

        # Details for each item with issues
        for item in items_with_issues:
            self.append_result(f"\n--- {item.item_type}: {item.title} ---")

            if item.warnings:
                for warning in item.warnings:
                    self.append_result(f"  ⚠️  {warning}")

            if item.info:
                for info in item.info:
                    self.append_result(f"  ℹ️  {info}")

            if item.prior_matches:
                self.append_result("  📋 Similar prior items:")
                for match in item.prior_matches:
                    self.append_result(f"    • {match['date_given']} - {match['title']} (similarity: {match['ratio']:.2f})")
                    self.append_result(f"      {match['snippet']}")

            if item.debug:
                self.append_result("  🔍 Debug info:")
                for debug in item.debug:
                    self.append_result(f"    {debug}")

    def append_result(self, text: str):
        """Append text to the results area."""
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)

    def clear_results(self):
        """Clear the results area."""
        self.results_text.delete(1.0, tk.END)

    def set_status(self, message: str):
        """Set the status message."""
        self.status_var.set(message)

    def run(self):
        """Start the GUI application."""
        # Load presentations on startup
        self.refresh_presentations()
        self.root.mainloop()


import argparse

# Command line arguments
parser = argparse.ArgumentParser(description='Validate Proclaim presentations.')
parser.add_argument('-i', '--index', type=int, default=0, help='Index of the presentation to validate (default: 0 for most recent)')
parser.add_argument('--gui', action='store_true', help='Launch the GUI instead of CLI validation')
args = parser.parse_args()

if args.gui:
    # Launch GUI
    app = ValidateProclaimGUI()
    app.run()
    exit()


# Connect to the Proclaim database
proclaim_data = Path('~/Library/Application Support/Proclaim/Data/5sos6hqf.xyd/').expanduser()
presentations_db = proclaim_data / 'PresentationManager' / 'PresentationManager.db'

conn = sqlite3.connect(presentations_db)

# Find the most recent presentation
presentations = conn.execute(
    '''
    SELECT
        PresentationId, DateGiven, Title, Content
        FROM Presentations
        WHERE DateGiven > "2024-01-01" AND Title NOT LIKE "INCORRECT%"
        ORDER BY DateGiven DESC
        LIMIT 1 OFFSET ?
    ;''', (args.index,))

most_recent_presentation = presentations.fetchone()
assert most_recent_presentation is not None, "No presentations found after 2024-01-01"

# Get all the items in that presentation
presentation_id = most_recent_presentation[0]
presentation_title = most_recent_presentation[2]
print(f"Validating presentation {presentation_title} ({presentation_id})")
presentation_content = json.loads(most_recent_presentation[3])

def get_virtual_screens():
    virtual_screens = json.loads(presentation_content.get('VirtualScreens', '[]'))
    return [screen for screen in virtual_screens if screen['outputKind'] in ["Slides", "SlidesAlternateContent"]]

greenscreen_screen_idx = next((i for i, screen in enumerate(get_virtual_screens()) if screen['name'] == 'Green Screen'), None)
print(f"Green screen index: {greenscreen_screen_idx}")

def get_idx_of_translations(languages):
    virtual_screens = get_virtual_screens()
    translation_screen_idx = [i for i, screen in enumerate(virtual_screens) if any(lang in screen['name'] for lang in languages)]
    if len(translation_screen_idx) != 1:
        for i, screen in enumerate(virtual_screens):
            print(f"Screen {i}: {screen['name']}")
        raise ValueError(f"Expected one translation screen, found {len(translation_screen_idx)}")
    return translation_screen_idx[0]

translation_screen_idx = get_idx_of_translations(['French', 'Haitian'])
print(f"Translation screen index: {translation_screen_idx}")

service_items = conn.execute(
    '''
    SELECT
        Title, Content, ServiceItemKind
        FROM ServiceItems
        WHERE PresentationId = ?
    ;''', (presentation_id,)).fetchall()


song_item_data = []
for i, (title, content_json, item_kind) in enumerate(service_items):
    print(f"{item_kind}: {title}")
    content = json.loads(content_json)
    if title.lower() in ['blank', 'ncf slide', 'offering slide']:
        continue
    if item_kind == "SongLyrics":
        validate_songlyrics(content)
        song_item_data.append(dict(title=title, **content))
    elif item_kind == "Content":
        validate_plaintext(content, key="_richtextfield:Main Content")
    elif item_kind == "BiblePassage":
        validate_biblepassage(content)
    elif item_kind in ["Grouping", "ImageSlideshow"]:
        continue
    else:
        print(f"Unknown item kind: {item_kind}")
        continue

conn.close()


# Make a table of all of the song lyrics items
#import pandas as pd
#pd.DataFrame(song_item_data).to_csv('song_lyrics.csv', index=False)