import os
import yt_dlp
from utils import normalize_yt_title, safe_filename, clean_feat, clean_title
from discogs import search_discogs_with_prompt
from tag import tag_mp3_with_discogs, tag_from_yt
from tqdm import tqdm
from yaspin import yaspin

OUTPUT_DIR = "downloads"
FFMPEG_PATH = r"C:\Users\djniz\anaconda3\envs\python3_13\Library\bin"

def make_progress_hook():
    pbar = None
    def hook(d):
        nonlocal pbar
        if d['status'] == 'downloading':
            if pbar is None:
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                pbar = tqdm(total=total, unit='B', unit_scale=True, desc=d.get('filename', 'downloading'))
            pbar.n = d.get('downloaded_bytes', 0)
            pbar.refresh()
        elif d['status'] == 'finished':
            if pbar:
                pbar.close()
                pbar = None
    return hook

# --- Download Playlist ---
def download_playlist(playlist_url: str, discogs_tagging: bool, album_title: str = None, album_artist: str = None, track_indices: list = None) -> list:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []
    i = 0

    # Determine subfolder
    if album_title and album_artist:
        album_subdir = safe_filename(f"{album_artist} - {album_title}")
        current_output_dir = os.path.join(OUTPUT_DIR, album_subdir)
        os.makedirs(current_output_dir, exist_ok=True)
    else:
        current_output_dir = OUTPUT_DIR

    # use video ID as temporary filename (avoids clashes & illegal chars)
    ydl_opts = {
        "update": True,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "160"
        }],
        "ffmpeg_location": FFMPEG_PATH,
        "ignoreerrors": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [make_progress_hook()],
    }

    with yaspin(text="🔍 Processing playlist items, if the playlist is long, this might take a while...", color="cyan") as spinner:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            entries = info.get("entries", [])
            spinner.ok("✅ ")

            # Filter entries based on track_indices if provided
            if track_indices is not None:
                entries = [entries[i] for i in track_indices if i < len(entries)]

            for index, entry in enumerate(tqdm(entries, desc="Downloading videos", unit="video")):
                if not entry:
                    print("⚠️ Skipping unavailable video (entry is None)")
                    continue

                video_url = entry.get("webpage_url")
                if not video_url:
                    continue

                # Download this entry only
                try:
                    ydl.download([video_url])
                except Exception as e:
                    print(f"⚠️ Failed to download {entry.get('title')}: {e}")
                    continue
                artist, song = normalize_yt_title(entry)
                if not song:
                    i += 1
                    song = "Untitled " + str(i)

                artist = clean_feat(artist)

                # build final polished filename
                if album_title and album_artist:
                    filename = f"{index + 1:02d} - {song}"
                else:
                    filename = f"{artist} - {song}"

                safe_title = clean_title(safe_filename(filename))
                final_path = os.path.join(current_output_dir, f"{safe_title}.mp3")

                if os.path.exists(final_path):
                    final_path = os.path.join(current_output_dir, f"{safe_title}_{entry['id']}.mp3")

                # temp file path from yt-dlp
                temp_path = os.path.join(OUTPUT_DIR, f"{entry['id']}.mp3")

                if os.path.exists(temp_path):
                    try:
                        os.rename(temp_path, final_path)
                        print(f"✅ Saved: {final_path}")

                        # Tag with YouTube metadata
                        tag_from_yt(final_path, entry["webpage_url"], album=album_title, album_artist=album_artist, track_num=index + 1)
                        results.append({"title": safe_title, "file": final_path})
                    except Exception as e:
                        print(f"⚠️ Failed to process {entry.get('title')}: {e}")
                    if discogs_tagging:
                        release = search_discogs_with_prompt(safe_title)
                        if release:
                            tag_mp3_with_discogs(final_path, release)
                        else:
                            print("No release selected. Skipping Discogs tagging.")
                else:
                    print(f"⚠️ File not found after download: {entry.get('title')}")

    return results

def parse_track_selection(selection: str, max_tracks: int) -> list:
    """Parse track selection input which can be individual numbers or ranges like 1-9"""
    if not selection:
        return []

    selected_indices = []
    parts = selection.split(',')

    for part in parts:
        part = part.strip()
        if '-' in part:
            # Handle range like 1-9
            range_parts = part.split('-')
            if len(range_parts) == 2:
                try:
                    start = int(range_parts[0].strip())
                    end = int(range_parts[1].strip())
                    if start <= end:
                        selected_indices.extend(range(start - 1, end))
                    else:
                        print(f"⚠️ Invalid range {part}: start must be <= end")
                except ValueError:
                    print(f"⚠️ Invalid range {part}: must be numbers")
            else:
                print(f"⚠️ Invalid range format {part}")
        else:
            # Handle individual number
            try:
                num = int(part)
                if 1 <= num <= max_tracks:
                    selected_indices.append(num - 1)
                else:
                    print(f"⚠️ Track {num} is out of range (1-{max_tracks})")
            except ValueError:
                print(f"⚠️ Invalid track number {part}")

    return selected_indices

