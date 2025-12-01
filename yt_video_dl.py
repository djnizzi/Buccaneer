import os
import sys
import logging
from datetime import datetime
import yt_dlp
from utils import strip_video_tags

DOWNLOAD_DIR = r"W:\MusicClips\NowWatching"
LOG_DIR = "logs"
ARCHIVE_FILE = "downloaded_ids.txt"
FFMPEG_PATH = r"C:\Users\djniz\anaconda3\envs\python3_13\Library\bin"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Logging
log_filename = os.path.join(LOG_DIR, f"download_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
console = logging.getLogger()
console.addHandler(logging.StreamHandler(sys.stdout))

class MyYDL(yt_dlp.YoutubeDL):
    def prepare_filename(self, info_dict, *args, **kwargs):
        info = info_dict.copy()
        if "title" in info:
            info["title"] = strip_video_tags(info["title"])
        return super().prepare_filename(info, *args, **kwargs)

def progress_hook(d):
    status = d.get("status")
    if status == "downloading":
        pct = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("_eta_str", "").strip()
        filename = os.path.basename(d.get("filename", ""))
        logging.debug(f"Downloading {filename}: {pct} {speed} ETA {eta}")
    elif status == "finished":
        filename = os.path.basename(d.get("filename", ""))
        logging.info(f"Finished downloading {filename}")

def download_playlist(url):
    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "ffmpeg_location": FFMPEG_PATH,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "progress_hooks": [progress_hook],
        "download_archive": ARCHIVE_FILE,
        "ignoreerrors": True,
    }

    with MyYDL(ydl_opts) as ydl:
        ydl.download([url])

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else input("Enter playlist URL: ").strip()
    if not url:
        sys.exit(1)
    download_playlist(url)
