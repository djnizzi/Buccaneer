import os
import shutil

def restore_from_log(log_path="processed_log.txt"):
    if not os.path.exists(log_path):
        print(f"Log file '{log_path}' not found.")
        return

    restore_log = "restore_log.txt"
    restored_count = 0
    skipped_count = 0

    with open(log_path, "r", encoding="utf-8") as log, open(restore_log, "w", encoding="utf-8") as rlog:
        for line in log:
            cue_path = line.strip()
            if not cue_path:
                continue

            bak_path = cue_path + ".bak"

            if os.path.exists(bak_path):
                try:
                    shutil.copy2(bak_path, cue_path)
                    rlog.write(f"RESTORED: {cue_path}\n")
                    restored_count += 1
                except Exception as e:
                    rlog.write(f"ERROR restoring {cue_path}: {e}\n")
            else:
                rlog.write(f"NO BAK FOUND (skipped): {cue_path}\n")
                skipped_count += 1

    print(f"Done. Restored: {restored_count}, Skipped: {skipped_count}")
    print(f"Details written to {restore_log}")

if __name__ == "__main__":
    restore_from_log()
