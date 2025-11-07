import os
from tqdm import tqdm

def find_pngs(folder_path, output_file="png_artwork.txt"):

    empty_files = []

    for root, _, files in tqdm(os.walk(folder_path)):
        for file in files:
            if file.lower().endswith(".png"):
                file_path = os.path.join(root, file)

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
        find_pngs(folder)