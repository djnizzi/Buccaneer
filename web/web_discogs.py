from flask import Flask, render_template, request
import os
from subprocess import run
import sys

def run_tagger(folder_path):
    cmd = [
        sys.executable,
        "tagger.py",
        "--path", folder_path,
        "--overwrite", "y",
        "--mode", "a"
    ]

    result = run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr

app = Flask(__name__)

MUSIC_ROOT = "/data"

@app.route("/", methods=["GET", "POST"])
def index():
    folders = [f for f in os.listdir(MUSIC_ROOT) if os.path.isdir(os.path.join(MUSIC_ROOT, f))]
    selected_folder = None
    logs = ""

    if request.method == "POST":
        selected_folder = request.form["folder"]
        full_path = os.path.join(MUSIC_ROOT, selected_folder)
        # run your existing logic here
        logs = run_tagger(full_path)

    return render_template("index.html", folders=folders, selected_folder=selected_folder, logs=logs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
