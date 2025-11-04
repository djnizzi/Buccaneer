import os
from tqdm import tqdm

def find_empty_mp3s(folder_path, output_file="empty_mp3s.txt"):
    """
    Recursively searches for .mp3 files in folder_path and writes the paths
    of empty (0-byte) files into output_file.
    """
    empty_files = []

    for root, _, files in os.walk(folder_path):
        for file in tqdm(files):
            if file.lower().endswith(".mp3"):
                file_path = os.path.join(root, file)
                try:
                    if os.path.getsize(file_path) == 0:
                        empty_files.append(file_path)
                except OSError as e:
                    print(f"⚠️ Could not access {file_path}: {e}")

    with open(output_file, "w", encoding="utf-8") as out:
        if empty_files:
            for path in empty_files:
                out.write(path + "\n")
            print(f"✅ Found {len(empty_files)} empty MP3 file(s). Paths saved to '{output_file}'.")
        else:
            out.write("No empty MP3 files found.\n")
            print("✅ No empty MP3 files found.")


if __name__ == "__main__":
    folder = input("Enter the folder path to search for empty .mp3 files: ").strip()
    if not os.path.isdir(folder):
        print("❌ The specified path is not a valid directory.")
    else:
        find_empty_mp3s(folder)
