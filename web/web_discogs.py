# web/web_discogs.py

import os
import sys
from subprocess import run

MUSIC_ROOT = "/data"

def get_music_folders():
    return [
        f for f in os.listdir(MUSIC_ROOT)
        if os.path.isdir(os.path.join(MUSIC_ROOT, f))
    ]

def run_tagger(folder_path):
    cmd = [
        sys.executable,
        "discogs_tagger.py",
        "--path", folder_path,
        "--overwrite", "y",
        "--mode", "a"
    ]

    result = run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr


