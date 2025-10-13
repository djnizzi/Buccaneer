import os
import yt_dlp
import discogs_client
import lyricsgenius
import requests
from mutagen.id3 import ID3, APIC, TOAL, TSRC, TALB, TPE1, TPE2, TIT2, TCON, TDRC, TPUB, TDOR, COMM, TCOM, USLT
from rapidfuzz import fuzz, process
import configparser
import re
import unicodedata
import time
import magic
from PIL import Image
from io import BytesIO
from scripts.regsetup import description

# --- CONFIG ---
config = configparser.ConfigParser()
config.read('secrets.ini')
discogs_api_key = config['API']['key']
appname = config['APP']['appname']
version = config['APP']['version']
FFMPEG_PATH = r"C:\Users\djniz\anaconda3\envs\python3_13\Library\bin"
GENIUS_TOKEN = "YOUR_GENIUS_TOKEN"
OUTPUT_DIR = "downloads"
app = appname + "/" + version

# Init clients
d = discogs_client.Client(app, user_token=discogs_api_key)

# --- DEBUG STUFF ---
def inspect(obj, maxlen=120):
    """
    Pretty-print attributes and values of an object.
    Falls back gracefully if attribute access fails.
    """
    print(f"🔎 Inspecting object of type: {type(obj)}\n")
    for attr in dir(obj):
        if attr.startswith("_"):  # skip private/internal
            continue
        try:
            value = getattr(obj, attr)
            # truncate long values for readability
            val_str = str(value)
            if len(val_str) > maxlen:
                val_str = val_str[:maxlen] + "..."
            print(f"{attr:20} = {val_str}")
        except Exception as e:
            print(f"{attr:20} = <Error: {e}>")

def clean_uploader(uploader: str) -> str:
    """Strip ' - Topic' suffix from YouTube uploader names."""
    if not uploader:
        return ""
    # Remove ' - Topic' (case-insensitive, strip trailing whitespace)
    return re.sub(r"\s*-\s*Topic$", "", uploader, flags=re.IGNORECASE).strip()

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

# --- YT description ---
def parse_youtube_description(description: str):
    data = {}

    # ℗ year + publisher
    m = re.search(r"℗\s*(\d{4})?\s*(.+)", description)
    if m:
        if m.group(1):  # year exists
            data["year"] = m.group(1)
        new_publisher = m.group(2).strip()
        if "publisher" in data:
            if new_publisher != data["publisher"]:
                data["publisher"] = f"{data['publisher']}; {new_publisher}"
        else:
            data["publisher"] = new_publisher

    # Publisher/label line
    m = re.search(r"Provided to YouTube by (.+)", description, re.IGNORECASE)
    if m:
        new_publisher = m.group(1).strip()
        if "publisher" in data:
            if new_publisher != data["publisher"]:
                data["publisher"] = f"{data['publisher']}; {new_publisher}"
        else:
            data["publisher"] = new_publisher

    # Title + artist line (split by "·")
    m = re.search(r"(.+?) · (.+)", description)
    if m:
        data["title"] = m.group(1).strip()
        normalized_uploader = m.group(2).replace(" · ", "; ")
        data["uploader"] = normalized_uploader.strip()

    # Released on: YYYY-MM-DD
    m = re.search(r"Released on:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", description, re.IGNORECASE)
    if m:
        data["upload_date"] = m.group(1)  # exact release date

    # Composer(s) — can appear multiple times
    composers = re.findall(r"Composer:\s*(.+)", description, re.IGNORECASE)
    if composers:
        # Join multiple composers with "; " (like Discogs style)
        data["composer"] = "; ".join(c.strip() for c in composers)

    # Lyrics: everything after "lyrics:"
    m = re.search(r"lyrics[:\-\n]+(.+)", description, re.IGNORECASE | re.DOTALL)
    if m:
        data["lyrics"] = m.group(1).strip()

    return data

