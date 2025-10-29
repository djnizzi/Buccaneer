import configparser
import os
from tag import tag_mp3_with_discogs, get_metadata_tags, tagged_with_discogs
from utils import get_mp3_files, strip_feat
from discogs import search_discogs_with_prompt
import discogs_client as dis

# --- CONFIG ---
config = configparser.ConfigParser()
config.read('secrets.ini')
discogs_api_key = config['API']['key']
appname = config['APP']['appname']
version = config['APP']['version']

d = dis.Client(appname + '/' + version, user_token=discogs_api_key)


SAVED_SEARCHES = "saved_searches.txt"


def is_in_saved_searches(base, review_file=SAVED_SEARCHES):

    if not os.path.exists(review_file):
        return None

    with open(review_file, "r", encoding="utf-8") as f:
        saved_searches = {line.strip() for line in f if line.strip()}

    matching_line = next((line for line in saved_searches if line.lower().startswith(base.lower())), None)
    if matching_line and "discogs:" in matching_line:
        _, right = matching_line.split("discogs:", 1)
        return right.strip()
    return None

def tag_dir_with_discogs(folder: str, overwrite: str = "n"):
    mp3_files = get_mp3_files(folder, recursive=True)
    print(f"🎵 Found {len(mp3_files)} MP3 files")
    for file in mp3_files:
        url = tagged_with_discogs(file)
        if not url:
            title, artist, album, year = get_metadata_tags(file)
            base = f"{strip_feat(artist)} - {strip_feat(album)} - {year}".strip().lower()
            is_not_in_search = True
            saved_release_id = is_in_saved_searches(base)
            if saved_release_id:
                try:
                    release = d.release(int(saved_release_id))
                    print(f"💾 Using cached release {saved_release_id} for {base}")
                    is_not_in_search = False
                except Exception as e:
                    print(f"⚠️ Failed to fetch cached release {saved_release_id}: {e}")
                    release = None
            else:
                release = search_discogs_with_prompt(base)

            if release and is_not_in_search:
                discogs_release = release.data["id"]
                with open(SAVED_SEARCHES, "a", encoding="utf-8") as out:
                    out.write(base + " discogs:" + str(discogs_release) + "\n")
            tag_mp3_with_discogs(file, release, overwrite)

if __name__ == "__main__":
    source = input("📂 Enter folder path: ").strip()
    overwrite = input("📝 Overwrite (y|n)? ").strip().lower()
    tag_dir_with_discogs(source, overwrite)
