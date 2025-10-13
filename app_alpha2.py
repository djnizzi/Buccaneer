import os
import yt_dlp
import discogs_client
import lyricsgenius
import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, USLT
from rapidfuzz import fuzz, process

# --- CONFIG ---
DISCOGS_TOKEN = "YOUR_DISCOGS_TOKEN"
GENIUS_TOKEN = "YOUR_GENIUS_TOKEN"
OUTPUT_DIR = "downloads"
APP_NAME = "YTM2MP3"
APP_VERSION = "1.0"
APP = APP_NAME + "/" + APP_VERSION

# --- STEP 1: Download Playlist ---
def download_playlist(playlist_url: str) -> list:
    """Download YouTube playlist as MP3 and return list of file paths + titles."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=True)
        entries = info.get("entries", [])
        results = []
        for entry in entries:
            if entry:
                filename = os.path.join(OUTPUT_DIR, f"{entry['title']}.mp3")
                results.append({"title": entry['title'], "file": filename})
        return results

# Init clients
d = discogs_client.Client(APP, user_token=DISCOGS_TOKEN)
genius = lyricsgenius.Genius(GENIUS_TOKEN)

# --- STEP 2: Search Discogs ---
def search_discogs(query: str):
    """Search Discogs for a release matching query."""
    try:
        results = d.search(query, type='release')
        if results:
            return results[0]  # TODO: later improve with fuzzy match
    except Exception as e:
        print("Discogs error:", e)
    return None

# --- STEP 3: Tag MP3 with Discogs Metadata ---
def tag_mp3_with_discogs(filepath: str, release):
    """Tag an MP3 file with Discogs metadata (artist, album, etc)."""
    try:
        audio = EasyID3(filepath)
    except Exception:
        audio = EasyID3()

    if release:
        audio["artist"] = release.artists[0].name
        audio["title"] = release.title
        audio["album"] = release.title
        audio["albumartist"] = release.artists[0].name
        if release.year:
            audio["date"] = str(release.year)
        if release.genres:
            audio["genre"] = release.genres[0]
        if release.labels:
            audio["publisher"] = release.labels[0].name
        audio.save(filepath)

        id3 = ID3(filepath)

        # Add Discogs URL (as a comment frame for now)
        id3.add(
            USLT(encoding=3, lang='eng', desc='desc', text=f"Discogs: {release.url}")
        )

        # Add cover image
        if release.images:
            img_url = release.images[0]['uri']
            img_data = requests.get(img_url).content
            id3.add(APIC(
                encoding=3, mime="image/jpeg", type=3, desc=u"Cover",
                data=img_data
            ))
        id3.save(v2_version=3)

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

if __name__ == "__main__":
    playlist_url = input("Enter YouTube playlist URL: ")
    process_playlist(playlist_url)