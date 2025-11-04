import os

def collect_cue_files(folder_path, output_file="all_cues.txt"):
    """
    Recursively searches for .cue files in folder_path and writes their paths
    and contents into output_file.
    """
    with open(output_file, "w", encoding="utf-8") as out:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(".cue"):
                    cue_path = os.path.join(root, file)
                    out.write(f"=== FILE: {cue_path} ===\n")
                    try:
                        with open(cue_path, "r", encoding="utf-8", errors="replace") as cue_file:
                            content = cue_file.read()
                        out.write(content + "\n\n")
                    except Exception as e:
                        out.write(f"[Error reading {cue_path}: {e}]\n\n")
    print(f"✅ Done! All .cue file contents have been written to '{output_file}'.")


if __name__ == "__main__":
    folder = input("Enter the folder path to search for .cue files: ").strip()
    if not os.path.isdir(folder):
        print("❌ The specified path is not a valid directory.")
    else:
        collect_cue_files(folder)
