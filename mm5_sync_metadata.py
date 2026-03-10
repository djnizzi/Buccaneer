import sqlite3
import os
import shutil
import re
import argparse
from datetime import datetime

# Configuration
DB_PATHS = [
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM5.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey 5\MM.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey 5\MM5.DB'
]

def find_db():
    for path in DB_PATHS:
        if os.path.exists(path):
            return path
    return None

def backup_database(db_path):
    """Creates a timestamped backup of the SQLite database."""
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.{timestamp}.bak"

    try:
        shutil.copy2(db_path, backup_path)
        print(f"Database backup created: {backup_path}")
        return True
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return False

def clean_title(title):
    """
    Cleans the song title for fuzzy matching.
    Removes:
    - Text in (...) or [...]
    - "feat." and everything after it (optional, but user said 'strip any featured artist in the song title')
      - User said: "try stripping any featured artist in the song title and anything in ( ) or [ ]"
    - Leading/trailing whitespace
    """
    if not title:
        return ""
    
    # Remove text in brackets
    title = re.sub(r'[\(\[].*?[\)\]]', '', title)
    
    # Remove "feat." or "ft." and everything after
    # Case insensitive
    title = re.sub(r'\s(feat\.|ft\.|featuring).*$', '', title, flags=re.IGNORECASE)
    
    # Remove extra spaces
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title.lower()

def get_artists(artist_str):
    """Returns a set of artists from a semicolon-separated string."""
    if not artist_str:
        return set()
    return {a.strip().lower() for a in artist_str.split(';') if a.strip()}

