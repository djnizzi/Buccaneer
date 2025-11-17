import os
import re
import chardet

PROCESSED_LOG = "processed_log.txt"
CHECK_LOG = "check_that_dir.txt"


def load_processed():
    if not os.path.exists(PROCESSED_LOG):
        return set()
    with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_processed(path):
    with open(PROCESSED_LOG, "a", encoding="utf-8") as f:
        f.write(path + "\n")


def detect_encoding(path):
    with open(path, "rb") as f:
        raw = f.read()
    det = chardet.detect(raw)
    encoding = det["encoding"] or "utf-8"
    return raw, encoding


def split_header(text):
    """Split text into header and body at first TRACK."""
    track_pos = text.find("TRACK ")
    if track_pos == -1:
        return text, ""
    return text[:track_pos], text[track_pos:]

def parse_path(cue_path):
    folder = os.path.dirname(cue_path)
    parts = folder.split(os.sep)

    # We scan the path from right to left to find the album folder
    album_folder = None
    performer2 = None
    title = None

    album_regex_with_p2 = re.compile(r'^(.*?) - \((\d{4})\) (.*)$')
    album_regex_no_p2  = re.compile(r'^\((\d{4})\) (.*)$')

    # Walk backwards to find album folder
    for part in reversed(parts):
        m1 = album_regex_with_p2.match(part)
        m2 = album_regex_no_p2.match(part)

        if m1:
            performer2 = m1.group(1).strip()
            title = m1.group(3).strip()
            album_folder = part
            break

        if m2:
            title = m2.group(2).strip()
            album_folder = part
            break

    if not album_folder:
        return None, None  # cannot parse path

    # Now find PERFORMER = the folder BEFORE the album folder
    try:
        album_index = parts.index(album_folder)
        performer = parts[album_index - 1]
    except Exception:
        return None, None

    # Build final PERFORMER field
    if performer2:
        performer = performer + "; " + performer2

    return performer, title

import os
import re

def parse_path_vvaa(cue_path):
    """
    Handles VVAA albums with nested category folders.
    Extracts album artist='VVAA' and album title from folder:
      VVAA - (YEAR) TITLE
    """
    cue_path = os.path.normpath(cue_path)
    parts = cue_path.split(os.sep)

    idx = [p.lower() for p in parts].index("vvaa")

    # All folders after \VVAA are candidates
    subfolders = parts[idx + 1 :]

    # Find the first folder that matches VVAA - (YEAR) TITLE
    for folder in subfolders:
        m = re.match(r'^VVAA\s*-\s*\((\d{4})\)\s*(.+)$', folder, flags=re.IGNORECASE)
        if m:
            title = m.group(2).strip()
            return {
                "performer": "VVAA",
                "title": title,
            }

    # No matching folder → invalid
    return None


def extract_album_fields(header):
    """Get album PERFORMER and TITLE only (first ones before TRACK)."""
    performer = ""
    title = ""

    p = re.search(r'^\s*PERFORMER\s+"([^"]*)"\s*$', header, re.MULTILINE)
    if p: performer = p.group(1)

    t = re.search(r'^\s*TITLE\s+"([^"]*)"\s*$', header, re.MULTILINE)
    if t: title = t.group(1)

    return performer, title


def replace_album_field(header, field_name, new_value):
    """
    Safely replace album PERFORMER or TITLE without breaking on backslashes.
    """
    pattern = rf'^({field_name}\s+")([^"]*)(")$'

    def repl(match):
        return f'{match.group(1)}{new_value}{match.group(3)}'

    return re.sub(pattern, repl, header, count=1, flags=re.MULTILINE)



def replace_album_file(header, new_filename):
    pattern = r'^(FILE\s+")([^"]*)(".*)$'

    def repl(match):
        return f'{match.group(1)}{new_filename}{match.group(3)}'

    return re.sub(pattern, repl, header, count=1, flags=re.MULTILINE)


def process_cue(cue_path):
    processed = load_processed()
    if cue_path in processed:
        print(f"Skipping already processed: {cue_path}")
        return


    # Detect encoding and read raw text safely
    print(f"Processing {cue_path}")
    raw, encoding = detect_encoding(cue_path)
    text = raw.decode(encoding, errors="replace")

    folder = os.path.dirname(cue_path)
    mp3s = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]

    # If multiple mp3s → log and skip
    if len(mp3s) != 1:
        with open(CHECK_LOG, "a", encoding="utf-8") as f:
            f.write(folder + "\n")
        save_processed(cue_path)
        print(f"Multiple mp3 files → logged: {folder}")
        return

    mp3_filename = mp3s[0]
    if os.path.normpath(cue_path).lower().startswith(r"x:\albums\vvaa".lower()):
        album_performer, album_title = parse_path_vvaa(cue_path)
    else:
        album_performer, album_title = parse_path(cue_path)
    if not album_performer or not album_title:
        save_processed(cue_path)
        return

    header, body = split_header(text)

    # Detect current album fields
    performer_match = re.search(r'^\s*PERFORMER\s+"([^"]*)"', header, re.MULTILINE)
    title_match = re.search(r'^\s*TITLE\s+"([^"]*)"', header, re.MULTILINE)

    current_performer = performer_match.group(1) if performer_match else ""
    current_title = title_match.group(1) if title_match else ""

    # Detect if changes are needed
    performer_changed = album_performer != current_performer
    title_changed = album_title != current_title
    file_match = re.search(r'FILE\s+"([^"]*)"', header)
    filename_changed = file_match and file_match.group(1) != mp3_filename

    if not (performer_changed or title_changed or filename_changed):
        save_processed(cue_path)
        return

    # Backup original
    bak_path = cue_path + ".bak"
    if not os.path.exists(bak_path):
        with open(bak_path, "wb") as bf:
            bf.write(raw)

    # Apply replacements
    if performer_changed:
        header = replace_album_field(header, "PERFORMER", album_performer)
    if title_changed:
        header = replace_album_field(header, "TITLE", album_title)
    if filename_changed:
        header = replace_album_file(header, mp3_filename)

    text = header + body

    # Write back using original encoding
    with open(cue_path, "wb") as f:
        f.write(text.encode(encoding, errors="replace"))

    save_processed(cue_path)
    print(f"Processed: {cue_path}\n")


def main():
    root = input("Enter folder to scan recursively: ").strip()
    if not os.path.isdir(root):
        print("Invalid folder.")
        return

    for path, dirs, files in os.walk(root):
        for file in files:

            if file.lower().endswith(".cue"):
                full = os.path.join(path, file)
                process_cue(full)


if __name__ == "__main__":
    main()


