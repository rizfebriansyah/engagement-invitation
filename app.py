from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
# import psycopg2
# import psycopg2.extras
import psycopg
from psycopg.rows import dict_row
import os
from datetime import datetime

import csv
from io import StringIO
from flask import Response

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "engaged2026")


def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    # return psycopg2.connect(DATABASE_URL, sslmode="require")
    return psycopg.connect(DATABASE_URL)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rsvps (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            attending TEXT NOT NULL,
            pax INTEGER NOT NULL,
            dietary TEXT,
            message TEXT,
            submitted_at TIMESTAMP NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.before_request
def setup_database():
    init_db()


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
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO rsvps 
        (name, phone, attending, pax, dietary, message, submitted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        name,
        phone,
        attending,
        pax,
        dietary,
        message,
        datetime.now()
    ))
    conn.commit()
    cur.close()
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
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT * FROM rsvps ORDER BY submitted_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    total_responses = len(rows)
    attending_count = sum(1 for row in rows if row["attending"] == "yes")
    declined_count = sum(1 for row in rows if row["attending"] == "no")
    total_pax = sum(row["pax"] for row in rows if row["attending"] == "yes")

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
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT attending, pax FROM rsvps")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({
        "total_responses": len(rows),
        "attending_responses": sum(1 for row in rows if row["attending"] == "yes"),
        "declined_responses": sum(1 for row in rows if row["attending"] == "no"),
        "total_pax_attending": sum(row["pax"] for row in rows if row["attending"] == "yes")
    })

@app.route("/admin/export")
def export_csv():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)

    cur.execute("""
        SELECT
            name,
            phone,
            attending,
            pax,
            dietary,
            message,
            submitted_at
        FROM rsvps
        ORDER BY submitted_at DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Name",
        "Phone",
        "Attending",
        "Pax",
        "Dietary",
        "Message",
        "Submitted At"
    ])

    for row in rows:
        writer.writerow([
            row["name"],
            row["phone"],
            row["attending"],
            row["pax"],
            row["dietary"],
            row["message"],
            row["submitted_at"]
        ])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=guest_list.csv"
        }
    )


if __name__ == "__main__":
    app.run(debug=True)