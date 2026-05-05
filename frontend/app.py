from flask import Flask, render_template, request, send_file
import subprocess
import shlex
import os

app = Flask(__name__)

BASE_PATH = "/app/backend"
FILM_PATH = "/app/Film"
SERIE_PATH = "/app/SerieTV"
PROGRESS_PATH = os.path.join(os.path.dirname(__file__), "progress.json")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        anime_url = request.form.get("anime_url", "").strip()
        start = request.form.get("start", "").strip()
        end = request.form.get("end", "").strip()
        episodes = request.form.get("episodes", "").strip()
        tipo = request.form.get("tipo")

        if not anime_url:
            return render_template("index.html", message="❌ Errore: URL mancante")

        if episodes and (start or end):
            return render_template("index.html", message="❌ Errore: usa episodes oppure start/end, non entrambi")

        if tipo == "film":
            custom_path = FILM_PATH
        else:
            custom_path = SERIE_PATH

        cmd_parts = [
            "cd", BASE_PATH, "&&",
            "python3", "anime_downloader.py",
            shlex.quote(anime_url),
            "--custom-path", shlex.quote(custom_path)
        ]

        if episodes:
            cmd_parts.append("--episodes")
            cmd_parts.append(shlex.quote(episodes))
        else:
            if start:
                cmd_parts.append("--start")
                cmd_parts.append(shlex.quote(start))
            if end:
                cmd_parts.append("--end")
                cmd_parts.append(shlex.quote(end))

        command = " ".join(cmd_parts)

        try:
            subprocess.Popen(["bash", "-c", command])
        except Exception as e:
            return render_template("index.html", message=f"❌ Errore durante l'esecuzione: {e}")

        return render_template("index.html", message="✅ Download avviato!")

    return render_template("index.html")

@app.route("/progress.json")
def progress():
    return send_file(PROGRESS_PATH, mimetype="application/json")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)
