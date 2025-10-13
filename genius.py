import configparser
import lyricsgenius

config = configparser.ConfigParser()
config.read('secrets.ini')

# --- CONFIG ---
config = configparser.ConfigParser()
config.read('secrets.ini')
GENIUS_TOKEN =  config['API']['genius_key']

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