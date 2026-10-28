import os
import secrets

# Absolute path of the project folder (the folder that contains app.py).
# Used so file paths (like the uploads folder) work no matter where you
# start the app from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------
# DATABASE CONFIGURATION
# ---------------------------------------------------------------
DB_HOST = os.environ.get("BUSPASS_DB_HOST", "localhost")
DB_PORT = int(os.environ.get("BUSPASS_DB_PORT", "3306"))
DB_NAME = os.environ.get("BUSPASS_DB_NAME", "bus_pass_system")
DB_USER = os.environ.get("BUSPASS_DB_USER", "root")
DB_PASSWORD = os.environ.get("BUSPASS_DB_PASSWORD", "")

# ---------------------------------------------------------------
# SERVER CONFIGURATION  (used by `python app.py`)
# ---------------------------------------------------------------
# 127.0.0.1 = only this computer can open the site. Set
# BUSPASS_SERVER_HOST=0.0.0.0 if you want other devices on your Wi-Fi
# (for example your phone) to open it too.
SERVER_HOST = os.environ.get("BUSPASS_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("BUSPASS_SERVER_PORT", "8000"))

# Flask debug mode shows a detailed error page and auto-reloads when you
# edit code. Handy while learning, but NEVER turn it on for a real server.
DEBUG = os.environ.get("BUSPASS_DEBUG", "0") == "1"

# ---------------------------------------------------------------
# SESSION CONFIGURATION  (Flask sessions)
# ---------------------------------------------------------------
# Flask stores the logged-in user's id in a cookie and SIGNS it with
# SECRET_KEY, so the browser cannot edit it without the server noticing.
# The key must be secret and must not be written in the code.
#
# If BUSPASS_SECRET_KEY is not set we generate a random key every time
# the app starts. That is safe, but everyone gets logged out on each
# restart. Set BUSPASS_SECRET_KEY to keep logins across restarts (and
# always set it when running more than one worker process).
SECRET_KEY = os.environ.get("BUSPASS_SECRET_KEY") or secrets.token_hex(32)
SECRET_KEY_IS_RANDOM = not os.environ.get("BUSPASS_SECRET_KEY")

# How long a login session stays valid.
SESSION_LIFETIME_HOURS = int(os.environ.get("BUSPASS_SESSION_HOURS", "12"))
SESSION_COOKIE_NAME = "buspass_session"

# "Secure" cookies are only sent over HTTPS. Plain http://localhost
# cannot use them, so this is OFF by default for local development.
# Set BUSPASS_COOKIE_SECURE=1 when the site is served over HTTPS.
SESSION_COOKIE_SECURE = os.environ.get("BUSPASS_COOKIE_SECURE", "0") == "1"

# ---------------------------------------------------------------
# FILE UPLOAD CONFIGURATION (profile photos)
# ---------------------------------------------------------------
# Folder where uploaded profile photos are physically saved. Only the
# *path* to the file is stored in MySQL - the image bytes live on disk.
UPLOAD_FOLDER = os.environ.get(
    "BUSPASS_UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads", "profile")
)
# The URL prefix photos are served from; this is what gets stored in the
# student_profiles.photo_path column (same format as before the migration).
UPLOAD_URL_PREFIX = "/uploads/profile"
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PHOTO_SIZE_BYTES = 3 * 1024 * 1024  # 3 MB
# Flask refuses any request body bigger than this (a little above the
# photo limit, to leave room for the other form fields).
MAX_REQUEST_BYTES = 4 * 1024 * 1024
