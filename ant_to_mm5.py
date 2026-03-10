import sqlite3
import csv
import shutil
import re
import requests
from bs4 import BeautifulSoup
import os
import json
import glob
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Configuration
DB_PATH = r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM5.DB'
CSV_PATH = r'c:\mycode\Buccaneer\mymovies.csv'
IMAGE_SOURCE_DIR = r'C:\Users\djniz\OneDrive\dbz\Movies'
LOG_FILE = r'c:\mycode\Buccaneer\processed_movies_log.txt'
MISSING_LOG = r'c:\mycode\Buccaneer\missing_matches.txt'

def iunicode_collate(s1, s2):
    return (s1.lower() > s2.lower()) - (s1.lower() < s2.lower())

def backup_database(db_path):
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

class MM5Migrator:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.conn = None
        self.cursor = None
        self.triggers_to_restore = []
        self.processed_ids = set()
        self.load_processed_log()
        self.csv_data = []

    def load_processed_log(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                self.processed_ids = set(line.strip() for line in f if line.strip())

    def log_processed(self, song_id):
        if not self.dry_run:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{song_id}\n")
            self.processed_ids.add(str(song_id))

    def log_missing(self, song_title, song_path):
        with open(MISSING_LOG, 'a', encoding='utf-8') as f:
            f.write(f"Missing: '{song_title}' | Path: {song_path}\n")

    def connect_db(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.create_collation("IUNICODE", iunicode_collate)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def drop_triggers(self):
        if self.dry_run:
            return
        print("Dropping triggers...")
        self.cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='Songs'")
        triggers = self.cursor.fetchall()
        for trigger in triggers:
            self.triggers_to_restore.append((trigger['name'], trigger['sql']))
            self.cursor.execute(f"DROP TRIGGER IF EXISTS {trigger['name']}")

    def restore_triggers(self):
        if self.dry_run:
            return
        print("Restoring triggers...")
        for name, sql in self.triggers_to_restore:
            try:
                self.cursor.execute(sql)
            except sqlite3.Error as e:
                print(f"Error restoring trigger {name}: {e}")

    def load_csv(self):
        print(f"Loading CSV from {CSV_PATH}...")
        with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
            # The CSV seems to use semicolon as delimiter and double quotes for quoting
            reader = csv.DictReader(f, delimiter=';', quotechar='"')
            self.csv_data = list(reader)
        print(f"Loaded {len(self.csv_data)} records from CSV.")

    def find_csv_match(self, title):
        cleaned_title_search = re.sub(r'\[.*?\]', '', title).replace('(', '').replace(')', '').strip().lower()
        
        # Helper to clean CSV titles for comparison
        def clean_csv_title(t):
           return re.sub(r'\[.*?\]', '', t).replace('(', '').replace(')', '').strip().lower() # Basic cleaning

        # Exact match attempt first (Case insensitive)
        for row in self.csv_data:
            orig = clean_csv_title(row.get('OriginalTitle', ''))
            trans = clean_csv_title(row.get('TranslatedTitle', ''))
            
            if orig == cleaned_title_search:
                return row
            if trans == cleaned_title_search:
                return row
        return None

    def scrape_imdb_companies(self, url):
        if not url or 'imdb.com' not in url:
            return ""
        
        try:
            print(f"Scraping IMDB: {url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch {url}: {response.status_code}")
                return ""

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # This implementation is a "best guess" based on typical IMDB layout. 
            # It might need adjustment if IMDB changes DOM.
            # Usually production companies are in a section or list items.
            # Strategy: Search for text "Production companies" and look around it.
            
            companies = []
            
            # Method 1: Use specific data-testid provided by user
            # <li ... data-testid="title-details-companies">
            companies = []
            company_block = soup.find(attrs={"data-testid": "title-details-companies"})
            
            if company_block:
                # Find all company links inside this block
                # They seem to be in an unordered list, inside list items
                links = company_block.find_all('a', href=re.compile(r'/company/'))
                for link in links:
                    name = link.get_text().strip()
                    if name and name != "Production companies": # Skip the label link if it has same pattern
                        companies.append(name)
            
            if not companies:
                 # Fallback: Simple text search
                 company_section = soup.find(string=re.compile("Production companies", re.I))
                 if company_section:
                    parent = company_section.find_parent('li') or company_section.find_parent('div')
                    if parent:
                        links = parent.find_all('a', href=re.compile(r'/company/'))
                        for link in links:
                            if link.get_text().strip():
                                companies.append(link.get_text().strip())
            
            # Deduplicate and join
            # usage of dict.fromkeys to preserve order and dedupe
            unique_companies = list(dict.fromkeys(companies))
            return "; ".join(unique_companies)
            
        except Exception as e:
            print(f"Error scraping IMDB: {e}")
            return ""

    def copy_image(self, row, song_dir):
        try:
            number = int(row.get('Number', 0))
        except ValueError:
            return 
            
        src_file = None
        
        if number < 6440:
            pattern = os.path.join(IMAGE_SOURCE_DIR, f"{number:05d}_*.jpg")
            matches = glob.glob(pattern)
            if matches:
                src_file = matches[0]
        else:
            path_candidate = os.path.join(IMAGE_SOURCE_DIR, f"{number}.jpg")
            if os.path.exists(path_candidate):
                src_file = path_candidate
        
        if src_file:
            target = os.path.join(song_dir, "folder.jpg")
            if not os.path.exists(target):
                print(f"Copying image: {src_file} -> {target}")
                if not self.dry_run:
                    shutil.copy2(src_file, target)
            else:
                pass # Already exists

    def process(self):
        if not self.dry_run:
            if not backup_database(DB_PATH):
                return

        self.connect_db()
        self.load_csv()
        self.drop_triggers()

        try:
            # Select relevant songs
            print("Querying songs...")
            # User clarification: Paths are stored as ":\The Best..." without drive letter
            self.cursor.execute("SELECT * FROM Songs WHERE SongPath LIKE ':\\The Best%'")
            songs = self.cursor.fetchall()
            print(f"Found {len(songs)} potential songs to update.")

            for song in songs:
                song_id = song['ID']
                if str(song_id) in self.processed_ids:
                    continue

                song_path_raw = song['SongPath']
                if song_path_raw.startswith(':\\'):
                    full_song_path = 'Y' + song_path_raw
                else:
                    full_song_path = song_path_raw

                title = song['SongTitle']
                cleaned_title = re.sub(r'\[.*?\]', '', title).strip()
                
                match = self.find_csv_match(cleaned_title)
                
                if not match:
                    print(f"NO MATCH: {title} (Cleaned: {cleaned_title})")
                    self.log_missing(title, full_song_path)
                    continue

                print(f"MATCH: {title} -> CSV: {match.get('OriginalTitle')}")
                
                # --- Build Update Data ---
                
                # Extended Tags
                extended_tags = []
                
                def add_tag(key, val_key, val_transform=None):
                    val = match.get(val_key, '').strip()
                    if not val: return
                    if val_transform: val = val_transform(val)
                    extended_tags.append({"title": key, "value": val})

                add_tag("MyRating", "UserRating")
                add_tag("IMDBRating", "Rating")
                add_tag("URL", "URL")
                add_tag("Country", "Country")
                add_tag("Language", "Languages")
                add_tag("AdditionalMedia", "MediaType")
                
                extended_tags_json = json.dumps(extended_tags)
                
                # Publisher (Scrape)
                publisher = ""
                imdb_url = match.get('URL', '')
                if imdb_url:
                     # Only scrape if not dry run or if we want to test it (it takes time!)
                     # For safety in dry run, maybe skip scraping to be fast? 
                     # Or print intent. Let's print intent in dry run to avoid spamming IMDB.
                     if self.dry_run:
                         publisher = "[DRY RUN: WOULD SCRAPE IMDB]"
                     else:
                         publisher = self.scrape_imdb_companies(imdb_url)

                # Prepare standard fields
                def sep(val): return "; ".join([x.strip() for x in val.split(',') if x.strip()])
                
                artist = sep(match.get('Director', ''))
                actors = sep(match.get('Actors', ''))
                
                year_str = match.get('Year', '').strip()
                year_val = None
                if year_str and year_str.isdigit():
                    year_val = int(year_str) * 10000 # YYYY0000 format
                
                genre = sep(match.get('Category', ''))
                involved_people = sep(match.get('Composer', ''))
                orig_title = match.get('OriginalTitle', '')
                producer = sep(match.get('Producer', ''))
                lyricist = sep(match.get('Writer', ''))
                parental_rating = match.get('Certification', '')
                
                desc = match.get('Description', '').strip()
                comm = match.get('Comments', '').strip()
                comment_full = f"{desc}\n{comm}".strip()

                song_path_dir = os.path.dirname(full_song_path)
                
                print(f"  -> Updating ID {song_id}...")
                
                if not self.dry_run:
                    # Update DB
                    sql = """
                        UPDATE Songs SET
                            Artist = ?,
                            Actors = ?,
                            Year = ?,
                            Genre = ?,
                            InvolvedPeople = ?,
                            OrigTitle = ?,
                            Producer = ?,
                            Lyricist = ?,
                            ParentalRating = ?,
                            Comment = ?,
                            ExtendedTags = ?,
                            Publisher = ?
                        WHERE ID = ?
                    """
                    self.cursor.execute(sql, (
                        artist, actors, year_val, genre, involved_people, orig_title, 
                        producer, lyricist, parental_rating, comment_full, extended_tags_json, 
                        publisher, song_id
                    ))
                    
                    # Image Copy
                    self.copy_image(match, song_path_dir)
                    
                    # Log
                    self.log_processed(song_id)
                else:
                    # Dry Run Output
                    print(f"    Artist: {artist}")
                    print(f"    Year: {year_val}")
                    print(f"    Publisher: {publisher}")
                    print(f"    Image Target: {os.path.join(song_path_dir, 'folder.jpg')}")
                    # ... add more details if needed
                    # Image Dry Run
                    self.copy_image(match, song_path_dir)

            if not self.dry_run:
                print("Commiting changes...")
                self.conn.commit()

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            if not self.dry_run:
                self.conn.rollback()
        finally:
            self.restore_triggers()
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--force", action="store_true", help="Actually execute the updates (disables default dry-run)")
    args = parser.parse_args()

    # Default to dry run unless --force is used, or explicit --dry-run
    # If neither, basic safety: default to dry run
    is_dry = True
    if args.force:
        is_dry = False
    
    # If user explicitly passed --dry-run, it overrides force
    if args.dry_run:
        is_dry = True

    print(f"Mode: {'DRY RUN' if is_dry else 'LIVE UPDATE'}")
    
    migrator = MM5Migrator(dry_run=is_dry)
    migrator.process()