# --- YT metadata ---
def get_yt_metadata(url: str):
    ydl_opts = {"skip_download": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ytinfo = ydl.extract_info(url, download=False)
        description = ytinfo.get("description", "")
        upload_date = ytinfo.get("upload_date")
        if upload_date:
            ytinfo["upload_date"] = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        parsed = parse_youtube_description(description)

        # Merge parsed info into yt_dlp info (parsed values overwrite if duplicated)
        combined = {**ytinfo, **parsed}

        return combined

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

            # Detect MIME type
            mime_type = magic.from_buffer(img_data, mime=True)

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

# --- tag from YT ---
def tag_from_yt(filepath: str, url: str):
    info = get_yt_metadata(url)
    id3 = ID3(filepath)

    artist, song = normalize_yt_title(info)
    upload_date = info.get("upload_date")  # YYYY-MM-DD

    album_artist = merge_feat(artist)

    # Title + Artist
    id3.add(TIT2(encoding=3, text=song))
    id3.add(TPE1(encoding=3, text=artist))
    id3.add(TPE2(encoding=3, text=album_artist))
    id3.add(TALB(encoding=3, text=f"{song} [Single]"))

    # Release date (TDOR) & year (TDRC)
    if upload_date:
        id3.add(TDOR(encoding=3, text=f"{upload_date}"))
        id3.add(TDRC(encoding=3, text=f"{upload_date[0:4]}"))
    # overwrite with year if present
    if "year" in info:
        id3.add(TDRC(encoding=3, lang="eng", desc="", text=info["year"]))

    # Save lyrics if present
    if "lyrics" in info:
        id3.add(USLT(encoding=3, lang="eng", desc="", text=info["lyrics"]))

    # Save composer if present
    if "composer" in info:
        id3.add(TCOM(encoding=3, lang="eng", desc="", text=info["composer"]))

    # Save publisher if present
    if "publisher" in info:
        id3.add(TPUB(encoding=3, lang="eng", desc="", text=info["publisher"]))

    # Save description if present
    if "description" in info:
        id3.add(COMM(encoding=3, lang="eng", desc="", text=info["description"]))

    # Cover art
    cover_data, mime_type = fetch_and_crop_cover(info.get("thumbnails", []))
    if cover_data:
        id3.add(APIC(
            encoding=3,
            mime=mime_type or "image/jpeg",
            type=3,
            desc="Cover",
            data=cover_data
        ))
        print("🖼️ Added cropped YouTube thumbnail as cover")
    else:
        print("⚠️ No valid thumbnail to add as cover, skipping")

    id3.save(v2_version=3)
    print(f"✅ Tagged {filepath} with YouTube metadata")

# --- Search Discogs ---
def search_discogs(query: str, max_results: int = 15, top_n: int = 5):
    print(f"🔍 Searching Discogs with query: {query}")


    results = d.search(query, type="release")

    if not results:
            print(f"⚠️ No Discogs results for query: {query}")
            return None

    # results_list = list(results)[:max_results]
    #
    # # Print info for each release
    # for i, r in enumerate(results_list, start=1):
    #     artist_names = []
    #     for a in getattr(r, "artists", []):
    #         if isinstance(a, dict):
    #             artist_names.append(a.get("name", "Unknown"))
    #         else:
    #             artist_names.append(getattr(a, "name", "Unknown"))
    #     artists_str = ", ".join(artist_names)
    #
    #     print(f"{i}. {artists_str} - {r.title} ({getattr(r, 'year', 'Unknown')}) | ID: {r.id}")

    # Build candidate list with deduplication
    candidates = []
    seen_ids = set()
    for i, r in enumerate(results):
        if i >= max_results:
            break
        if r.id in seen_ids:
            continue
        seen_ids.add(r.id)
        artist_names = []
        for a in getattr(r, "artists", []):
            if isinstance(a, dict):
                artist_names.append(a.get("name", "Unknown"))
            else:
                artist_names.append(getattr(a, "name", "Unknown"))
        artist_names = ", ".join(artist_names)

        candidate_title = f"{artist_names} - {r.title}"
        candidates.append((candidate_title, r))

    if not candidates:
        print("⚠️ No unique candidates found")
        return None

        # Compute fuzzy scores
    scored = []
    for title, release in candidates:
        score = fuzz.token_sort_ratio(query, title)
        scored.append((score, title, release))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Display top matches with details
    n_display = min(top_n, len(scored))
    print("\nTop matches:")
    for idx in range(n_display):
        score, title, release = scored[idx]

        try:
            # fetch full release details
            full_release = d.release(release.id)
        except Exception as e:
            print(f"⚠️ Could not fetch full release {release.id}: {e}")
            continue

        # Labels
        labels_list = []
        for l in getattr(full_release, "labels", []):
              if isinstance(l, dict):
                labels_list.append(l.get("name", "Unknown"))
              else:
                labels_list.append(getattr(l, "name", "Unknown"))
        labels = ", ".join(labels_list)

        # Formats
        formats_list = []
        for f in getattr(full_release, "formats", []):
            fmt_name = getattr(f, "name", f.get("name", "Unknown") if isinstance(f, dict) else "Unknown")
            descs = getattr(f, "descriptions", f.get("descriptions", []) if isinstance(f, dict) else [])
            formats_list.append(f"{fmt_name} ({', '.join(descs)})" if descs else fmt_name)
        formats = ", ".join(formats_list)

        country = getattr(full_release, "country", "Unknown")
        released = (
                getattr(full_release, "released", None)
                or full_release.data.get("released")
                or full_release.data.get("released_formatted")
        )
        if not released and getattr(full_release, "master_id", None):
            try:
                master = d.master(full_release.master_id)
                released = getattr(master, "released", None)
            except Exception:
                pass

        # Step 3: fallback to year
        if not released:
            released = str(getattr(full_release, "year", "Unknown"))

        print(f"{idx + 1}. {title}, {released}, {labels}, {country}, {formats} - {score:.2f}%")

    # Skip choice if only one release
    # if len(scored) == 1:
    #     selected_release = scored[0][2]
    #     print(f"✅ Only one match, automatically selected: {scored[0][1]}")
    #     return selected_release

    # Otherwise ask user
    while True:
        choice = input(f"Choose a release [1-{min(top_n, len(scored))}] or 0 to skip: ")
        if choice.isdigit():
            choice = int(choice)
            if 0 <= choice <= min(top_n, len(scored)):
                break
        print("Invalid input, try again.")

    if choice == 0:
        print("Skipped.")
        return None

    selected_release = scored[choice - 1][2]
    print(f"✅ You selected: {scored[choice - 1][1]}")
    return selected_release

def clean_discogs_artist(name: str) -> str:
    """Remove Discogs' (N) suffix from artist names."""
    return re.sub(r"\s*\(\d+\)$", "", name).strip()

# --- Tag MP3 with Discogs Metadata ---
def tag_mp3_with_discogs(file: str, release):
    """Tag an MP3 file with Discogs metadata, cover art, URL, and catalog/ISRC."""
    if not release:
        print(f"⚠️ No release provided for tagging {file}")
        return
    filepath = OUTPUT_DIR + f"/{file}"
    try:
        id3 = ID3(filepath)
    except Exception:
          id3 = ID3()

    # --- Core tags ---
    try:
        artists = [clean_discogs_artist(a.name if not isinstance(a, dict) else a.get("name", "Unknown Artist"))
                   for a in getattr(release, "artists", [])]
        # Join them with "; "
        artists_str = "; ".join(artists) if artists else "Unknown Artist"
        title = getattr(release, "title", "Unknown Title")
        album = getattr(release, "title", "Unknown Album")
        formats = getattr(release, "formats", [])
        is_single = False
        is_ep = False

        for fmt in formats:
            # Check format name (e.g. "CD", "File") and descriptions (e.g. "Single", "AAC")
            if "name" in fmt and "single" in fmt["name"].lower():
                is_single = True
                break
            if "descriptions" in fmt and any("single" in d.lower() for d in fmt["descriptions"]):
                is_single = True
                break
            if "name" in fmt and "ep" in fmt["name"].lower():
                is_ep = True
                break
            if "descriptions" in fmt and any("ep" in d.lower() for d in fmt["descriptions"]):
                is_ep = True
                break

        if is_single:
            album += " [Single]"
            id3.add(TPE1(encoding=3, text=artists_str if artists else "Unknown Artist"))  # Lead artist
        if is_ep:
            album += " [EP]"
        genres = list(getattr(release, "genres", []))
        year = getattr(release, "year", None)
        released = (
                getattr(release, "released", None)
                or release.data.get("released")
                or release.data.get("released_formatted")
        )
        id3.add(TPE2(encoding=3, text=artists_str if artists else "Unknown Artist"))  # Album artist
        #id3.add(TIT2(encoding=3, text=title))
        id3.add(TALB(encoding=3, text=album))
        if genres:
            id3.add(TCON(encoding=3, text=genres[0]))
        if year:
            id3.add(TDRC(encoding=3, text=str(year)))
        if released:
            id3.add(TDOR(encoding=3, text=str(released)))

        print(f"✅ Tagged basic metadata for {filepath} " + released)
    except Exception as e:
        print(f"❌ Error tagging basic metadata: {e}")

    # --- Extended / custom tags ---
    try:
        # Labels / publisher
        labels = [l.name if not isinstance(l, dict) else l.get("name", "Unknown")
                  for l in getattr(release, "labels", [])]
        if labels:
            id3.add(TPUB(encoding=3, desc="Publisher", text="; ".join(labels)))

        # Discogs URL (use master URL if available)
        discogs_url = getattr(getattr(release, "master", release), "url", getattr(release, "url", None))
        if discogs_url:
            id3.add(TOAL(encoding=3, desc="DiscogsURL", text=discogs_url))

        # Catalog number (from first label)
        catno = None
        if getattr(release, "labels", []):
            label = release.labels[0]
            if isinstance(label, dict):
                catno = label.get("catno")
            else:
                catno = getattr(label, "catno", None)
        if catno:
            id3.add(TSRC(encoding=3, desc="CatalogNumber", text=catno))

        # Cover image
        if hasattr(release, "images") and release.images:
            img_url = release.images[0].get("resource_url")  # use resource_url
            if img_url:
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/116.0.0.0 Safari/537.36"
                    }
                    response = requests.get(img_url, headers=headers)
                    if response.headers.get("content-type", "").startswith("image/"):
                        img_data = response.content
                        mime_type = response.headers["content-type"]

                        id3.add(APIC(
                            encoding=3,
                            mime=mime_type,
                            type=3,  # Cover (front)
                            desc="Cover",
                            data=img_data
                        ))
                        print("🖼️ Added cover art ")
                except Exception as e:
                    print(f"⚠️ Could not fetch cover art: {e}")

        id3.save(v2_version=3)
        print(f"✅ Saved all ID3v2 tags for {filepath}")

    except Exception as e:
        print(f"❌ Error adding extended tags: {e}")

