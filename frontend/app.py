from flask import Flask, render_template, request, send_file, jsonify, g
import subprocess
import shlex
import os
import sqlite3
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BASE_PATH = "/app/backend"
FILM_PATH = "/app/Film"
SERIE_PATH = "/app/SerieTV"
PROGRESS_PATH = os.path.join(os.path.dirname(__file__), "progress.json")
DB_PATH = os.environ.get("SCHEDULES_DB_PATH", "/app/data/schedules.db")

ITALIAN_WEEKDAYS = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]

# Orario a cui lo scheduler controlla le programmazioni giornaliere.
# Configurabile via variabile d'ambiente SCHEDULER_TIME nel formato "HH:MM"
# (es. SCHEDULER_TIME=06:00 nel file .env). Se assente o malformata, si usa 08:00.
DEFAULT_SCHEDULER_TIME = "08:00"


def get_scheduler_time():
    """Legge e valida SCHEDULER_TIME dall'ambiente, restituendo (hour, minute)."""
    raw = os.environ.get("SCHEDULER_TIME", DEFAULT_SCHEDULER_TIME).strip()

    try:
        hour_str, minute_str = raw.split(":")
        hour, minute = int(hour_str), int(minute_str)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        print(f"[scheduler] SCHEDULER_TIME='{raw}' non valido, uso il default {DEFAULT_SCHEDULER_TIME}.")
        hour, minute = (int(x) for x in DEFAULT_SCHEDULER_TIME.split(":"))

    return hour, minute


# ══════════════════════════ DB ══════════════════════════

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_url TEXT NOT NULL,
            start_episode INTEGER NOT NULL,
            day_of_week TEXT NOT NULL CHECK (
                day_of_week IN ('lunedi','martedi','mercoledi','giovedi','venerdi','sabato','domenica')
            ),
            end_date DATE,
            custom_folder TEXT,
            last_downloaded_episode INTEGER DEFAULT 0,
            consecutive_failures INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migrazione: se il DB esisteva già da prima di questa colonna, aggiungila
    # senza perdere le programmazioni già salvate.
    existing_columns = {row[1] for row in db.execute("PRAGMA table_info(scheduled_downloads)")}
    if "consecutive_failures" not in existing_columns:
        db.execute("ALTER TABLE scheduled_downloads ADD COLUMN consecutive_failures INTEGER DEFAULT 0")
        print("[init_db] Migrazione: aggiunta colonna consecutive_failures.")

    db.commit()
    db.close()


def row_to_dict(row):
    return {
        "id": row["id"],
        "anime_url": row["anime_url"],
        "start_episode": row["start_episode"],
        "day_of_week": row["day_of_week"],
        "end_date": row["end_date"],
        "custom_folder": row["custom_folder"],
        "last_downloaded_episode": row["last_downloaded_episode"],
        "consecutive_failures": row["consecutive_failures"],
    }


# ══════════════════════════ Download (condiviso tra form manuale e scheduler) ══════════════════════════

def build_download_command(anime_url, tipo, start=None, end=None, episodes=None, custom_folder=None):
    custom_path = FILM_PATH if tipo == "film" else SERIE_PATH

    cmd_parts = [
        "cd", BASE_PATH, "&&",
        "python3", "anime_downloader.py",
        shlex.quote(anime_url),
        "--custom-path", shlex.quote(custom_path),
    ]

    if episodes:
        cmd_parts += ["--episodes", shlex.quote(str(episodes))]
    else:
        if start:
            cmd_parts += ["--start", shlex.quote(str(start))]
        if end:
            cmd_parts += ["--end", shlex.quote(str(end))]

    if custom_folder:
        cmd_parts += ["--subfolder", shlex.quote(custom_folder)]

    return " ".join(cmd_parts)


def run_download(anime_url, tipo, start=None, end=None, episodes=None, custom_folder=None):
    """Avvia il download in background, senza attendere l'esito (usato dal form manuale)."""
    command = build_download_command(anime_url, tipo, start, end, episodes, custom_folder)
    subprocess.Popen(["bash", "-c", command])


def run_download_and_wait(anime_url, tipo, episodes, custom_folder=None):
    """Avvia il download e ASPETTA che finisca, restituendo True solo se ha trovato
    ed effettivamente scaricato l'episodio richiesto (usato dallo scheduler).

    Il codice di uscita 2 da anime_downloader.py significa "nessun episodio trovato"
    (es. non ancora uscito): in quel caso NON va considerato un successo, così lo
    scheduler ritenterà lo stesso episodio la prossima volta.
    """
    command = build_download_command(anime_url, tipo, episodes=episodes, custom_folder=custom_folder)
    result = subprocess.run(["bash", "-c", command], capture_output=True, text=True)

    if result.returncode == 0:
        return True, "ok"
    if result.returncode == 2:
        return False, "episodio non ancora disponibile"
    return False, f"errore (exit code {result.returncode}): {result.stderr[-500:]}"


# ══════════════════════════ Scheduler ══════════════════════════

MAX_CONSECUTIVE_FAILURES = 4


