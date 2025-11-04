import os
import yt_dlp
from utils import normalize_yt_title, safe_filename, clean_feat, clean_title
from discogs import search_discogs_with_prompt
from tag import tag_mp3_with_discogs, tag_from_yt

OUTPUT_DIR = "downloads"
FFMPEG_PATH = r"C:\Users\djniz\anaconda3\envs\python3_13\Library\bin"

# --- Download Playlist ---
def download_playlist(playlist_url: str) -> list:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []
    i = 0

    # use video ID as temporary filename (avoids clashes & illegal chars)
    ydl_opts = {
        "update": True,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128"
        }],
        "ffmpeg_location": FFMPEG_PATH,
        "ignoreerrors": True,
        "noplaylist": True,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get("entries", [])

        for entry in entries:
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
            safe_title = safe_filename(f"{artist} - {song}")
            safe_title = clean_title(safe_title)
            final_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp3")

            # temp file path from yt-dlp
            temp_path = os.path.join(OUTPUT_DIR, f"{entry['id']}.mp3")

            if os.path.exists(temp_path):
                try:
                    os.rename(temp_path, final_path)
                    print(f"✅ Saved as {safe_title}.mp3")

                    # Tag with YouTube metadata
                    tag_from_yt(final_path, entry["webpage_url"])
                    results.append({"title": safe_title, "file": final_path})
                except Exception as e:
                    print(f"⚠️ Failed to process {entry.get('title')}: {e}")
                release = search_discogs_with_prompt(safe_title)
                if release:
                    tag_mp3_with_discogs(final_path, release)
                else:
                    print("No release selected. Skipping Discogs tagging.")
            else:
                print(f"⚠️ File not found after download: {entry.get('title')}")

    return results

def main():
    playlist_url = input("🎵 Enter the YouTube playlist URL: ").strip()
    if not playlist_url:
        print("⚠️ No URL entered, exiting.")
        return

    results = download_playlist(playlist_url)

    if results:
        print("\n✅ Finished processing playlist:")
        for r in results:
            print(f"  • {r['title']} → {r['file']}")
    else:
        print("⚠️ No tracks downloaded or processed.")

if __name__ == "__main__":
    main()