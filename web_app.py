from flask import Flask, render_template, request
from web.web_discogs import run_tagger
from web.web_genius import run_genius
MUSIC_ROOT = "/data"
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/discogs_tagger", methods=["GET", "POST"])
def discogs_page():
    selected_folder = ""
    logs = ""
    overwrite = "n"
    mode = "a"

    if request.method == "POST":
        selected_folder = request.form["folder"]
        overwrite = request.form.get("overwrite", "n")
        mode = request.form.get("mode", "a")

        full_path = f"{MUSIC_ROOT}/{selected_folder.strip()}"

        logs = run_tagger(full_path, overwrite, mode)

    return render_template(
        "discogs_tagger.html",
        selected_folder=selected_folder,
        overwrite=overwrite,
        mode=mode,
        logs=logs
    )

@app.route("/genius_tagger", methods=["GET", "POST"])
def genius_page():
    selected_folder = ""
    logs = ""

    if request.method == "POST":
        selected_folder = request.form.get("folder", "").strip()

        if not selected_folder:
            logs = "❌ No folder provided."
        else:
            full_path = f"{MUSIC_ROOT}/{selected_folder}"
            logs = run_genius(full_path)


    return render_template(
        "genius_tagger.html",
        selected_folder=selected_folder,
        logs=logs
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
