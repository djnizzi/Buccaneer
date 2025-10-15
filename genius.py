import os
import glob
import configparser
from mutagen.id3 import ID3, USLT, ID3NoHeaderError
from rapidfuzz import fuzz
import lyricsgenius
from utils import flip_query, keep_main

# --- CONFIG ---
config = configparser.ConfigParser()
config.read('secrets.ini')
GENIUS_TOKEN = config['API']['genius_key']

# Init Genius client
genius = lyricsgenius.Genius(GENIUS_TOKEN, verbose=False)
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
            getattr(frame, "FrameID", "") == "USLT" and getattr(frame, "text", "").strip()
            for frame in tags.values()
        )
    except ID3NoHeaderError:
        return False

def search_genius(query: str):
    """
    Search Genius and rank results by similarity score to query.
    Input `query` should be the basename, e.g. "Artist - Title".
    This function flips the query internally to "Title - Artist" for searching.
    """
    # keep original query (Artist - Title)
    flipped = flip_query(query)  # Title - Artist
    try:
        results = genius.search_songs(flipped)
        hits = results.get("hits", []) if results else []

        scored = []
        for hit in hits:
            song = hit["result"]
            # Build comparison string in the same format we flip to:
            full_title = f"{song.get('title','')} - {song.get('primary_artist',{}).get('name','')}"
            # Compare flipped query vs Genius full title
            score = fuzz.token_sort_ratio(flipped, full_title)
            scored.append((score, song))

        # ensure sorted by score desc
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored
    except Exception as e:
        print(f"⚠️ Genius search failed for '{query}': {e}")
        return []

def choose_song(matches, query: str, min_score: int = 50, auto_threshold: int = 75):
    """
    Decide what to do with search results:
      - returns ("auto", song_dict) if auto-selected
      - returns ("skip", None) if no match >= min_score
      - returns ("manual", filtered_list) if manual selection is needed

    Important: `query` is the basename "Artist - Title" (unflipped).
    Scoring is computed against the flipped form ("Title - Artist") to match search_genius.
    """
    if not matches:
        return "skip", None

    # Use the same flipped form as the search function for scoring
    query_for_scoring = flip_query(query).lower()

    # Recompute (case-insensitive) scores to be sure
    scored = []
    for _, song in matches:
        full_title = f"{song.get('title','')} - {song.get('primary_artist',{}).get('name','')}".lower()
        score = fuzz.token_sort_ratio(query_for_scoring, full_title)
        scored.append((score, song))

    # Sort descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Filter out weak matches
    filtered = [(s, song) for s, song in scored if s >= min_score]
    if not filtered:
        # show best score for debugging
        best = scored[0][0] if scored else 0
        print(f"⏭️ Skipping")
        return "skip", None

    best_score, best_song = filtered[0]

    if best_score >= auto_threshold:
        print("🤖", end = "")
        return "auto", best_song

    # Manual needed: return filtered candidates (score, song)
    return "manual", filtered

def fetch_lyrics(song):
    """Fetch lyrics from Genius given a song dict (title & primary artist required)."""
    try:
        # use search_song to get a Song object with .lyrics
        title = song.get("title")
        artist = song.get("primary_artist", {}).get("name")
        if not (title and artist):
            return None
        lyrics_song = genius.search_song(title, artist)
        if lyrics_song:
            return lyrics_song.lyrics
    except Exception as e:
        print(f"⚠️ Failed to fetch lyrics for {song.get('title')} - {e}")
    return None

def tag_with_lyrics(filepath: str, lyrics: str):
    """Write lyrics to MP3 file (replace old USLT frames)."""
    try:
        tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = ID3()

    # Remove existing USLT frames
    for key in list(tags.keys()):
        if key.startswith("USLT"):
            tags.pop(key)

    tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
    tags.save(filepath)
    if lyrics != "Instrumental":
        print(f"✅ Tagged {os.path.basename(filepath)}")
    else:
        print(f"✅ Tagged {os.path.basename(filepath)} as Instrumenal")

def genius_tagger(folder: str):
    """Main function to process all MP3s in a folder. Manual prompts deferred to the end."""
    mp3_files = get_mp3_files(folder)
    if not mp3_files:
        print(f"No mp3s found in {folder}")
        return

    pending = []

    for file in mp3_files:
        # use basename without extension as the query
        base = os.path.splitext(os.path.basename(file))[0]
        if has_lyrics(file):
            print(f"🎵 Skipping {base}, already has lyrics.")
            continue

        print("🔍", end = "")
        results = search_genius(base)   # search_genius flips internally
        decision, data = choose_song(results, base)

        # 🔁 Retry with stripped "feat." if low score (manual trigger)
        if decision != "auto":
            alt_query = flip_query(keep_main(flip_query(base)))
            if alt_query != base:
                print("↩️", end = "")
                results = search_genius(alt_query)
                decision, data = choose_song(results, alt_query)

        if decision == "auto":
            song = data
            lyrics = fetch_lyrics(song)
            if lyrics:
                tag_with_lyrics(file, lyrics)
            else:
                tag_with_lyrics(file, "Instrumental")

        elif decision == "skip":
            # already printed reason inside choose_song
            pass

        elif decision == "manual":
            # Defer manual review: store file path, display name, and filtered candidates
            pending.append((file, base, data))

    # After loop: prompt user for pending/manual ones
    if pending:
        print("\n=== Manual review for ambiguous matches ===")
    for file, base, scored in pending:
        if not has_lyrics(file):
            base = flip_query(base)
            print(f"\n🔍 Manual review needed for: {base}")
            for idx, (score, song) in enumerate(scored, 1):
                print(f"🎧 {idx}. {song.get('title')} - {song.get('primary_artist',{}).get('name')} ({score:.1f}%)")

            choice = input(f"Select a match [1–{len(scored)}], 0 for Instrumental or press Enter to skip: ").strip()
            if choice == "0":
                tag_with_lyrics(file, "Instrumental")
            elif choice.isdigit() and 1 <= int(choice) <= len(scored):
                song = scored[int(choice) - 1][1]
                lyrics = fetch_lyrics(song)
                if lyrics:
                    tag_with_lyrics(file, lyrics)
            else:
                print("⏭️ Skipped.")

if __name__ == "__main__":
    folder = input("📂 Enter folder with MP3 files: ").strip()
    genius_tagger(folder)




