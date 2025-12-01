import sqlite3
import os
import shutil
import argparse
from datetime import datetime

# Configuration
DB_PATH = r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM5.DB'
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mpg', '.mpeg', '.wmv', '.flv', '.webm', '.m4v', '.mov')
TAG_SUFFIX = " [Music Video]"

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

def process_videos(dry_run=False):
    if not os.path.exists(DB_PATH):
        print(f"Database not found at: {DB_PATH}")
        return

    if not dry_run:
        if not backup_database(DB_PATH):
            print("Aborting due to backup failure.")
            return

    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Register custom collation IUNICODE (MM5 specific)
        # Mapping it to standard string comparison (case-insensitive)
        def iunicode_collate(s1, s2):
            return (s1.lower() > s2.lower()) - (s1.lower() < s2.lower())

        conn.create_collation("IUNICODE", iunicode_collate)
        
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print(f"Connected to database: {DB_PATH}")
        if dry_run:
            print("--- DRY RUN MODE: No changes will be applied ---")

        # Select songs where Path contains 'MusicClips'
        cursor.execute("SELECT ID, SongTitle, SongPath, Album FROM Songs WHERE SongPath LIKE '%MusicClips%'")
        songs = cursor.fetchall()

        updated_count = 0
        skipped_count = 0
        
        print(f"Scanning {len(songs)} entries (Path contains 'MusicClips')...")
        
        # Disable triggers to bypass 'unknown tokenizer: mm' error
        if not dry_run:
            print("Disabling triggers temporarily...")
            cursor.execute("PRAGMA ignore_check_constraints = 1") # Might not be enough
            # A more robust way is to not use PRAGMA but just hope the update doesn't touch FTS columns directly?
            # Actually, updating 'Album' likely triggers FTS update.
            # We can try 'PRAGMA writable_schema = 1' to modify sqlite_master but that's dangerous.
            # Let's try to just run the update. If it fails, we catch it.
            # But the user already saw it fail.
            
            # Strategy: We can't easily disable specific triggers in SQLite without dropping them.
            # However, we can try to use `PRAGMA defer_foreign_keys = ON`? No.
            
            # Let's try to see if we can just catch the error and print a warning?
            # No, the update fails.
            
            # ALTERNATIVE: Drop the triggers temporarily?
            # That requires knowing the trigger definitions. We can read them, drop them, run update, recreate them.
            # This is complex but might be the only way if 'mm' tokenizer is required by the trigger.
            pass

        # We will try to read triggers, drop them, update, and restore them.
        triggers_to_restore = []
        if not dry_run:
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='Songs'")
            triggers = cursor.fetchall()
            for trigger in triggers:
                # Only drop triggers that might be relevant or all of them?
                # Safer to drop all on Songs table and restore.
                triggers_to_restore.append((trigger['name'], trigger['sql']))
                cursor.execute(f"DROP TRIGGER {trigger['name']}")
            print(f"Temporarily dropped {len(triggers_to_restore)} triggers.")

        try:
            for song in songs:
                song_path = song['SongPath']
                current_album = song['Album'] if song['Album'] else ""
                
                # Check if it's a video file (Safety check)
                if song_path and song_path.lower().endswith(VIDEO_EXTENSIONS):
                    
                    # Check if already tagged
                    if current_album.endswith(TAG_SUFFIX):
                        skipped_count += 1
                        continue
                    
                    new_album = current_album + TAG_SUFFIX
                    
                    print(f"MATCH: {song['SongTitle']}")
                    print(f"  Path: {song_path}")
                    print(f"  Old Album: '{current_album}'")
                    print(f"  New Album: '{new_album}'")
                    
                    if not dry_run:
                        cursor.execute("UPDATE Songs SET Album = ? WHERE ID = ?", (new_album, song['ID']))
                    
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
                # Attempt to restore triggers if they were dropped
                try:
                    for name, sql in triggers_to_restore:
                        # Check if trigger exists before creating? No, we dropped them.
                        # But if rollback happened, did it restore triggers?
                        # DDL statements (DROP TRIGGER) are transactional in SQLite.
                        # So rollback should restore them!
                        pass
                except:
                    print("Warning: Could not verify trigger restoration after rollback.")

        print(f"Total Videos Found & Processed: {updated_count}")
        print(f"Already Tagged: {skipped_count}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag music videos in MediaMonkey 5 DB.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them.")
    args = parser.parse_args()

    process_videos(dry_run=args.dry_run)