def safe_filename(name: str, replacement: str = "") -> str:
    # Forbidden characters in Windows + macOS
    forbidden = r'[\\/:*?"<>|]'
    return re.sub(forbidden, replacement, name).strip()

def strip_feat(title: str) -> str:

    # (feat. X) → X
    title = re.sub(r"\(\s*(feat\.?|ft\.?)\s*([^)]+)\)", r"\2", title, flags=re.IGNORECASE)

    # feat. X → X  (when not inside parentheses)
    title = re.sub(r"\b(feat\.?|ft\.)\s+([^-\[\]()]+)", r"\2", title, flags=re.IGNORECASE)

    return " ".join(title.split()).strip()

def search_discogs_with_prompt(query: str, max_results: int = 30, top_n: int = 5):
    # Strip feat./ft. for Discogs search
    cleaned_query = strip_feat(query)

    # Ask user if they want to proceed with the cleaned query
    print(f"\n🔍 Proposed Discogs query: \"{cleaned_query}\" (from \"{query}\")")
    choice = input("Press [Enter] to search, or type a custom query (or 0 to skip): ").strip()

    if choice == "0":
        print("⏭️ Skipping Discogs search.")
        return None
    elif choice:
        cleaned_query = choice  # user override

    # Continue with normal search
    return search_discogs(cleaned_query, max_results=max_results, top_n=top_n)

