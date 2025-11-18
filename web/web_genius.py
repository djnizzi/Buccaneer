import os
import sys
from subprocess import run

def run_genius(folder_path):
    if not os.path.exists(folder_path):
        return f"❌ Folder does not exist inside container: {folder_path}"

    cmd = [
        sys.executable,
        "/app/genius.py",
        "--path", folder_path
    ]

    result = run(cmd, capture_output=True, text=True)
    return (result.stdout or "") + "\n" + (result.stderr or "")