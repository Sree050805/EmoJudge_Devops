from flask import (
    Flask,
    render_template,
    request,
    Response,
    redirect,
    url_for,
    session,
    send_from_directory,
    jsonify
)
import sqlite3
import datetime
import requests
import os
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash
import jwt as pyjwt


# ── Application Configuration ─────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR),
    static_folder=str(BASE_DIR)
)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "emojudge_secret_2025")
JWT_SECRET = os.getenv("JWT_SECRET", "emojudge_jwt_secret")

# Local development:
# http://127.0.0.1:8000
#
# Docker/Kubernetes can override this using the FASTAPI_URL environment variable.
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")


# ── DB Helpers ────────────────────────────────────────────────────────────────

def get_db():
    db_path = BASE_DIR / "users.db"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attorney_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS case_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attorney_id TEXT NOT NULL,
            video TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    conn.commit()
    conn.close()


init_db()


# ── Auth Helpers ──────────────────────────────────────────────────────────────

def make_jwt(attorney_id: str) -> str:
    payload = {
        "sub": attorney_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8),
    }

    return pyjwt.encode(
        payload,
        JWT_SECRET,
        algorithm="HS256"
    )


def verify_jwt(token: str):
    try:
        return pyjwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

    except pyjwt.PyJWTError:
        return None


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):

        if "attorney_id" not in session:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated


# ── Health Check ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "emojudge-web"
    }), 200


# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        attorney_id = request.form["attorney_id"]
        password = request.form["password"]

        conn = get_db()

        row = conn.execute(
            "SELECT password FROM users WHERE attorney_id=?",
            (attorney_id,)
        ).fetchone()

        conn.close()

        if row and check_password_hash(row["password"], password):

            session["attorney_id"] = attorney_id
            session["jwt"] = make_jwt(attorney_id)

            return redirect("/videos1")

        return render_template(
            "login.html",
            error="Invalid Attorney ID or Password."
        )

    return render_template(
        "login.html",
        error=None
    )


@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        attorney_id = request.form["attorney_id"]

        password = generate_password_hash(
            request.form["password"]
        )

        email = request.form["email"]

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (attorney_id, password, email)
                VALUES (?, ?, ?)
                """,
                (
                    attorney_id,
                    password,
                    email
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return render_template(
                "signup.html",
                error="Attorney ID already exists."
            )

        conn.close()

        return redirect("/")

    return render_template(
        "signup.html",
        error=None
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    message = ""
    success = False

    if request.method == "POST":

        email = request.form["email"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if user:

            message = "Reset link sent to your email."
            success = True

        else:

            try:

                conn.execute(
                    """
                    INSERT INTO users
                    (attorney_id, password, email)
                    VALUES (?, ?, ?)
                    """,
                    (
                        "",
                        "",
                        email
                    )
                )

                conn.commit()

                message = "Email registered. Reset link sent."
                success = True

            except sqlite3.IntegrityError:

                message = "Error processing request."

        conn.close()

    return render_template(
        "forgot-password.html",
        message=message,
        success=success
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ── Video Routes ──────────────────────────────────────────────────────────────

@app.route("/videos/<filename>")
def serve_video(filename):

    return send_from_directory(
        str(BASE_DIR),
        filename
    )


@app.route("/videos1")
@login_required
def videos1():

    return render_template(
        "videos1.html"
    )


# ── JWT API Token Endpoint (Flutter / Mobile) ────────────────────────────────

@app.route("/api/token", methods=["POST"])
def api_token():

    data = request.get_json()

    conn = get_db()

    row = conn.execute(
        "SELECT password FROM users WHERE attorney_id=?",
        (
            data.get("attorney_id"),
        )
    ).fetchone()

    conn.close()

    if row and check_password_hash(
        row["password"],
        data.get("password", "")
    ):

        return jsonify({
            "token": make_jwt(
                data["attorney_id"]
            )
        })

    return jsonify({
        "error": "Invalid credentials"
    }), 401


# ── Case Notes API ────────────────────────────────────────────────────────────

@app.route("/api/notes", methods=["GET", "POST"])
@login_required
def case_notes():

    attorney_id = session["attorney_id"]

    conn = get_db()

    if request.method == "POST":

        data = request.get_json()

        conn.execute(
            """
            INSERT INTO case_notes
            (attorney_id, video, note)
            VALUES (?, ?, ?)
            """,
            (
                attorney_id,
                data["video"],
                data["note"]
            )
        )

        conn.commit()
        conn.close()

        return jsonify({
            "status": "saved"
        })

    rows = conn.execute(
        """
        SELECT
            id,
            video,
            note,
            created_at
        FROM case_notes
        WHERE attorney_id=?
        ORDER BY created_at DESC
        """,
        (
            attorney_id,
        )
    ).fetchall()

    conn.close()

    return jsonify([
        dict(r) for r in rows
    ])


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
@login_required
def delete_note(note_id):

    conn = get_db()

    conn.execute(
        """
        DELETE FROM case_notes
        WHERE id=? AND attorney_id=?
        """,
        (
            note_id,
            session["attorney_id"]
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "status": "deleted"
    })


# ── Emotion History Proxy ─────────────────────────────────────────────────────

@app.route("/api/emotion_history/<video_name>")
@login_required
def emotion_history(video_name):

    try:

        response = requests.get(
            f"{FASTAPI_URL}/emotion_history/{video_name}",
            timeout=3
        )

        return jsonify(
            response.json()
        )

    except Exception:

        return jsonify({
            "history": []
        })

# ── Emotion Analysis Proxy ────────────────────────────────────────────────────

@app.route("/api/analyze_emotion", methods=["POST"])
@login_required
def analyze_emotion_proxy():
    try:
        response = requests.post(
            f"{FASTAPI_URL}/analyze_emotion/",
            json=request.get_json(),
            timeout=30
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as e:
        return jsonify({
            "error": "AI service unavailable",
            "details": str(e)
        }), 503
# ── Voice Status ──────────────────────────────────────────────────────────────

is_speaking = False


@app.route("/update_voice_status", methods=["POST"])
def update_voice_status():

    global is_speaking

    is_speaking = request.json.get(
        "speaking",
        False
    )

    return jsonify({
        "status": "updated",
        "speaking": is_speaking
    })


# ── Start Flask Application ───────────────────────────────────────────────────

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )