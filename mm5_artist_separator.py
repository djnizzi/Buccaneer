import sqlite3
import os
import shutil
import argparse
from datetime import datetime

# Configuration
# Attempt to find the DB in common locations, similar to inspect_mm5_schema.py
PATHS = [
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM5.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey 5\MM.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey 5\MM5.DB'
]

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mpg', '.mpeg', '.wmv', '.flv', '.webm', '.m4v', '.mov')
SEPARATORS = [" feat.", ",", " x ", " & "]
REPLACEMENT = ";"

def get_db_path():
    for path in PATHS:
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

def process_artists(dry_run=False):
    db_path = get_db_path()
    if not db_path:
        print("Error: MM5 Database not found in common locations.")
        return

    print(f"Target Database: {db_path}")

    if not dry_run:
        if not backup_database(db_path):
            print("Aborting due to backup failure.")
            return

    try:
        conn = sqlite3.connect(db_path)
        
        # Register custom collation IUNICODE (MM5 specific)
        def iunicode_collate(s1, s2):
            return (s1.lower() > s2.lower()) - (s1.lower() < s2.lower())

        conn.create_collation("IUNICODE", iunicode_collate)
        
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if dry_run:
            print("--- DRY RUN MODE: No changes will be applied ---")

        # Select songs where Path contains 'MusicClips'
        cursor.execute("SELECT ID, SongTitle, SongPath, AlbumArtist FROM Songs WHERE SongPath LIKE '%MusicClips%'")
        songs = cursor.fetchall()

        updated_count = 0
        
        print(f"Scanning {len(songs)} entries (Path contains 'MusicClips')...")
        
        # Handle triggers
        triggers_to_restore = []
        if not dry_run:
            print("Temporarily dropping triggers to avoid tokenizer errors...")
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='Songs'")
            triggers = cursor.fetchall()
            for trigger in triggers:
                triggers_to_restore.append((trigger['name'], trigger['sql']))
                cursor.execute(f"DROP TRIGGER {trigger['name']}")
            print(f"Dropped {len(triggers_to_restore)} triggers.")

        try:
            for song in songs:
                song_path = song['SongPath']
                current_artist = song['AlbumArtist'] if song['AlbumArtist'] else ""
                
                # Check if it's a video file (Safety check)
                if song_path and song_path.lower().endswith(VIDEO_EXTENSIONS):
                    
                    new_artist = current_artist
                    changed = False
                    
                    for sep in SEPARATORS:
                        # Case-insensitive check might be better, but requirements implied specific strings.
                        # However, usually " feat." is case insensitive. Let's stick to exact match for now based on request,
                        # or maybe case-insensitive replace?
                        # Request says: replaces " feat." or "," or " x " or " & " with ";"
                        # I will do case-insensitive replacement for " feat." " x " " & " but "," is just ",".
                        
                        # Actually, simple replace is safer to start with.
                        if sep in new_artist:
                             new_artist = new_artist.replace(sep, REPLACEMENT)
                             changed = True
                        
                        # Also handle case variations if needed? 
                        # For now, let's stick to the exact strings requested.
                        
                    # Clean up double semicolons or trailing/leading semicolons if any created?
                    # The request didn't specify, but it's good practice.
                    # But I should stick to exactly what was asked: replace X with ;
                    
                    if changed and new_artist != current_artist:
                        print(f"MATCH: {song['SongTitle']}")
                        print(f"  Path: {song_path}")
                        print(f"  Old Artist: '{current_artist}'")
                        print(f"  New Artist: '{new_artist}'")
                        
                        if not dry_run:
                            cursor.execute("UPDATE Songs SET AlbumArtist = ? WHERE ID = ?", (new_artist, song['ID']))
                        
                        updated_count += 1

            if not dry_run:
                # Restore triggers
                for name, sql in triggers_to_restore:
                    cursor.execute(sql)
                print(f"Restored {len(triggers_to_restore)} triggers.")
                
                conn.commit()
                print("\nChanges applied successfully.")
            else:
                print("\nDry run completed. No changes made.")

        except Exception as e:
            print(f"Error during processing: {e}")
            if not dry_run:
                conn.rollback()
                print("Rolled back changes.")
                # Attempt to restore triggers
                try:
                    for name, sql in triggers_to_restore:
                        # We can't easily check if they exist, but rollback might have restored them?
                        # If we dropped them, they are gone from schema. Rollback undoes DDL in SQLite?
                        # Yes, SQLite DDL is transactional.
                        pass
                except:
                    pass

        print(f"Total Videos Processed: {updated_count}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Separate artists in MediaMonkey 5 DB for music videos.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them.")
    args = parser.parse_args()

    process_artists(dry_run=args.dry_run)
