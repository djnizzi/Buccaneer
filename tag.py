from mutagen.id3 import ID3, APIC, TOAL, TSRC, TALB, TPE1, TPE2, TIT2, TCON, TDRC, TPUB, TDOR, COMM, TCOM, USLT
import requests
from utils import normalize_yt_title, merge_feat, fetch_and_crop_cover, clean_discogs_artist
from yt import get_yt_metadata


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
        print("🖼️ Added cropped YouTube thumbnail as cover")
    else:
        print("⚠️ No valid thumbnail to add as cover, skipping")

    id3.save(v2_version=3)
    print(f"✅ Tagged {filepath} with YouTube metadata")

# --- Tag MP3 with Discogs Metadata ---
def tag_mp3_with_discogs(filepath: str, release):
    """Tag an MP3 file with Discogs metadata, cover art, URL, and catalog/ISRC."""
    if not release:
        print(f"⚠️ No release provided for tagging {filepath}")
        return
    try:
        id3 = ID3(filepath)
    except Exception:
          id3 = ID3()

    # --- Core tags ---
    try:
        artists = [clean_discogs_artist(a.name if not isinstance(a, dict) else a.get("name", "Unknown Artist"))
                   for a in getattr(release, "artists", [])]
        # Join them with "; "
        artists_str = "; ".join(artists) if artists else "Unknown Artist"
        title = getattr(release, "title", "Unknown Title")
        album = getattr(release, "title", "Unknown Album")
        formats = getattr(release, "formats", [])
        is_single = False
        is_ep = False

        for fmt in formats:
            # Check format name (e.g. "CD", "File") and descriptions (e.g. "Single", "AAC")
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
            id3.add(TPE1(encoding=3, text=artists_str if artists else "Unknown Artist"))  # Lead artist
        if is_ep:
            album += " [EP]"
        genres = list(getattr(release, "genres", []))
        year = getattr(release, "year", None)
        released = (
                getattr(release, "released", None)
                or release.data.get("released")
                or release.data.get("released_formatted")
        )
        id3.add(TPE2(encoding=3, text=artists_str if artists else "Unknown Artist"))  # Album artist
        #id3.add(TIT2(encoding=3, text=title))
        id3.add(TALB(encoding=3, text=album))
        if genres:
            id3.add(TCON(encoding=3, text=genres[0]))
        if year:
            id3.add(TDRC(encoding=3, text=str(year)))
        if released:
            id3.add(TDOR(encoding=3, text=str(released)))

        print(f"✅ Tagged basic metadata for {filepath} " + released)
    except Exception as e:
        print(f"❌ Error tagging basic metadata: {e}")

    # --- Extended / custom tags ---
    try:
        # Labels / publisher
        labels = [l.name if not isinstance(l, dict) else l.get("name", "Unknown")
                  for l in getattr(release, "labels", [])]
        if labels:
            id3.add(TPUB(encoding=3, desc="Publisher", text="; ".join(labels)))

        # Discogs URL (use master URL if available)
        discogs_url = getattr(getattr(release, "master", release), "url", getattr(release, "url", None))
        if discogs_url:
            id3.add(TOAL(encoding=3, desc="DiscogsURL", text=discogs_url))

        # Catalog number (from first label)
        catno = None
        if getattr(release, "labels", []):
            label = release.labels[0]
            if isinstance(label, dict):
                catno = label.get("catno")
            else:
                catno = getattr(label, "catno", None)
        if catno:
            id3.add(TSRC(encoding=3, desc="CatalogNumber", text=catno))

        # Cover image
        if hasattr(release, "images") and release.images:
            img_url = release.images[0].get("resource_url")  # use resource_url
            if img_url:
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/116.0.0.0 Safari/537.36"
                    }
                    response = requests.get(img_url, headers=headers)
                    if response.headers.get("content-type", "").startswith("image/"):
                        img_data = response.content
                        mime_type = response.headers["content-type"]

                        id3.add(APIC(
                            encoding=3,
                            mime=mime_type,
                            type=3,  # Cover (front)
                            desc="Cover",
                            data=img_data
                        ))
                        print("🖼️ Added cover art ")
                except Exception as e:
                    print(f"⚠️ Could not fetch cover art: {e}")

        id3.save(v2_version=3)
        print(f"✅ Saved all ID3v2 tags for {filepath}")

    except Exception as e:
        print(f"❌ Error adding extended tags: {e}")