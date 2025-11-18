from flask import Flask, render_template, request
from web.web_discogs import get_music_folders, run_tagger, MUSIC_ROOT

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/discogs_tagger", methods=["GET", "POST"])
def discogs_page():
    folders = get_music_folders()
    selected_folder = None
    logs = ""

    if request.method == "POST":
        selected_folder = request.form["folder"]
        full_path = f"{MUSIC_ROOT}/{selected_folder}"
        logs = run_tagger(full_path)

    return render_template(
        "discogs_tagger.html",
        folders=folders,
        selected_folder=selected_folder,
        logs=logs
    )

@app.route("/another")
def another_page():
    return render_template("another.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
