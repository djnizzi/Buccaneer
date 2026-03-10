#!/usr/bin/env python3
"""
CLI tool to scan and display ID3 tags from MP3 files.
Prompts for a path to an MP3 file and prints all ID3 tags in table format.
"""

import sys
from pathlib import Path

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
except ImportError:
    print("Error: mutagen library is required. Install with: pip install mutagen")
    sys.exit(1)


def get_frame_name(frame_id: str) -> str:
    """Map ID3 frame IDs to human-readable names."""
    # Extract base frame ID (before any colon)
    base_frame = frame_id.split(':')[0] if ':' in frame_id else frame_id
    
    frame_names = {
        # Common frames
        'TIT2': 'Title',
        'TPE1': 'Artist',
        'TPE2': 'Album Artist',
        'TPE3': 'Composer',
        'TPE4': 'Remixer',
        'TALB': 'Album',
        'TRCK': 'Track Number',
        'TPOS': 'Part of Set',
        'TYER': 'Year',
        'TDRC': 'Recording Time',
        'TDRL': 'Release Time',
        'TDOR': 'Original Release Time',
        'TCON': 'Genre',
        'TCOM': 'Composer',
        'TEXT': 'Lyricist',
        'TOLY': 'Lyricist',
        'TOWN': 'File Owner',
        'TCMP': 'Part of Compilation',
        'TCAT': 'Category',
        'TCOP': 'Copyright',
        'TPRO': 'Produced',
        'TPUB': 'Publisher',
        'TRSN': 'Internet Radio Station Name',
        'TRSO': 'Internet Radio Station Owner',
        'TSRC': 'ISRC',
        'TSSE': 'Encoder Settings',
        'TXXX': 'User Defined Text',
        # Comment frames
        'COMM': 'Comment',
        # Picture frames
        'APIC': 'Cover Art',
        'PIC': 'Cover Art (Old)',
        # Other frames
        'UFID': 'Unique File Identifier',
        'USER': 'Terms of Use',
        'OWNE': 'Ownership',
        'COMR': 'Commercial Frame',
        'ENCR': 'Encryption Method',
        'GRID': 'Group Identification',
        'LINK': 'Linked Information',
        'POSS': 'Position Synchronization',
        'SYLT': 'Synchronized Lyrics',
        'SYTC': 'Synchronized Tempo Codes',
        'RVRB': 'Reverb',
        'VOL': 'Volume Adjustment',
        'AENC': 'Audio Encryption',
        # Popularimeter
        'POPM': 'Popularimeter',
        # Unsynchronized lyrics
        'USLT': 'Unsynchronized Lyrics',
        # Official chunks
        'CHAP': 'Chapter',
        'CTOC': 'Table of Contents',
        # Unknown
        'UNKNOWN': 'Unknown Frame',
    }
    
    # Return mapped name or the base frame ID
    return frame_names.get(base_frame, base_frame)


def format_value(value) -> str:
    """Format the tag value for display."""
    if value is None:
        return ''
    
    if hasattr(value, 'text'):
        # For text frames
        text = value.text[0] if value.text else ''
        return str(text)
    elif hasattr(value, 'data'):
        # For binary data frames like APIC
        if hasattr(value, 'desc'):
            return f"[Binary Data: {value.desc}]"
        return "[Binary Data]"
    else:
        return str(value)


def scan_mp3_tags(file_path: str) -> None:
    """Scan and display ID3 tags from an MP3 file."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    if not path.is_file():
        print(f"Error: Not a file: {file_path}")
        sys.exit(1)
    
    try:
        audio = MP3(str(path))
    except Exception as e:
        print(f"Error: Could not read MP3 file: {e}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"MP3 Tag Scanner")
    print(f"{'='*60}")
    print(f"File: {path.name}")
    print(f"Path: {path.absolute()}")
    print(f"{'='*60}\n")
    
    # Check if file has ID3 tags
    if audio.tags is None:
        print("No ID3 tags found in this file.")
        return
    
    # Collect all tags
    tags = []
    
    # Iterate through all tags
    for frame_id, frame in audio.tags.items():
        frame_name = get_frame_name(str(frame_id))
        value = format_value(frame)
        tags.append((frame_id, frame_name, value))
    
    # Sort by frame ID
    tags.sort(key=lambda x: x[0])
    
    if not tags:
        print("No ID3 tags found in this file.")
        return
    
    # Print table header
    print(f"{'Frame ID':<10} {'Frame Name':<30} {'Value':<50}")
    print("-" * 90)
    
    # Print each tag
    for frame_id, frame_name, value in tags:
        # Truncate value if too long
        display_value = value[:47] + "..." if len(value) > 50 else value
        print(f"{frame_id:<10} {frame_name:<30} {display_value:<50}")
    
    print("-" * 90)
    print(f"Total tags found: {len(tags)}")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Use command line argument if provided
        file_path = sys.argv[1]
    else:
        # Prompt for file path
        file_path = input("Enter path to MP3 file: ").strip()
    
    if not file_path:
        print("Error: No file path provided.")
        sys.exit(1)
    
    scan_mp3_tags(file_path)


if __name__ == "__main__":
    main()
