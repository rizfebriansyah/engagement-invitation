# Engagement RSVP App

A simple mobile-friendly digital engagement invitation with RSVP tracking.

## Features
- Mobile-first digital invitation
- RSVP form
- Guest count tracking
- Admin dashboard
- SQLite database
- Accept / decline status
- Number of pax per guest
- Dietary notes / message field

## How to run locally

1. Install Python 3.10+
2. Open terminal in this folder
3. Run:

```bash
pip install -r requirements.txt
python app.py
```

4. Open:

```text
http://127.0.0.1:5000
```

Admin dashboard:

```text
http://127.0.0.1:5000/admin
```

## Admin Password

Default password:

```text
engaged2026
```

Change it in `app.py` under `ADMIN_PASSWORD`.

## Deployment idea

You can deploy this on Render, Railway, or PythonAnywhere.
For a small 30-pax engagement event, this setup is enough.
