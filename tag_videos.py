import os
import subprocess

DOWNLOAD_DIR = r"W:\MusicClips\NowWatching"
FFMPEG_PATH = r"C:\Users\djniz\anaconda3\envs\python3_13\Library\bin"

for filename in os.listdir(DOWNLOAD_DIR):
    if not filename.lower().endswith(".mp4"):
        continue
    base = os.path.splitext(filename)[0]
    mp4_path = os.path.join(DOWNLOAD_DIR, filename)
    jpg_path = os.path.join(DOWNLOAD_DIR, base + ".jpg")

    # convert WebP/PNG thumbnail to JPG if needed
    if not os.path.exists(jpg_path):
        for ext in ["webp", "png"]:
            thumb_path = os.path.join(DOWNLOAD_DIR, base + f".{ext}")
            if os.path.exists(thumb_path):
                jpg_path = os.path.join(DOWNLOAD_DIR, base + ".jpg")
                subprocess.run([os.path.join(FFMPEG_PATH, "ffmpeg.exe"), "-y", "-i", thumb_path, jpg_path])
                break

    if os.path.exists(jpg_path):
        print(f"Embedding thumbnail for {filename}")
        temp_output = os.path.join(DOWNLOAD_DIR, base + "_thumb.mp4")
        subprocess.run([
            os.path.join(FFMPEG_PATH, "ffmpeg.exe"),
            "-i", mp4_path,
            "-i", jpg_path,
            "-map", "0",
            "-map", "1",
            "-c", "copy",
            "-disposition:v:1", "attached_pic",
            temp_output
        ])
        # Replace original MP4
        os.replace(temp_output, mp4_path)

print("\n--- Cleaning up image files ---")
for filename in os.listdir(DOWNLOAD_DIR):
    if filename.lower().endswith(('.jpg', '.webp')):
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        try:
            os.remove(file_path)
            print(f"Deleted: {filename}")
        except OSError as e:
            print(f"Error deleting {filename}: {e}")

