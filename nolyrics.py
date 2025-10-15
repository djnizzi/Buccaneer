import os
import glob
from mutagen.id3 import ID3, ID3NoHeaderError
from tqdm import tqdm
from utils import safe_filename


def has_lyrics(filepath: str) -> bool:
    """Check if MP3 already has lyrics tag."""
    try:
        tags = ID3(filepath)
        return any(frame.FrameID == "USLT" and frame.text.strip() for frame in tags.values())
    except ID3NoHeaderError:
        return False

def safe_path(path):
    """Return relative path if possible, else absolute path."""
    try:
        return os.path.relpath(path)
    except ValueError:
        return os.path.abspath(path)

def no_lyrics_list(without_lyrics):
    print("\n❌ Files missing lyrics:")
    for f in without_lyrics:
        print("  -", safe_path(f))

def export_no_lyrics(without_lyrics, export_path):
    """Save the list of MP3s without lyrics to a text file."""
    with open(export_path, "w", encoding="utf-8") as f:
        f.write("❌ Files missing lyrics:\n")
        for file in without_lyrics:
            f.write(safe_path(file) + "\n")
    print(f"\n💾 Missing-lyrics list saved to: {os.path.abspath(export_path)}")

def check_lyrics(folder: str, show_list: bool = False, export: bool = False):
    """Count MP3s with and without lyrics in a folder (including subfolders)."""
    mp3_files = glob.glob(os.path.join(folder, "**", "*.mp3"), recursive=True)
    with_lyrics = []
    without_lyrics = []

    for file in tqdm(mp3_files, desc="Scanning MP3 files"):
        if has_lyrics(file):
            with_lyrics.append(file)
        else:
            without_lyrics.append(file)

    print(f"\n📂 Folder: {folder}")
    print(f"🎧 Total MP3 files: {len(mp3_files)}")
    print(f"✅ With lyrics: {len(with_lyrics)}")
    print(f"❌ Without lyrics: {len(without_lyrics)}")

    if show_list and without_lyrics:
        no_lyrics_list(without_lyrics)

    if export and without_lyrics:
        export_no_lyrics(without_lyrics, safe_filename(folder) + ".txt")

if __name__ == "__main__":
    folder = input("📂 Enter folder with MP3 files: ").strip()
    choice = input("📋 Show list of files without lyrics? (y/n): ").strip().lower()
    save_choice = input("💾 Export missing-lyrics list to file? (y/n): ").strip().lower()
    check_lyrics(folder, show_list=(choice == "y"), export=(save_choice == "y"))