def sync_metadata(dry_run=False):
    db_path = find_db()
    if not db_path:
        print("Error: Could not find MediaMonkey database.")
        return

    print(f"Using database: {db_path}")

    if not dry_run:
        if not backup_database(db_path):
            print("Aborting due to backup failure.")
            return
    else:
        print("--- DRY RUN MODE ---")

    try:
        conn = sqlite3.connect(db_path)
        
        # Register custom collation IUNICODE (MM5 specific)
        def iunicode_collate(s1, s2):
            return (s1.lower() > s2.lower()) - (s1.lower() < s2.lower())
        conn.create_collation("IUNICODE", iunicode_collate)
        
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Get all Music Videos
        print("Fetching Music Videos...")
        # User specified Grouping = "MusicVideo", which maps to GroupDesc in DB
        cursor.execute("SELECT * FROM Songs WHERE GroupDesc = 'MusicVideo'")
        music_videos = cursor.fetchall()
        print(f"Found {len(music_videos)} Music Videos.")

        # 2. Get all potential Audio Songs (not MusicVideo)
        # We fetch ID, SongTitle, AlbumArtist, Year, Genre, Publisher
        print("Fetching Audio Songs...")
        # Optimization: Fetch only necessary columns to save memory
        # We exclude items where GroupDesc is 'MusicVideo'
        cursor.execute("SELECT ID, SongTitle, AlbumArtist, Year, Genre, Publisher FROM Songs WHERE GroupDesc != 'MusicVideo' OR GroupDesc IS NULL")
        audio_songs = cursor.fetchall()
        print(f"Found {len(audio_songs)} Audio Songs.")

        # 3. Index Audio Songs for faster lookup
        # We'll use a dictionary where key = cleaned_title, value = list of songs
        audio_index = {}
        for song in audio_songs:
            ct = clean_title(song['SongTitle'])
            if ct not in audio_index:
                audio_index[ct] = []
            audio_index[ct].append(song)

        matches_found = 0
        misses = []
        
        # Load processed IDs
        processed_ids = set()
        processed_log_path = "mm5_sync_processed.txt"
        if os.path.exists(processed_log_path):
            with open(processed_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        processed_ids.add(int(line.strip()))
                    except ValueError:
                        pass
        print(f"Loaded {len(processed_ids)} processed IDs.")

        # Drop triggers to avoid 'unknown tokenizer: mm' error
        triggers_to_restore = []
        if not dry_run:
            print("Temporarily dropping triggers on Songs table...")
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='Songs'")
            triggers = cursor.fetchall()
            for trigger in triggers:
                triggers_to_restore.append((trigger['name'], trigger['sql']))
                cursor.execute(f"DROP TRIGGER {trigger['name']}")
            print(f"Dropped {len(triggers_to_restore)} triggers.")

        # 4. Iterate and Match
        for video in music_videos:
            if video['ID'] in processed_ids:
                continue

            # Filter out videos from 2022 onwards
            video_year = video['Year']
            if video_year:
                str_year = str(video_year)
                # Handle YYYYMMDD or YYYY
                if len(str_year) >= 4:
                    try:
                        year_num = int(str_year[:4])
                        if year_num >= 2022:
                            continue
                    except ValueError:
                        pass

            video_title = video['SongTitle']
            video_artist_str = video['AlbumArtist']
            
            cleaned_video_title = clean_title(video_title)
            video_artists = get_artists(video_artist_str)
            
            potential_matches = audio_index.get(cleaned_video_title, [])
            
            # Filter by Artist Overlap
            confirmed_matches = []
            for song in potential_matches:
                song_artists = get_artists(song['AlbumArtist'])
                # Check intersection
                if not video_artists or not song_artists:
                     continue
                
                if not video_artists.isdisjoint(song_artists):
                    confirmed_matches.append(song)

            if not confirmed_matches:
                misses.append(f"{video_title} ({video_artist_str})")
                
                # Log processed ID even if no match found (to avoid re-processing)
                if not dry_run:
                    with open(processed_log_path, "a", encoding="utf-8") as f:
                        f.write(f"{video['ID']}\n")
                continue

            selected_match = None
            if len(confirmed_matches) == 1:
                selected_match = confirmed_matches[0]
            else:
                # Multiple matches - Auto-select oldest year
                # Sort by Year ascending. Treat 0 or None as very large number to put them at end.
                def get_year_sort_key(match):
                    y = match['Year']
                    if not y or y == 0:
                        return 99999999 # Push to end
                    return y
                
                confirmed_matches.sort(key=get_year_sort_key)
                
                selected_match = confirmed_matches[0]
                
                # Log the decision
                print(f"Multiple matches for '{video_title}': Auto-selected oldest year ({selected_match['Year']}) from {len(confirmed_matches)} matches.")
                # for m in confirmed_matches:
                #     print(f"  - {m['SongTitle']} ({m['Year']})")
            
            if selected_match:
                # Update Video
                new_year = selected_match['Year']
                new_genre = selected_match['Genre']
                new_publisher = selected_match['Publisher']
                
                print(f"Updating '{video_title}': Year={new_year}, Genre={new_genre}, Publisher={new_publisher}")
                
                if not dry_run:
                    cursor.execute("""
                        UPDATE Songs 
                        SET Year = ?, Genre = ?, Publisher = ?
                        WHERE ID = ?
                    """, (new_year, new_genre, new_publisher, video['ID']))
                    matches_found += 1
            
            # Log processed ID
            if not dry_run:
                with open(processed_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{video['ID']}\n")

        if not dry_run:
            # Restore triggers
            print("Restoring triggers...")
            for name, sql in triggers_to_restore:
                cursor.execute(sql)
            print(f"Restored {len(triggers_to_restore)} triggers.")
            
            conn.commit()
            print("\nChanges committed to database.")
        
        print(f"\nTotal Matches Updated: {matches_found}")
        print(f"Total Misses: {len(misses)}")
        
        if misses:
            with open("mm5_sync_misses.log", "w", encoding="utf-8") as f:
                for miss in misses:
                    f.write(miss + "\n")
            print("Misses logged to mm5_sync_misses.log")

    except Exception as e:
        print(f"An error occurred: {e}")
        if not dry_run and 'conn' in locals():
            conn.rollback()
            print("Rolled back changes.")
            # Since we rolled back, triggers dropped in the transaction should be restored automatically by SQLite.
            # But if we dropped them *before* a transaction started (if autocommit is on? No, python sqlite3 starts transaction automatically)
            # Python sqlite3 starts a transaction on the first DML/DDL statement usually.
            # So rollback should restore triggers.



    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync metadata from Audio to Music Videos in MM5.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them.")
    args = parser.parse_args()

    sync_metadata(dry_run=args.dry_run)
