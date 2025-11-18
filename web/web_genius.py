import sys
from subprocess import run

def run_genius(folder_path):
    cmd = [
        sys.executable,
        "genius.py",
        "--path", folder_path
    ]

    result = run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr