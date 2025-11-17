import os
import shutil

SOURCE_ROOT = r"X:"
DEST_ROOT   = r"X:\documents\cuebackups"
LOG_FILE    = r"X:\documents\cuebackups\move_log.txt"

def main():
    moved = 0
    skipped = 0

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        for root, dirs, files in os.walk(SOURCE_ROOT):
            for f in files:
                if not f.lower().endswith(".cue.bak"):
                    continue

                src = os.path.join(root, f)

                # Compute relative path inside SOURCE_ROOT
                rel = os.path.relpath(src, SOURCE_ROOT)
                dest = os.path.join(DEST_ROOT, rel)

                # Make sure destination folder exists
                os.makedirs(os.path.dirname(dest), exist_ok=True)

                if os.path.exists(dest):
                    log.write(f"SKIPPED (exists): {src}\n")
                    skipped += 1
                    continue

                # Move the file
                shutil.move(src, dest)
                log.write(f"MOVED: {src} → {dest}\n")
                moved += 1

    print(f"Done. Moved {moved} files. Skipped {skipped}.")

if __name__ == "__main__":
    main()
