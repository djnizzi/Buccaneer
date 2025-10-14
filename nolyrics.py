import os
import glob
from mutagen.id3 import ID3, ID3NoHeaderError

def has_lyrics(filepath: str) -> bool:
    """Check if MP3 already has lyrics tag."""
    try:
        tags = ID3(filepath)
        return any(frame.FrameID == "USLT" and frame.text.strip() for frame in tags.values())
    except ID3NoHeaderError:
        return False
def no_lyrics_list(without_lyrics):
    print("\n❌ Files missing lyrics:")
    for f in without_lyrics:
        print("  -", os.path.basename(f))

def check_lyrics(folder: str):
    """Count MP3s with and without lyrics in a folder."""
    mp3_files = glob.glob(os.path.join(folder, "*.mp3"))
    with_lyrics = []
    without_lyrics = []

    for file in mp3_files:
        if has_lyrics(file):
            with_lyrics.append(file)
        else:
            without_lyrics.append(file)

    print(f"\n📂 Folder: {folder}")
    print(f"🎧 Total MP3 files: {len(mp3_files)}")
    print(f"✅ With lyrics: {len(with_lyrics)}")
    print(f"❌ Without lyrics: {len(without_lyrics)}")
    # if without_lyrics:
    #     no_lyrics_list(without_lyrics)

if __name__ == "__main__":
    folder = input("📂 Enter folder with MP3 files: ").strip()
    check_lyrics(folder)
