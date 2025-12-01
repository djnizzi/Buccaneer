import sqlite3
import xml.etree.ElementTree as ET
import os
import shutil
from datetime import datetime

# Configuration
# ------------------------------------------------------------------------------
XML_FILE_PATH = r'C:\Path\To\Your\collection.xml'
DB_PATH = r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM.DB'
CREATE_BACKUP = True


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


def get_or_create_genre(cursor, genre_name):
    """Finds or creates a Genre and returns its ID."""
    if not genre_name:
        return None

    primary_genre = genre_name.split(',')[0].strip()  # Take first genre only

    try:
        cursor.execute("SELECT IDGenre FROM Genres WHERE GenreName = ?", (primary_genre,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            cursor.execute("INSERT INTO Genres (GenreName) VALUES (?)", (primary_genre,))
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error handling Genre '{primary_genre}': {e}")
        return None


def find_media_monkey_id(cursor, original_title, translated_title, year):
    """
    Tries to find the MediaMonkey Song ID.
    1. Attempts match by OriginalTitle (+ Year).
    2. Fails -> Attempts match by TranslatedTitle (+ Year).
    """

    # Helper query builder
    def check_title(title_to_check):
        if not title_to_check: return []

        query = "SELECT ID FROM Songs WHERE SongTitle = ?"
        params = [title_to_check]

        # Optional: Strict Year matching.
        # If you want to relax this (e.g. Ant has 1999, MM has 2000), comment out the if block below.
        if year > 1900:
            query += " AND Year = ?"
            params.append(year)

        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    # 1. Try Original Title
    matches = check_title(original_title)
    if matches:
        return matches, "OriginalTitle"

    # 2. Try Translated Title (Fallback)
    matches = check_title(translated_title)
    if matches:
        return matches, "TranslatedTitle"

    return [], None


def parse_and_update(xml_path, db_path):
    """Parses XML and updates MediaMonkey DB with fallback title matching."""

    # 1. Parse XML
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    # 2. Connect DB
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        print(f"DB Connection error: {e}")
        return

    print("Connected to database. Processing movies...")

    stats = {'updated': 0, 'skipped': 0, 'errors': 0}

    # 3. Process Movies
    movies = root.findall("./Contents/Movie")

    for movie in movies:
        try:
            xml_data = movie.attrib

            # Titles
            original_title = xml_data.get('OriginalTitle', '').strip()
            translated_title = xml_data.get('TranslatedTitle', '').strip()  # Ant field for translated

            # Basic Metadata
            year_str = xml_data.get('Year', '0')
            rating_str = xml_data.get('Rating', '0')

            # People
            director = xml_data.get('Director', '')
            producer = xml_data.get('Producer', '')
            writer = xml_data.get('Writer', '')
            actors = xml_data.get('Actors', '').replace('|', '; ')

            # Misc
            category = xml_data.get('Category', '')
            country = xml_data.get('Country', '')
            url = xml_data.get('URL', '')
            description = xml_data.get('Description', '')  # Often mapped to Comment

            # Conversions
            try:
                year = int(year_str)
            except:
                year = 0

            try:
                rating_val = float(rating_str)
                mm_rating = int(rating_val * 10)  # MM 0-100
                if mm_rating > 100: mm_rating = 100
            except:
                mm_rating = -1

            # --- MATCHING LOGIC ---
            matches, match_type = find_media_monkey_id(cursor, original_title, translated_title, year)

            if not matches:
                # Log which title we tried to search for in the console for debugging
                search_term = original_title if original_title else translated_title
                print(f"SKIP: No match found for '{search_term}' (Year: {year})")
                stats['skipped'] += 1
                continue

            # Get Genre ID
            genre_id = get_or_create_genre(cursor, category)

            # --- UPDATE LOGIC ---
            for match in matches:
                song_id = match['ID']

                # Mapping Logic:
                # Lyricist -> Writer (Standard MM Video mapping)
                # Custom2 -> Country (Your specific mapping)
                # Comment -> Description

                # ---------------------------------------------------------
                # TODO: EXTENDED TAGS MAPPING
                # When you provide the specific extended tags, we will add them
                # to the SQL query below.
                # Example: Custom1, Custom3, Mood, Occasion, etc.
                # ---------------------------------------------------------

                update_sql = """
                    UPDATE Songs SET 
                        Rating = ?,
                        Director = ?,
                        Producer = ?,
                        Lyricist = ?, 
                        Actors = ?,
                        IDGenre = ?,
                        WebWWW = ?,
                        Custom2 = ?
                    WHERE ID = ?
                """

                params = (
                    mm_rating,
                    director,
                    producer,
                    writer,
                    actors,
                    genre_id if genre_id else None,
                    url,
                    country,  # Mapped to Custom2 as requested
                    song_id
                )

                cursor.execute(update_sql, params)

            stats['updated'] += 1
            # Optional: Print how it matched
            # print(f"UPDATED: '{original_title}' (Matched via {match_type})")

        except Exception as e:
            print(f"ERROR processing entry: {e}")
            stats['errors'] += 1

    try:
        conn.commit()
        print("\n--- Summary ---")
        print(f"Updated: {stats['updated']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Errors : {stats['errors']}")
    finally:
        conn.close()


if __name__ == "__main__":
    if not os.path.exists(XML_FILE_PATH) or not os.path.exists(DB_PATH):
        print("Check your file paths.")
    else:
        if CREATE_BACKUP: backup_database(DB_PATH)
        parse_and_update(XML_FILE_PATH, DB_PATH)