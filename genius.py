import os
import glob
import configparser
from mutagen.id3 import ID3, USLT, ID3NoHeaderError
from rapidfuzz import fuzz
import lyricsgenius
from utils import flip_query

# --- CONFIG ---
config = configparser.ConfigParser()
config.read('secrets.ini')
GENIUS_TOKEN = config['API']['genius_key']

# Init Genius client
genius = lyricsgenius.Genius(GENIUS_TOKEN)
genius.skip_non_songs = True
genius.remove_section_headers = True

def get_mp3_files(folder: str):
    """Return list of all mp3 files in a folder."""
    return glob.glob(os.path.join(folder, "*.mp3"))

def has_lyrics(filepath: str) -> bool:
    """Check if MP3 already has lyrics tag."""
    try:
        tags = ID3(filepath)
        return any(
            frame.FrameID == "USLT" and frame.text.strip()
            for frame in tags.values()
        )
    except ID3NoHeaderError:
        return False

def search_genius(query: str):
    """Search Genius and rank results by similarity score to query."""
    flipped = flip_query(query)
    try:
        results = genius.search_songs(flipped)
        hits = results.get("hits", []) if results else []

        scored = []
        for hit in hits:
            song = hit["result"]
            full_title = f"{song['title']} - {song['primary_artist']['name']}"
            # Compare flipped query vs Genius full title
            score = fuzz.token_sort_ratio(flipped, full_title)
            scored.append((score, song))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored
    except Exception as e:
        print(f"⚠️ Genius search failed: {e}")
        return []

def choose_song(matches, min_score: int = 50, auto_threshold: int = 75):
    """
    Pick best match automatically if confidence is high enough,
    skip if best match is too low,
    otherwise prompt user.
    """
    if not matches:
        print(f"⚠️ No results found on Genius.")
        return None

    # Normalize titles for scoring
    normalized_matches = []
    for score, song in matches:
        full_title = f"{song['title']} - {song['primary_artist']['name']}".lower()
        normalized_matches.append((score, song, full_title))

    # Filter out weak matches
    matches = [(score, song) for score, song, _ in normalized_matches if score >= min_score]
    if not matches:
        print(f"⏭️ Skipping, all matches below {min_score}%.")
        return None

    best_score, best_song = matches[0]

    if best_score >= auto_threshold:
        print(f"🤖 Auto-selected: {best_song['title']} - {best_song['primary_artist']['name']} ({best_score:.1f}%)")
        return best_song

    # Otherwise, show filtered matches
    print("\nTop Genius matches:")
    for idx, (score, song) in enumerate(matches, 1):
        print(f"🎧 {idx}. {song['title']} - {song['primary_artist']['name']} ({score:.1f}%)")

    choice = input(f"Select a match [1–{len(matches)}] or press Enter to skip: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(matches):
        return matches[int(choice) - 1][1]  # return song dict
    return None


def fetch_lyrics(song):
    """Fetch lyrics from Genius given a song dict."""
    try:
        # Use Genius API again to ensure lyrics are retrieved
        lyrics_song = genius.search_song(song["title"], song["primary_artist"]["name"])
        if lyrics_song:
            return lyrics_song.lyrics
    except Exception as e:
        print(f"⚠️ Failed to fetch lyrics: {e}")
    return None

def tag_with_lyrics(filepath: str, lyrics: str):
    """Write lyrics to MP3 file."""
    try:
        tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = ID3()

    # Remove any old USLT frame to avoid duplicates
    for key in list(tags.keys()):
        if key.startswith("USLT"):
            tags.pop(key)

    tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
    tags.save(filepath)
    print(f"✅ Tagged lyrics into {os.path.basename(filepath)}")

def genius_tagger(folder: str):
    """Main function to process all MP3s in a folder."""
    mp3_files = get_mp3_files(folder)

    for file in mp3_files:
        filename = os.path.basename(file)
        title = flip_query(os.path.splitext(filename)[0])

        if has_lyrics(file):
            print(f"⏭️ Skipping {filename}, already has lyrics.")
            continue

        print(f"\n🔍 Searching lyrics for: {title}")
        results = search_genius(title)
        song = choose_song(results)

        if not song:
            print("⏭️ Skipping file, no match selected.")
            continue

        lyrics = fetch_lyrics(song)
        if lyrics:
            tag_with_lyrics(file, lyrics)
        else:
            print(f"⚠️ No lyrics found for {title}")

if __name__ == "__main__":
    folder = input(f"📂 Enter folder with MP3 files: ").strip()
    genius_tagger(folder)
