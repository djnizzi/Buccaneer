from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/tagger")
def tagger_page():
    return render_template("tagger.html")

@app.route("/another")
def another_page():
    return render_template("another.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
