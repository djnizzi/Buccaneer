from flask import Flask, render_template, request, Response, stream_with_context
from web.web_discogs import run_tagger
# from web.web_genius import run_genius
from genius import genius_tagger
import json

MUSIC_ROOT = "/data"
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/progress_stream")
def progress_stream():
    user_param = request.args.get('param')
    fullpath = f"{MUSIC_ROOT}/{user_param.strip()}"

    @stream_with_context
    def generate():
        completed = 0
        current_total = 1

        # 1. Iterate over your existing tagger (Start msg, Files, Summary msg)
        for step, total_steps, message in genius_tagger(fullpath):
            current_total = total_steps
            completed += step

            if current_total > 0:
                percent = int((completed / current_total) * 100)
            else:
                percent = 0

            # Send data with "complete": false
            # This ensures the frontend keeps listening even if percent is 100
            data = {
                "percent": percent,
                "message": message,
                "complete": False  # <--- NEW FLAG
            }
            yield f"data:{json.dumps(data)}\n\n"

        # 2. The loop is finished (Summary has been sent).
        # Now send the kill signal.
        final_data = {
            "percent": 100,
            "message": "",
            "complete": True  # <--- This tells JS to stop
        }
        yield f"data:{json.dumps(final_data)}\n\n"

    return Response(generate(), mimetype='text/event-stream')


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

@app.route("/genius_tagger", methods=["GET"])
def genius_page():
    # We removed POST logic here because the SSE handles the execution now.
    # This prevents the "Double Run" issue.
    return render_template(
        "genius_tagger.html",
        selected_folder="",
        logs=""
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