# --- Download Playlist ---
def download_playlist(playlist_url: str) -> list:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []

    # use video ID as temporary filename (avoids clashes & illegal chars)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128"
        }],
        "ffmpeg_location": FFMPEG_PATH,
        "ignoreerrors": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get("entries", [])

        for entry in entries:
            if not entry:
                print("⚠️ Skipping unavailable video (entry is None)")
                continue

            video_url = entry.get("webpage_url")
            if not video_url:
                continue

            # Download this entry only
            try:
                ydl.download([video_url])
            except Exception as e:
                print(f"⚠️ Failed to download {entry.get('title')}: {e}")
                continue

            artist, song = normalize_yt_title(entry)
            if not song:
                print("⚠️ Skipping entry without title")
                continue

            artist = clean_feat(artist)

            # build final polished filename
            safe_title = safe_filename(f"{artist} - {song}")
            safe_title = clean_title(safe_title)
            final_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp3")

            # temp file path from yt-dlp
            temp_path = os.path.join(OUTPUT_DIR, f"{entry['id']}.mp3")

            if os.path.exists(temp_path):
                try:
                    os.rename(temp_path, final_path)
                    print(f"✅ Saved as {safe_title}.mp3")

                    # Tag with YouTube metadata
                    tag_from_yt(final_path, entry["webpage_url"])
                    results.append({"title": safe_title, "file": final_path})
                except Exception as e:
                    print(f"⚠️ Failed to process {entry.get('title')}: {e}")
                release = search_discogs_with_prompt(safe_title)
                if release:
                    tag_mp3_with_discogs(f"{safe_title}.mp3", release)
                else:
                    print("No release selected. Skipping tagging.")
            else:
                print(f"⚠️ File not found after download: {entry.get('title')}")

    return results


# Init clients
genius = lyricsgenius.Genius(GENIUS_TOKEN)
# --- STEP 4: Fetch Lyrics from Genius ---
def fetch_and_add_lyrics(filepath: str, artist: str, title: str):
    """Fetch lyrics from Genius and add them to MP3 tags."""
    try:
        song = genius.search_song(title, artist)
        if song:
            id3 = ID3(filepath)
            id3.add(
                USLT(encoding=3, lang='eng', desc='Lyrics', text=song.lyrics)
            )
            id3.save(v2_version=3)
    except Exception as e:
        print(f"Lyrics fetch failed for {artist} - {title}: {e}")

# --- MAIN DRIVER ---
def process_playlist(playlist_url: str):
    """Full pipeline: download, search metadata, tag, add lyrics."""
    entries = download_playlist(playlist_url)
    for entry in entries:
        title, filepath = entry["title"], entry["file"]
        print(f"\nProcessing: {title}")
        release = search_discogs(title)
        if release:
            print(f"Matched with Discogs: {release.title} - {release.artists[0].name}")
            tag_mp3_with_discogs(filepath, release)
            fetch_and_add_lyrics(filepath, release.artists[0].name, release.title)
        else:
            print(f"No Discogs match for {title}")