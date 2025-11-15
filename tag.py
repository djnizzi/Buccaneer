import os
from mutagen.id3 import ID3, APIC, TOAL, TSRC, TALB, TPE1, TPE2, TIT2, TCON, TDRC, TPUB, TDOR, COMM, TCOM, USLT, ID3NoHeaderError
import requests
from tqdm import tqdm
from utils import normalize_yt_title, merge_feat, fetch_and_crop_cover, clean_discogs_artist
from yt import get_yt_metadata

def tagged_with_discogs(filepath: str):

    try:
        tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = None

    url = None
    if tags:
        if "TOAL" in tags:
            url = str(tags["TOAL"])
            if url == "" or not "discogs" in url:
                url = None

    return url


def get_metadata_tags(filepath: str):
    """
    Return (title, artist) from ID3 tags.
    - Title from TIT2
    - Album Artist (TPE2), unless it contains 'VVAA'
    - If VVAA in Album Artist, fallback to Artist (TPE1)
    """
    try:
        tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = None

    title, artist, album, year = None, None, None, None
    if tags:
        if "TIT2" in tags:
            title = str(tags["TIT2"])
        if "TALB" in tags:
            album = str(tags["TALB"])
        if "TDRC" in tags:
            year = str(tags["TDRC"])
        if "TPE2" in tags:  # Album Artist
            artist = str(tags["TPE2"])
        if artist:
            if "VVAA" in artist.upper():
                if "TPE1" in tags:  # fallback to Artist
                    artist = str(tags["TPE1"])

    # fallback from filename if missing
    if not title:
        title = os.path.splitext(os.path.basename(filepath))[0]
    if not artist:
        if tags:
            if "TPE1" in tags:
                artist = str(tags["TPE1"])
            else:
                tqdm.write(f"⛔ Artist is None! in {filepath}")
                artist = "NOARTIST"
            tqdm.write(f"⛔ Album Artist is None! in {filepath}")
        else:
            tqdm.write(f"⛔ No tags! in {filepath}")
            artist = "NOARTIST"

    return title.strip(), artist.strip(), album, year



# --- tag from YT ---
def tag_from_yt(filepath: str, url: str):
    info = get_yt_metadata(url)
    id3 = ID3(filepath)

    artist, song = normalize_yt_title(info)
    upload_date = info.get("upload_date")  # YYYY-MM-DD

    album_artist = merge_feat(artist)

    # Title + Artist
    id3.add(TIT2(encoding=3, text=song))
    id3.add(TPE1(encoding=3, text=artist))
    id3.add(TPE2(encoding=3, text=album_artist))
    id3.add(TALB(encoding=3, text=f"{song} [Single]"))

    # Release date (TDOR) & year (TDRC)
    if upload_date:
        id3.add(TDOR(encoding=3, text=f"{upload_date}"))
        id3.add(TDRC(encoding=3, text=f"{upload_date[0:4]}"))
    # overwrite with year if present
    if "year" in info:
        id3.add(TDRC(encoding=3, lang="eng", desc="", text=info["year"]))

    # Save lyrics if present
    if "lyrics" in info:
        id3.add(USLT(encoding=3, lang="eng", desc="", text=info["lyrics"]))

    # Save composer if present
    if "composer" in info:
        id3.add(TCOM(encoding=3, lang="eng", desc="", text=info["composer"]))

    # Save publisher if present
    if "publisher" in info:
        id3.add(TPUB(encoding=3, lang="eng", desc="", text=info["publisher"]))

    # Save description if present
    if "description" in info:
        id3.add(COMM(encoding=3, lang="eng", desc="", text=info["description"]))

    # Cover art
    cover_data, mime_type = fetch_and_crop_cover(info.get("thumbnails", []))
    if cover_data:
        id3.add(APIC(
            encoding=3,
            mime=mime_type or "image/jpeg",
            type=3,
            desc="Cover",
            data=cover_data
        ))
        # print("🖼️ Added cropped YouTube thumbnail as cover")
    else:
        print("⚠️ No valid thumbnail to add as cover, skipping")

    id3.save(v2_version=3)
    # print(f"✅ Tagged {filepath} with YouTube metadata")