def check_and_run_scheduled_downloads():
    """Eseguita una volta al giorno: controlla schedules.db e avvia i download del giorno."""
    today_name = ITALIAN_WEEKDAYS[date.today().weekday()]
    today = date.today()

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT * FROM scheduled_downloads WHERE active = 1 AND day_of_week = ?",
        (today_name,),
    ).fetchall()

    for row in rows:
        # Salta se la programmazione è già scaduta
        if row["end_date"]:
            end_date = datetime.strptime(row["end_date"], "%Y-%m-%d").date()
            if today > end_date:
                db.execute("DELETE FROM scheduled_downloads WHERE id = ?", (row["id"],))
                db.commit()
                print(
                    f"[scheduler] id={row['id']}: programmazione scaduta "
                    f"(end_date={row['end_date']}), eliminata."
                )
                continue

        next_episode = row["last_downloaded_episode"] + 1 if row["last_downloaded_episode"] else row["start_episode"]

        print(f"[scheduler] Avvio download programmato: id={row['id']} url={row['anime_url']} episodio={next_episode} cartella={row['custom_folder']}")

        try:
            success, detail = run_download_and_wait(
                row["anime_url"], "serie", episodes=next_episode, custom_folder=row["custom_folder"]
            )
            if success:
                db.execute(
                    """
                    UPDATE scheduled_downloads
                    SET last_downloaded_episode = ?, consecutive_failures = 0
                    WHERE id = ?
                    """,
                    (next_episode, row["id"]),
                )
                db.commit()
                print(f"[scheduler] id={row['id']}: episodio {next_episode} scaricato con successo.")
            else:
                failures = row["consecutive_failures"] + 1

                if failures >= MAX_CONSECUTIVE_FAILURES:
                    db.execute("DELETE FROM scheduled_downloads WHERE id = ?", (row["id"],))
                    db.commit()
                    print(
                        f"[scheduler] id={row['id']}: episodio {next_episode} non trovato per "
                        f"{failures} volte consecutive ({detail}). Programmazione eliminata "
                        "(probabile fine stagione)."
                    )
                else:
                    db.execute(
                        "UPDATE scheduled_downloads SET consecutive_failures = ? WHERE id = ?",
                        (failures, row["id"]),
                    )
                    db.commit()
                    print(
                        f"[scheduler] id={row['id']}: episodio {next_episode} NON scaricato "
                        f"({detail}). Tentativo {failures}/{MAX_CONSECUTIVE_FAILURES}. Riproverò la prossima volta."
                    )
        except Exception as e:
            print(f"[scheduler] Errore avviando il download per id={row['id']}: {e}")

    db.close()


scheduler = BackgroundScheduler()
# Ogni giorno, all'orario configurato (default 08:00, sovrascrivibile con
# SCHEDULER_TIME nel .env), controlla se c'è qualche programmazione da avviare.
_scheduler_hour, _scheduler_minute = get_scheduler_time()
scheduler.add_job(check_and_run_scheduled_downloads, "cron", hour=_scheduler_hour, minute=_scheduler_minute)
print(f"[scheduler] Job giornaliero impostato alle {_scheduler_hour:02d}:{_scheduler_minute:02d}.")


# ══════════════════════════ Route esistenti ══════════════════════════

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

        try:
            run_download(anime_url, tipo, start=start or None, end=end or None, episodes=episodes or None)
        except Exception as e:
            return render_template("index.html", message=f"❌ Errore durante l'esecuzione: {e}")

        return render_template("index.html", message="✅ Download avviato!")

    return render_template("index.html")


@app.route("/progress.json")
def progress():
    return send_file(PROGRESS_PATH, mimetype="application/json")


# ══════════════════════════ Route nuove: /api/schedules ══════════════════════════

@app.route("/api/schedules", methods=["GET"])
def list_schedules():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM scheduled_downloads WHERE active = 1 ORDER BY created_at DESC"
    ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/schedules", methods=["POST"])
def create_schedule():
    data = request.get_json()

    required = ["anime_url", "start_episode", "day_of_week"]
    if not data or not all(data.get(k) for k in required):
        return jsonify({"error": "Campi obbligatori mancanti"}), 400

    if data["day_of_week"] not in ITALIAN_WEEKDAYS:
        return jsonify({"error": "Giorno della settimana non valido"}), 400

    db = get_db()
    cur = db.execute(
        """
        INSERT INTO scheduled_downloads (anime_url, start_episode, day_of_week, end_date, custom_folder)
        VALUES (?, ?, ?, ?, ?)
        """,
        (data["anime_url"], data["start_episode"], data["day_of_week"], data.get("end_date"), data.get("custom_folder")),
    )
    db.commit()

    new_row = db.execute(
        "SELECT * FROM scheduled_downloads WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(row_to_dict(new_row)), 201


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    db = get_db()
    db.execute("DELETE FROM scheduled_downloads WHERE id = ?", (schedule_id,))
    db.commit()
    return "", 204


if __name__ == "__main__":
    init_db()
    scheduler.start()
    app.run(debug=False, host="0.0.0.0", port=5050)
