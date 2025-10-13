import re
import yt_dlp

def parse_youtube_description(description: str):
    data = {}

    # ℗ year + publisher
    m = re.search(r"℗\s*(\d{4})?\s*(.+)", description)
    if m:
        if m.group(1):  # year exists
            data["year"] = m.group(1)
        new_publisher = m.group(2).strip()
        if "publisher" in data:
            if new_publisher != data["publisher"]:
                data["publisher"] = f"{data['publisher']}; {new_publisher}"
        else:
            data["publisher"] = new_publisher

    # Publisher/label line
    m = re.search(r"Provided to YouTube by (.+)", description, re.IGNORECASE)
    if m:
        new_publisher = m.group(1).strip()
        if "publisher" in data:
            if new_publisher != data["publisher"]:
                data["publisher"] = f"{data['publisher']}; {new_publisher}"
        else:
            data["publisher"] = new_publisher

    # Title + artist line (split by "·")
    m = re.search(r"(.+?) · (.+)", description)
    if m:
        data["title"] = m.group(1).strip()
        normalized_uploader = m.group(2).replace(" · ", "; ")
        data["uploader"] = normalized_uploader.strip()

    # Released on: YYYY-MM-DD
    m = re.search(r"Released on:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", description, re.IGNORECASE)
    if m:
        data["upload_date"] = m.group(1)  # exact release date

    # Composer(s) — can appear multiple times
    composers = re.findall(r"Composer:\s*(.+)", description, re.IGNORECASE)
    if composers:
        # Join multiple composers with "; " (like Discogs style)
        data["composer"] = "; ".join(c.strip() for c in composers)

    # Lyrics: everything after "lyrics:"
    m = re.search(r"lyrics[:\-\n]+(.+)", description, re.IGNORECASE | re.DOTALL)
    if m:
        data["lyrics"] = m.group(1).strip()

    return data

# --- YT metadata ---
def get_yt_metadata(url: str):
    ydl_opts = {"skip_download": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ytinfo = ydl.extract_info(url, download=False)
        description = ytinfo.get("description", "")
        upload_date = ytinfo.get("upload_date")
        if upload_date:
            ytinfo["upload_date"] = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        parsed = parse_youtube_description(description)

        # Merge parsed info into yt_dlp info (parsed values overwrite if duplicated)
        combined = {**ytinfo, **parsed}

        return combined
