import os
import yt_dlp
import discogs_client
import lyricsgenius
import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, USLT
from rapidfuzz import process

# --- CONFIG ---
DISCOGS_TOKEN = "YOUR_DISCOGS_TOKEN"
GENIUS_TOKEN = "YOUR_GENIUS_TOKEN"
OUTPUT_DIR = "downloads"

# Init clients
d = discogs_client.Client('YTDiscogsTagger/1.0', user_token=DISCOGS_TOKEN)
genius = lyricsgenius.Genius(GENIUS_TOKEN)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- STEP 1: Download playlist ---
def download_playlist(playlist_url):
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
        return info.get("entries", [])

# --- STEP 2: Find Discogs release ---
def search_discogs(title):
    try:
        results = d.search(title, type='release')
        if results:
            return results[0]  # take best match for now
    except Exception as e:
        print("Discogs error:", e)
    return None

# --- STEP 3: Tag MP3 ---
def tag_mp3(filepath, release):
    try:
        audio = EasyID3(filepath)
    except Exception:
        audio = EasyID3()
    
    if release:
        audio["artist"] = release.artists[0].name
        audio["title"] = release.title
        audio["album"] = release.title
        audio["albumartist"] = release.artists[0].name
        audio["date"] = str(release.year) if release.year else ""
        audio["genre"] = release.genres[0] if release.genres else ""
        audio["publisher"] = release.labels[0].name if release.labels else ""
        audio.save(filepath)

        # Add Discogs URL
        id3 = ID3(filepath)
        id3.add(
            USLT(encoding=3, lang='eng', desc='desc', text=f"Discogs: {release.url}")
        )

        # Fetch and embed cover
        if release.images:
            img_url = release.images[0]['uri']
            img_data = requests.get(img_url).content
            id3.add(APIC(
                encoding=3, mime="image/jpeg", type=3, desc=u"Cover",
                data=img_data
            ))
        id3.save(v2_version=3)

# --- STEP 4: Fetch lyrics ---
def add_lyrics(filepath, artist, title):
    song = genius.search_song(title, artist)
    if song:
        id3 = ID3(filepath)
        id3.add(
            USLT(encoding=3, lang='eng', desc='Lyrics', text=song.lyrics)
        )
        id3.save(v2_version=3)

# --- MAIN ---
if __name__ == "__main__":
    playlist_url = input("Enter YouTube playlist URL: ")
    entries = download_playlist(playlist_url)

    for entry in entries:
        if not entry: continue
        title = entry.get("title")
        filename = os.path.join(OUTPUT_DIR, f"{title}.mp3")

        release = search_discogs(title)
        if release:
            print(f"Matched: {release.title} - {release.artists[0].name}")
            tag_mp3(filename, release)
            add_lyrics(filename, release.artists[0].name, release.title)
        else:
            print(f"No Discogs match for {title}")