from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
# import psycopg2
# import psycopg2.extras
import psycopg
from psycopg.rows import dict_row
import os

from datetime import datetime
from zoneinfo import ZoneInfo

import csv
from io import StringIO
from flask import Response

app = Flask(__name__)

@app.template_filter("sg_time")
def sg_time(value):
    if not value:
        return ""

    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))

    sg = value.astimezone(ZoneInfo("Asia/Singapore"))
    return sg.strftime("%Y-%m-%d %I:%M %p")

app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "engaged2026")

FAMILIES = {
    "pakde-bob-family": {
        "family_name": "Pakde Bob & Family",
        "max_pax": 3
    },
    "tante-wulan-family": {
        "family_name": "Tante Wulan & Family",
        "max_pax": 3
    },    
    "mas-ais-family": {
        "family_name": "Mas Ais & Family",
        "max_pax": 3
    },
    "bude-nunuk-family": {
        "family_name": "Bude Nunuk & Family",
        "max_pax": 3
    },
    "pakde-mat-family": {
        "family_name": "Pakde Mat & Family",
        "max_pax": 4
    },
    "mba-irma-family": {
        "family_name": "Mba Irma & Family",
        "max_pax": 3
    },
    "tante-lely-family": {
        "family_name": "Tante Lely & Family",
        "max_pax": 3
    },
    "kak-aga-family": {
        "family_name": "Kak Aga & Family",
        "max_pax": 3
    }    
}

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
            family_slug TEXT,
            family_name TEXT,
            name TEXT NOT NULL,
            phone TEXT,
            attending TEXT NOT NULL,
            pax INTEGER NOT NULL,
            dietary TEXT,
            message TEXT,
            submitted_at TIMESTAMP NOT NULL
        )
    """)
    try:
        cur.execute("ALTER TABLE rsvps ADD COLUMN family_slug TEXT")
    except Exception:
        conn.rollback()

    try:
        cur.execute("ALTER TABLE rsvps ADD COLUMN family_name TEXT")
    except Exception:
        conn.rollback()
    conn.commit()
    cur.close()
    conn.close()


@app.before_request
def setup_database():
    init_db()


@app.route("/")
def invitation():
    return render_template(
        "index.html",
        family_slug="general",
        family_name="Our Beloved Guest",
        max_pax=10
    )

@app.route("/invite/<slug>")
def personalized_invite(slug):
    family = FAMILIES.get(slug)

    if not family:
        return redirect(url_for("invitation"))

    return render_template(
        "index.html",
        family_slug=slug,
        family_name=family["family_name"],
        max_pax=family["max_pax"]
    )

@app.route("/rsvp", methods=["POST"])
def submit_rsvp():
    # name = request.form.get("name", "").strip()
    # phone = request.form.get("phone", "").strip()
    name = request.form.get("family_name", "Guest").strip()
    phone = ""
    attending = request.form.get("attending", "").strip()
    pax = request.form.get("pax", "0").strip()
    dietary = request.form.get("dietary", "").strip()
    message = request.form.get("message", "").strip()
    family_slug = request.form.get("family_slug", "").strip()
    family_name = request.form.get("family_name", "").strip()
    max_pax = request.form.get("max_pax", "10").strip()

    # if not name or attending not in ["yes", "no"]:
    #     return redirect(url_for("invitation"))
    if attending not in ["yes", "no"]:
        return redirect(url_for("invitation"))

    try:
        pax = int(pax)
    except ValueError:
        pax = 0

    try:
        max_pax = int(max_pax)
    except ValueError:
        max_pax = 10

    if attending == "no":
        pax = 0
    else:
        pax = max(1, min(pax, max_pax))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO rsvps 
        (family_slug, family_name, name, phone, attending, pax, dietary, message, submitted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        family_slug,
        family_name,
        name,
        phone,
        attending,
        pax,
        dietary,
        message,
        datetime.now(ZoneInfo("Asia/Singapore"))
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

@app.route("/admin/reset-db")
def reset_db():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE rsvps RESTART IDENTITY;")

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("admin"))

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