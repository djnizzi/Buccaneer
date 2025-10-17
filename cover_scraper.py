import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from pathlib import Path


def extract_covers(source_folder, dest_folder, image_format="jpg"):
    source_folder = Path(source_folder)
    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith(".mp3"):
                mp3_path = Path(root) / file
                try:
                    audio = MP3(mp3_path, ID3=ID3)

                    if audio.tags is None:
                        continue

                    for tag in audio.tags.values():
                        if isinstance(tag, APIC):  # Album art
                            img_data = tag.data
                            img_ext = "jpg" if tag.mime == "image/jpeg" else "png"
                            img_ext = image_format if image_format in ["jpg", "png"] else img_ext

                            out_name = mp3_path.stem + f".{img_ext}"
                            out_path = dest_folder / out_name

                            with open(out_path, "wb") as img_file:
                                img_file.write(img_data)

                            print(f"Saved cover for {mp3_path.name}")
                            break
                except Exception as e:
                    print(f"Error reading {mp3_path}: {e}")


if __name__ == "__main__":
    # Example usage:
    source = input("📂 Enter folder with MP3 files: ").strip()
    dest = input("📂 Enter folder where to save covers: ").strip()
    extract_covers(source, dest, image_format="jpg")
