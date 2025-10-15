import re
import unicodedata
import requests
from PIL import Image
from io import BytesIO

def clean_feat(artist: str) -> str:
    m = re.search(r"\(\s*(feat\.?|ft\.?)\s+([^)]+)\)", artist, flags=re.IGNORECASE)
    if m:
        # Normalize to "feat. ..."
        feat_part = f"feat. {m.group(2).strip()}"
        # Remove from artist
        artist = re.sub(r"\(\s*(feat\.?|ft\.?)\s+([^)]+)\)", "", artist, flags=re.IGNORECASE).strip()
        # Append to artist
        artist = f"{artist.strip()} {feat_part}"
    return artist

def strip_feat(title: str) -> str:

    # (feat. X) → X
    title = re.sub(r"\(\s*(feat\.?|ft\.?)\s*([^)]+)\)", r"\2", title, flags=re.IGNORECASE)

    # feat. X → X  (when not inside parentheses)
    title = re.sub(r"\b(feat\.?|ft\.)\s+([^-\[\]()]+)", r"\2", title, flags=re.IGNORECASE)

    return " ".join(title.split()).strip()

def clean_uploader(uploader: str) -> str:
    """Strip ' - Topic' suffix from YouTube uploader names."""
    if not uploader:
        return ""
    # Remove ' - Topic' (case-insensitive, strip trailing whitespace)
    return re.sub(r"\s*-\s*Topic$", "", uploader, flags=re.IGNORECASE).strip()

def clean_discogs_artist(name: str) -> str:
    """Remove Discogs' (N) suffix from artist names."""
    return re.sub(r"\s*\(\d+\)$", "", name).strip()

def merge_feat(artist: str) -> str:
    # Detect "feat." or "ft." followed by featured artists
    m = re.search(r"\b(?:feat|ft)\.?\s+(.+)", artist, re.IGNORECASE)
    if m:
        featured = m.group(1).strip()
        # Strip everything after 'feat' from the base artist
        base_artist = re.sub(r"\b(?:feat|ft)\.?\s+.+", "", artist, flags=re.IGNORECASE).strip()
        return f"{base_artist}; {featured}"
    return artist

# --- Normalize YT title ---
def normalize_yt_title(info: dict) -> tuple[str, str]:
    """
    Returns (artist, title) based on YouTube title patterns.
    Patterns handled:
      1. 'Artist - Song' → use Artist and clean_title(Song)
         - also merges (feat./ft.) artists into Artist
      2. 'Song' only → use uploader + clean_title(Song)
    """
    raw_title = info.get("title", "").strip()
    uploader = clean_uploader(info.get("uploader", "Unknown Artist"))

    if " - " in raw_title:
        artist, song = raw_title.split(" - ", 1)
        artist = artist.strip()
        song = song.strip()

        artist = clean_feat(artist)

        # Detect and merge featured artists
        m = re.search(r"\((?:feat\.|ft\.)\s*(.+?)\)", song, re.IGNORECASE)
        if m:
        #    featured = m.group(1).strip()
        #    artist = f"{artist}; {featured}"
            # remove (feat. ...) from song
            song = re.sub(r"\((?:feat\.|ft\.).*?\)", "", song, flags=re.IGNORECASE).strip()
        song = clean_title(song)
    else:
        # Pattern 2: fallback, no artist in title
        artist = uploader.strip()
        song = clean_title(raw_title)

    return artist, song

# --- clean_title ---
def clean_title(title: str) -> str:
    """
    Clean YouTube video titles to improve Discogs/Genius matching.
    Removes common noise like (Official Video), [HD], etc.,
    but preserves meaningful info like 'remix' or 'feat'.
    """
    # Normalize accents / smart quotes
    title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("utf-8")

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002500-\U00002BEF"  # chinese characters
        "\U00002702-\U000027B0"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+", flags=re.UNICODE)
    title = emoji_pattern.sub(r'', title)

    noise_words = [
        "official video", "official music video", "official audio", "letra/lyrics",
        "lyrics", "hd", "remastered", "full album", "mv",
        "official lyrics", "official lyric video", "official visualizer",
        "original mix", "extended mix", "letra", "lyric video", "melodic, progressive house",
        "lyric visualizer", "visualizer", "audio"
    ]

    # Build a single regex pattern
    escaped_words = [re.escape(word) for word in noise_words]
    pattern = re.compile(
        r"\(\s*(" + "|".join(escaped_words) + r")\s*\)"
        + r"|\[\s*(" + "|".join(escaped_words) + r")\s*]"
        + r"|\b(" + "|".join(escaped_words) + r")\b",
        flags=re.IGNORECASE
    )

    # Apply to title
    title = pattern.sub("", title)
    # Clean extra spaces
    title = re.sub(r"\s{2,}", " ", title).strip()


    if " - " not in title:
        return title  # nothing to do
    artist, song = title.split(" - ", 1)

    # Look for "(feat ...)" in song
    m = re.search(r"\(\s*(feat\.?|ft\.?)\s+([^)]+)\)", song, flags=re.IGNORECASE)
    if m:
        # Normalize to "feat. ..."
        feat_part = f"feat. {m.group(2).strip()}"
        # Remove from song
        song = re.sub(r"\(\s*(feat\.?|ft\.?)\s+([^)]+)\)", "", song, flags=re.IGNORECASE).strip()
        # Append to artist
        artist = f"{artist.strip()} {feat_part}"

    # Clean spaces
    artist = re.sub(r"\s+", " ", artist).strip()
    song = re.sub(r"\s+", " ", song).strip()
    title = f"{artist} - {song}"

    # Cleanup spacing/punctuation
    title = re.sub(r"\s{2,}", " ", title)    # collapse multiple spaces
    title = re.sub(r"[–—_]+", "-", title)    # normalize dashes
    title = title.strip(" -")                # strip trailing junk

    return title.strip()

# --- fetch & crop cover ---
def fetch_and_crop_cover(thumbnails):
    if not thumbnails:
        return None, None

    for thumb in reversed(thumbnails):  # try highest quality first
        url = thumb.get("url")
        if not url:
            continue

        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            img_data = resp.content
            if not img_data or not isinstance(img_data, (bytes, bytearray)):
                continue

            # Central square crop
            img = Image.open(BytesIO(img_data))
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            img = img.resize((720, 720))

            out = BytesIO()
            img.save(out, format="JPEG")
            return out.getvalue(), "image/jpeg"

        except requests.RequestException:
            print(f"⚠️ Failed to fetch thumbnail: {url}")
        except Exception as e:
            print(f"⚠️ Failed to process thumbnail {url}: {e}")

    print("⚠️ No valid thumbnails found")
    return None, None

def safe_filename(name: str, replacement: str = "") -> str:
    # Forbidden characters in Windows + macOS
    forbidden = r'[\\/:*?"<>|]'
    return re.sub(forbidden, replacement, name).strip()

def flip_query(query: str) -> str:
    """Turn 'Artist - Title' into 'Title - Artist' if pattern matches."""
    if " - " in query:
        left, right = query.split(" - ", 1)
        return f"{right.strip()} - {left.strip()}"

def keep_main(title: str) -> str:
    title = re.sub(r"\b(feat\.?|ft\.).*", "", title, flags=re.IGNORECASE)

    return title.strip()