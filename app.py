from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
CORS(app)

DB_PATH = Path("rsvp.db")
ADMIN_PASSWORD = "engaged2026"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            attending TEXT NOT NULL,
            pax INTEGER NOT NULL,
            dietary TEXT,
            message TEXT,
            submitted_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


@app.route("/")
def invitation():
    return render_template("index.html")


@app.route("/rsvp", methods=["POST"])
def submit_rsvp():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    attending = request.form.get("attending", "").strip()
    pax = request.form.get("pax", "0").strip()
    dietary = request.form.get("dietary", "").strip()
    message = request.form.get("message", "").strip()

    if not name or attending not in ["yes", "no"]:
        return redirect(url_for("invitation"))

    try:
        pax = int(pax)
    except ValueError:
        pax = 0

    if attending == "no":
        pax = 0
    else:
        pax = max(1, min(pax, 10))

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO rsvps (name, phone, attending, pax, dietary, message, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, phone, attending, pax, dietary, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    return render_template("thank_you.html", name=name, attending=attending)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        return render_template("login.html", error="Wrong password. Please try again.")

    if not session.get("admin_logged_in"):
        return render_template("login.html", error=None)

    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM rsvps ORDER BY submitted_at DESC").fetchall()

    total_responses = len(rows)
    attending_count = sum(1 for row in rows if row["attending"] == "yes")
    declined_count = sum(1 for row in rows if row["attending"] == "no")
    total_pax = sum(row["pax"] for row in rows if row["attending"] == "yes")

    conn.close()

    return render_template(
        "admin.html",
        rows=rows,
        total_responses=total_responses,
        attending_count=attending_count,
        declined_count=declined_count,
        total_pax=total_pax
    )


@app.route("/admin/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))


@app.route("/api/summary")
def api_summary():
    conn = get_db_connection()
    rows = conn.execute("SELECT attending, pax FROM rsvps").fetchall()
    conn.close()

    return jsonify({
        "total_responses": len(rows),
        "attending_responses": sum(1 for row in rows if row["attending"] == "yes"),
        "declined_responses": sum(1 for row in rows if row["attending"] == "no"),
        "total_pax_attending": sum(row["pax"] for row in rows if row["attending"] == "yes")
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