def tag_mp3_with_discogs(filepath: str, release, overwrite: str = "y"):
    """
    Tag an MP3 file with Discogs metadata, cover art, URL, and catalog/ISRC.
    If overwrite='n', only writes tags that are currently missing.
    """
    if not release:
        print(f"⚠️ No release provided for tagging {filepath}")
        return

    try:
        id3 = ID3(filepath)
    except Exception:
        id3 = ID3()

    def add_tag(frame_class, *args, **kwargs):
        """Add a tag if overwriting is allowed or tag doesn't exist."""
        frame_id = frame_class.__name__[:4]
        if overwrite.lower() == "n" and frame_id in id3:
            # Skip if not overwriting and tag already present
            return
        id3.add(frame_class(*args, **kwargs))

    try:
        # --- Core tags ---
        artists = [
            clean_discogs_artist(a.name if not isinstance(a, dict) else a.get("name", "Unknown Artist"))
            for a in getattr(release, "artists", [])
        ]
        artists_str = "; ".join(artists) if artists else "Unknown Artist"
        album = getattr(release, "title", "Unknown Album")
        formats = getattr(release, "formats", [])
        is_single = False
        is_ep = False

        for fmt in formats:
            if "name" in fmt and "single" in fmt["name"].lower():
                is_single = True
                break
            if "descriptions" in fmt and any("single" in d.lower() for d in fmt["descriptions"]):
                is_single = True
                break
            if "name" in fmt and "ep" in fmt["name"].lower():
                is_ep = True
                break
            if "descriptions" in fmt and any("ep" in d.lower() for d in fmt["descriptions"]):
                is_ep = True
                break

        if is_single:
            album += " [Single]"
        if is_ep:
            album += " [EP]"

        genres = list(getattr(release, "genres", []))
        year = getattr(release, "year", None)
        released = (
            getattr(release, "released", None)
            or getattr(release, "data", {}).get("released")
            or getattr(release, "data", {}).get("released_formatted")
        )

        add_tag(TPE1, encoding=3, text=artists_str)
        add_tag(TPE2, encoding=3, text=artists_str)
        # add_tag(TIT2, encoding=3, text=title)
        add_tag(TALB, encoding=3, text=album)
        if genres:
            add_tag(TCON, encoding=3, text=genres[0])
        if year:
            add_tag(TDRC, encoding=3, text=str(year))
        if released:
            add_tag(TDOR, encoding=3, text=str(released))

        # Labels / publisher
        labels = [l.name if not isinstance(l, dict) else l.get("name", "Unknown") for l in getattr(release, "labels", [])]
        if labels:
            add_tag(TPUB, encoding=3, desc="Publisher", text="; ".join(labels))

        # Discogs URL
        discogs_url = getattr(release, "url", None)
        if discogs_url:
            add_tag(TOAL, encoding=3, desc="DiscogsURL", text=discogs_url)

        # Catalog number
        catno = None
        if getattr(release, "labels", []):
            label = release.labels[0]
            if isinstance(label, dict):
                catno = label.get("catno")
            else:
                catno = getattr(label, "catno", None)
        if catno:
            add_tag(TSRC, encoding=3, desc="CatalogNumber", text=catno)

        # Cover art
        existing_covers = [f for f in id3.getall("APIC") if f.data]
        if overwrite.lower() == "n" and existing_covers:
            print("🖼️ Skipping cover art (already present)")
        elif hasattr(release, "images") and release.images:
            img_url = release.images[0].get("resource_url")
            if img_url and (overwrite.lower() == "y" or "APIC" not in id3):
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    response = requests.get(img_url, headers=headers)
                    if response.headers.get("content-type", "").startswith("image/"):
                        img_data = response.content
                        mime_type = response.headers["content-type"]
                        add_tag(APIC, encoding=3, mime=mime_type, type=3, desc="Cover", data=img_data)
                        print("🖼️ Added cover art")
                except Exception as e:
                    print(f"⚠️ Could not fetch cover art: {e}")

        id3.save(filepath, v2_version=3)
        print(f"✅ Saved tags for {filepath}")

    except Exception as e:
        print(f"❌ Error tagging {filepath}: {e}")