def main():
    playlist_url = input("🎵 Enter the YouTube playlist URL: ").strip()
    if "music.youtube.com" in playlist_url:
        playlist_url = playlist_url.replace("music.youtube.com", "www.youtube.com")
    discogs_tagging = input("🏷  Do you want Discogs tagging? (y|N): ")
    if discogs_tagging.lower() == "y":
        discogs_tagging = True
    else:
        discogs_tagging = False

    if not playlist_url:
        print("⚠️ No URL entered, exiting.")
        return

    is_album = input("💿 Is this an album? (y|N): ").strip().lower() == "y"
    if not is_album:
        results = download_playlist(playlist_url, discogs_tagging)
        if results:
            print("\n✅ Finished processing playlist:")
            for r in results:
                print(f"  • {r['title']} → {r['file']}")
        else:
            print("⚠️ No tracks downloaded or processed.")
        return

    # First, get playlist info to show available tracks
    with yaspin(text="🔍 Processing playlist items, if the playlist is long, this might take a while...", color="cyan") as spinner:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            entries = info.get("entries", [])
            spinner.ok("✅ ")

    if not entries:
        print("⚠️ No tracks found in playlist.")
        return

    print(f"\n📋 Found {len(entries)} tracks in playlist:")
    for i, entry in enumerate(entries):
        title = entry.get("title", "Unknown")
        print(f"  {i + 1}. {title}")

    total_results = []
    processed_indices = set()

    while True:
        default_artist = info.get("uploader") or info.get("channel") or ""
        if not default_artist and entries:
            default_artist = entries[0].get("artist") or entries[0].get("uploader") or entries[0].get("channel") or ""
        default_album = info.get("title", "")
        if default_album.startswith("Album - "):
            default_album = default_album[len("Album - "):]

        artist_prompt = f"\n👤 Enter Album Artist [{default_artist}]: " if default_artist else "\n👤 Enter Album Artist: "
        album_artist = input(artist_prompt).strip()
        if not album_artist and default_artist:
            album_artist = default_artist

        title_prompt = f"💿 Enter Album Title [{default_album}]: " if default_album else "💿 Enter Album Title: "
        album_title = input(title_prompt).strip()
        if not album_title and default_album:
            album_title = default_album

        if not album_artist or not album_title:
            print("⚠️ Both artist and title are required. Please try again.")
            continue

        print("\n📋 Available tracks (select by number or range, e.g., 1-9, 10,12-15):")
        for i, entry in enumerate(entries):
            if i not in processed_indices:
                title = entry.get("title", "Unknown")
                print(f"  {i + 1}. {title}")

        track_selection = input("\n🔢 Enter track numbers/ranges (e.g., 1-9, 10,12-15) or press Enter to select all remaining: ").strip()

        if not track_selection:
            valid_indices = [i for i in range(len(entries)) if i not in processed_indices]
            if not valid_indices:
                print("⚠️ No tracks left in playlist.")
                break
        else:
            selected_indices = parse_track_selection(track_selection, len(entries))
            if not selected_indices:
                print("⚠️ No valid tracks selected. Please try again.")
                continue

            # Validate indices
            valid_indices = [i for i in selected_indices if i not in processed_indices]
            if not valid_indices:
                print("⚠️ No valid tracks selected. Please try again.")
                continue

        # Download selected tracks
        results = download_playlist(playlist_url, discogs_tagging, album_title, album_artist, valid_indices)
        total_results.extend(results)
        processed_indices.update(valid_indices)

        print(f"\n✅ Downloaded {len(valid_indices)} tracks for '{album_artist} - {album_title}'")

        more_albums = input("\n❓ Are there more albums in this playlist? (y|N): ").strip().lower()
        if more_albums != "y":
            break

    if total_results:
        print("\n✅ Finished processing playlist:")
        for r in total_results:
            print(f"  • {r['title']} → {r['file']}")
    else:
        print("⚠️ No tracks downloaded or processed.")

if __name__ == "__main__":
    main()