import os
import argparse
from mutagen.mp3 import MP3

def find_missing_cues(start_dir):
    missing_cues = []
    
    print(f"Scanning directory: {start_dir}")
    
    for root, dirs, files in os.walk(start_dir):
        # Check if there are any cue files in the current folder
        has_cue = any(f.lower().endswith('.cue') for f in files)
        
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = MP3(file_path)
                    # Check if duration is longer than 25 minutes (1500 seconds)
                    if audio.info.length > 1500:
                        if not has_cue:
                            missing_cues.append(file_path)
                            print(f"Found missing cue: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return missing_cues

def main():
    parser = argparse.ArgumentParser(description="Find MP3s longer than 25 minutes without a CUE file in the same folder.")
    parser.add_argument("path", nargs="?", default=os.getcwd(), help="Root directory to scan (default: current directory)")
    args = parser.parse_args()

    missing_cues = find_missing_cues(args.path)

    report_file = "missing_cues_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        for path in missing_cues:
            f.write(f"{path}\n")
    
    print(f"\nScan complete. Found {len(missing_cues)} files. Report saved to {report_file}")

if __name__ == "__main__":
    main()
