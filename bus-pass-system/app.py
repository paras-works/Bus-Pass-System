import os
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps

import mysql.connector
from flask import (
    Flask, g, jsonify, redirect, render_template, request,
    send_from_directory, session, url_for,
)

import auth
import config
import models
import pass_service
import route_service
from database import Database

# ---------------------------------------------------------------
# CREATE THE APP
# ---------------------------------------------------------------
# Flask automatically serves everything inside the `static/` folder at
# /static/... and looks for HTML files inside the `templates/` folder.
app = Flask(__name__)

app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = config.SESSION_COOKIE_NAME
app.config["SESSION_COOKIE_HTTPONLY"] = True      # JavaScript cannot read the cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"     # not sent on cross-site form posts
app.config["SESSION_COOKIE_SECURE"] = config.SESSION_COOKIE_SECURE
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=config.SESSION_LIFETIME_HOURS)
app.config["SESSION_REFRESH_EACH_REQUEST"] = False  # expire a fixed time after login
app.config["MAX_CONTENT_LENGTH"] = config.MAX_REQUEST_BYTES


def json_default(value):
    """Teach jsonify() how to turn MySQL values into JSON.
    MySQL returns dates as Python `date` objects and money as `Decimal`,
    which JSON does not understand. We send dates as "2026-10-01" (the
    format the page JavaScript expects) and everything else as text."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


app.json.default = json_default
app.json.sort_keys = False   # keep the keys in the order we wrote them


# ---------------------------------------------------------------
# DATABASE: one connection per request
# ---------------------------------------------------------------
def get_db():
    """Return this request's Database object (open it on first use)."""
    if "db" not in g:
        g.db = Database()
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """Flask calls this after every request - close the connection."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------
# LOGIN HELPERS
# ---------------------------------------------------------------
def get_current_user():
    """
    Returns the logged-in User object, or None.
    The session cookie only stores the user's id. We look the user up in
    MySQL on every request, so a deleted user (or a changed role) takes
    effect immediately - we never trust a role stored in the cookie.
    """
    if "current_user" not in g:
        user_id = session.get("user_id")
        g.current_user = models.User.find_by_id(get_db(), user_id) if user_id else None
    return g.current_user


def api_error(message, status):
    """Standard JSON error: {"success": false, "message": "..."}"""
    return jsonify({"success": False, "message": message}), status


def get_json_body():
    """The JSON the browser sent, as a dict ({} if there was none)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


# --- decorators for API routes (they answer with JSON errors) ----------
def api_login_required(view):
    """Only logged-in users may call this API route (else 401)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if get_current_user() is None:
            return api_error("Please log in first", 401)
        return view(*args, **kwargs)
    return wrapper


def api_admin_required(view):
    """Only admins may call this API route (401 if not logged in, 403 if
    a student). The frontend can hide admin links, but THIS check is what
    actually stops a student from calling an admin API directly."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return api_error("Please log in first", 401)
        if user.role != "admin":
            return api_error("Admin access only", 403)
        return view(*args, **kwargs)
    return wrapper


# --- decorators for page routes (they redirect instead) ----------------
def student_page_required(view):
    """Student pages: send everyone else to a login page."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return redirect(url_for("login_page"))
        if user.role != "student":
            return redirect(url_for("admin_login_page"))
        return view(*args, **kwargs)
    return wrapper


def admin_page_required(view):
    """Admin pages: send everyone else to the admin login page."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None or user.role != "admin":
            return redirect(url_for("admin_login_page"))
        return view(*args, **kwargs)
    return wrapper


# =====================================================================
# PAGES  (HTML, rendered from the templates/ folder)
# =====================================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/admin/login")
def admin_login_page():
    return render_template("admin_login.html")


# ----- student pages -----
@app.route("/student/dashboard")
@student_page_required
def student_dashboard_page():
    return render_template("student_dashboard.html", user=get_current_user())


@app.route("/student/profile")
@student_page_required
def profile_page():
    return render_template("profile.html", user=get_current_user())


@app.route("/student/profile/edit")
@student_page_required
def update_profile_page():
    return render_template("update_profile.html", user=get_current_user())


@app.route("/student/pass-form")
@student_page_required
def pass_form_page():
    return render_template("pass_form.html", user=get_current_user())


@app.route("/student/my-pass")
@student_page_required
def my_pass_page():
    return render_template("my_pass.html", user=get_current_user())


@app.route("/student/payment")
@student_page_required
def payment_page():
    return render_template("payment.html", user=get_current_user())


# ----- admin pages -----
@app.route("/admin/dashboard")
@admin_page_required
def admin_dashboard_page():
    return render_template("admin_dashboard.html")


@app.route("/admin/pass-holders")
@admin_page_required
def admin_pass_holders_page():
    return render_template("admin_pass_holders.html")


@app.route("/admin/requests")
@admin_page_required
def admin_requests_page():
    return render_template("admin_requests.html")


@app.route("/admin/routes")
@admin_page_required
def admin_routes_page():
    return render_template("admin_routes.html")


@app.route("/admin/payments")
@admin_page_required
def admin_payments_page():
    return render_template("admin_payments.html")


# ----- uploaded profile photos -----
@app.route("/uploads/profile/<path:filename>")
def uploaded_photo(filename):
    # send_from_directory refuses paths like "../../secret" for us.
    return send_from_directory(config.UPLOAD_FOLDER, filename)


# =====================================================================
# API - AUTHENTICATION
# =====================================================================
@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = get_json_body()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not name or not email or not password:
        return api_error("All fields are required", 400)
    if len(name) > 100 or len(email) > 150:
        return api_error("Name or email is too long", 400)
    if not auth.is_valid_email(email):
        return api_error("Enter a valid email address", 400)
    if not auth.is_valid_password(password):
        return api_error("Password must be at least 6 characters", 400)
    if password != confirm_password:
        return api_error("Passwords do not match", 400)

    db = get_db()
    if models.User.email_exists(db, email):
        return api_error("An account with this email already exists", 409)

    password_hash = auth.hash_password(password)
    try:
        models.User.create(db, name, email, password_hash, role="student")
    except mysql.connector.IntegrityError:
        # Two people signed up with the same email at the same moment;
        # MySQL's UNIQUE constraint on users.email stopped the second one.
        return api_error("An account with this email already exists", 409)

    return jsonify({"success": True, "message": "Signup successful. Please log in."}), 201


def _login_common(expected_role):
    """Shared by student login and admin login."""
    data = get_json_body()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return api_error("Email and password are required", 400)

    user = models.User.find_by_email(get_db(), email)
    if not user or not auth.verify_password(password, user.password_hash):
        return api_error("Invalid email or password", 401)

    if user.role != expected_role:
        return api_error(f"This login is only for {expected_role}s", 403)

    # Start a fresh session. Flask stores only the user's id, in a cookie
    # that is signed with SECRET_KEY.
    session.clear()
    session["user_id"] = user.id
    session.permanent = True   # use PERMANENT_SESSION_LIFETIME (12 hours)

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    })


@app.route("/api/login", methods=["POST"])
def api_login():
    return _login_common("student")


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    return _login_common("admin")


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out"})


@app.route("/api/me")
@api_login_required
def api_me():
    """Every page calls this on load to learn who is logged in."""
    user = get_current_user()
    return jsonify({
        "success": True,
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    })


# =====================================================================
# API - PROFILE
# =====================================================================
@app.route("/api/profile")
@api_login_required
def api_get_profile():
    user = get_current_user()
    profile = models.StudentProfile.get_by_user_id(get_db(), user.id) or {}
    return jsonify({
        "success": True,
        "profile": {
            "name": user.name,
            "email": user.email,
            "gender": profile.get("gender"),
            "college": profile.get("college"),
            "phone": profile.get("phone"),
            "address": profile.get("address"),
            "dob": profile.get("dob"),
            "age": profile.get("age"),
            "photo_path": profile.get("photo_path"),
        },
    })


def save_uploaded_photo(user_id, photo):
    """
    Validate and save an uploaded profile photo (a Flask FileStorage).
    Returns (web_path, None) on success or (None, error_message).
    """
    ext = os.path.splitext(photo.filename)[1].lower()
    if ext not in config.ALLOWED_PHOTO_EXTENSIONS:
        return None, "Photo must be a .jpg, .jpeg, .png or .webp file"

    content = photo.read()
    if len(content) > config.MAX_PHOTO_SIZE_BYTES:
        return None, "Photo must be smaller than 3 MB"

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    # We make up our own file name - the name the user sent is never used.
    unique_name = f"user{user_id}_{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(config.UPLOAD_FOLDER, unique_name), "wb") as f:
        f.write(content)

    # Store a web-reachable path, not a filesystem path.
    return f"{config.UPLOAD_URL_PREFIX}/{unique_name}", None


@app.route("/api/profile", methods=["POST"])
@api_login_required
def api_update_profile():
    user = get_current_user()

    # The update-profile page sends a form (multipart/form-data, because it
    # may contain a photo file). Plain JSON is still accepted too.
    if request.mimetype in ("multipart/form-data", "application/x-www-form-urlencoded"):
        fields = request.form
        photo = request.files.get("photo")
    else:
        fields = get_json_body()
        photo = None

    name = (fields.get("name") or "").strip()
    gender = fields.get("gender") or ""
    college = (fields.get("college") or "").strip()
    phone = (fields.get("phone") or "").strip()
    address = (fields.get("address") or "").strip()
    dob = fields.get("dob") or None
    age = fields.get("age") or None

    if not name:
        return api_error("Name is required", 400)
    if len(name) > 100:
        return api_error("Name is too long", 400)
    if gender not in ("", "Male", "Female", "Other"):
        return api_error("Invalid gender selected", 400)
    if len(college) > 150:
        return api_error("College name is too long", 400)
    if phone and (not phone.isascii() or not phone.isdigit() or len(phone) != 10):
        return api_error("Enter a valid 10 digit phone number", 400)
    if age:
        try:
            age = int(age)
            if age <= 0 or age > 120:
                raise ValueError
        except (ValueError, TypeError):
            return api_error("Enter a valid age", 400)
    if dob:
        try:
            dob = date.fromisoformat(str(dob))
        except ValueError:
            return api_error("Enter a valid date of birth", 400)

    photo_path = None
    if photo is not None and photo.filename:
        photo_path, error = save_uploaded_photo(user.id, photo)
        if error:
            return api_error(error, 400)

    db = get_db()
    # The Name box on the edit-profile page changes the name on the login
    # account (users table); everything else lives in student_profiles.
    models.User.update_name(db, user.id, name)
    models.StudentProfile.upsert(
        db, user.id, gender, college, phone, address, dob, age, photo_path
    )
    return jsonify({"success": True, "message": "Profile updated successfully"})


# =====================================================================
# API - BUS ROUTES (students read active ones, admin manages all)
# =====================================================================
@app.route("/api/routes")
@api_login_required
def api_get_active_routes():
    active_routes = route_service.list_active_routes(get_db())
    return jsonify({"success": True, "routes": active_routes})


@app.route("/api/admin/routes")
@api_admin_required
def api_get_admin_routes():
    all_routes = route_service.list_routes(get_db())
    return jsonify({"success": True, "routes": all_routes})


@app.route("/api/admin/routes", methods=["POST"])
@api_admin_required
def api_admin_add_route():
    data = get_json_body()
    success, message, route_id = route_service.add_route(
        get_db(),
        str(data.get("from_city") or ""),
        str(data.get("to_city") or ""),
        bool(data.get("active")),
    )
    status = 201 if success else 400
    return jsonify({"success": success, "message": message, "route_id": route_id}), status


@app.route("/api/admin/routes/<int:route_id>/<action>", methods=["POST"])
@api_admin_required
def api_admin_toggle_route(route_id, action):
    if action not in ("activate", "deactivate"):
        return api_error("Unknown API endpoint", 404)
    success, message = route_service.set_route_active(get_db(), route_id, action == "activate")
    return jsonify({"success": success, "message": message}), (200 if success else 404)


# =====================================================================
# API - PASS REQUESTS
# =====================================================================
@app.route("/api/pass-requests", methods=["POST"])
@api_login_required
def api_create_pass_request():
    user = get_current_user()
    data = get_json_body()
    success, message, result = pass_service.apply_for_pass(
        get_db(), user.id, data.get("route_id"), data.get("start_date"),
        data.get("plan"), data.get("pass_type"),
    )
    status = 201 if success else 400
    return jsonify({"success": success, "message": message, "data": result}), status


@app.route("/api/pass-requests/my")
@api_login_required
def api_get_my_requests():
    user = get_current_user()
    requests_list = models.PassRequest.list_for_user(get_db(), user.id)
    return jsonify({"success": True, "requests": requests_list})


@app.route("/api/admin/pass-requests")
@api_admin_required
def api_get_admin_requests():
    requests_list = models.PassRequest.list_all_with_student(get_db())
    return jsonify({"success": True, "requests": requests_list})


@app.route("/api/admin/pass-requests/<int:request_id>/<decision>", methods=["POST"])
@api_admin_required
def api_admin_decide_request(request_id, decision):
    if decision == "approve":
        success, message = pass_service.approve_request(get_db(), request_id)
    elif decision == "reject":
        success, message = pass_service.reject_request(get_db(), request_id)
    else:
        return api_error("Unknown API endpoint", 404)
    return jsonify({"success": success, "message": message}), (200 if success else 400)


@app.route("/api/admin/pass-requests/<int:request_id>", methods=["DELETE"])
@api_admin_required
def api_admin_delete_request(request_id):
    success, message = pass_service.delete_request(get_db(), request_id)
    return jsonify({"success": success, "message": message}), (200 if success else 404)


# =====================================================================
# API - PAYMENTS + BUS PASS
# =====================================================================
@app.route("/api/payments", methods=["POST"])
@api_login_required
def api_pay():
    user = get_current_user()
    data = get_json_body()
    success, message, result = pass_service.pay_for_request(
        get_db(), user.id, data.get("request_id"), str(data.get("payment_method") or "")
    )
    return jsonify({"success": success, "message": message, "data": result}), (200 if success else 400)


@app.route("/api/my-pass")
@api_login_required
def api_get_my_pass():
    user = get_current_user()
    db = get_db()
    bus_pass = models.BusPass.find_latest_for_user(db, user.id)
    profile = models.StudentProfile.get_by_user_id(db, user.id) or {}
    return jsonify({
        "success": True,
        "pass": bus_pass,
        "student": {"name": user.name, **profile} if bus_pass else None,
    })


@app.route("/api/admin/payments")
@api_admin_required
def api_get_admin_payments():
    payments = models.Payment.list_all_with_student(get_db())
    return jsonify({"success": True, "payments": payments})


@app.route("/api/admin/pass-holders")
@api_admin_required
def api_get_admin_pass_holders():
    holders = models.BusPass.list_all_with_student(get_db())
    return jsonify({"success": True, "pass_holders": holders})


# =====================================================================
# API - DASHBOARDS
# =====================================================================
@app.route("/api/student/dashboard")
@api_login_required
def api_get_student_dashboard():
    user = get_current_user()
    db = get_db()
    my_requests = models.PassRequest.list_for_user(db, user.id)
    latest_request = my_requests[0] if my_requests else None
    bus_pass = models.BusPass.find_latest_for_user(db, user.id)

    return jsonify({
        "success": True,
        "name": user.name,
        "latest_request": latest_request,
        "has_approved_unpaid": any(r["status"] == "approved" for r in my_requests),
        "active_pass": bus_pass,
    })


@app.route("/api/admin/dashboard-stats")
@api_admin_required
def api_get_admin_dashboard_stats():
    db = get_db()

    total_students = db.fetch_one(
        "SELECT COUNT(*) AS total FROM users WHERE role = 'student'"
    )["total"]
    pending = db.fetch_one(
        "SELECT COUNT(*) AS total FROM pass_requests WHERE status = 'pending'"
    )["total"]
    approved = db.fetch_one(
        "SELECT COUNT(*) AS total FROM pass_requests WHERE status = 'approved'"
    )["total"]
    paid = db.fetch_one(
        "SELECT COUNT(*) AS total FROM pass_requests WHERE status = 'paid'"
    )["total"]
    total_routes = db.fetch_one("SELECT COUNT(*) AS total FROM routes")["total"]
    total_payments = db.fetch_one(
        "SELECT COUNT(*) AS total, COALESCE(SUM(amount), 0) AS revenue FROM payments"
    )

    return jsonify({
        "success": True,
        "stats": {
            "total_students": total_students,
            "pending_requests": pending,
            "approved_requests": approved,
            "paid_passes": paid,
            "total_routes": total_routes,
            "total_payments": total_payments["total"],
            "total_revenue": float(total_payments["revenue"]),
        },
    })


# =====================================================================
# ERROR HANDLING
# =====================================================================
# API URLs always answer with JSON (the page JavaScript calls
# response.json()); normal page URLs get a short plain-text message.
def _is_api_request():
    return request.path.startswith("/api/")


@app.errorhandler(404)
def handle_not_found(error):
    if _is_api_request():
        return api_error("Unknown API endpoint", 404)
    return "404 Not Found", 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    if _is_api_request():
        return api_error("Method not allowed for this API endpoint", 405)
    return "405 Method Not Allowed", 405


@app.errorhandler(413)
def handle_too_large(error):
    return api_error("Uploaded data is too large", 413)


@app.errorhandler(500)
def handle_server_error(error):
    # Flask has already written the full traceback to the terminal.
    if _is_api_request():
        return api_error("Something went wrong on the server", 500)
    return "500 Internal Server Error", 500


@app.after_request
def add_security_headers(response):
    # Stops browsers from "guessing" that an uploaded image is really HTML.
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# =====================================================================
# START THE SERVER
# =====================================================================
if __name__ == "__main__":
    print("Connecting to MySQL...")
    try:
        Database().close()
    except Exception as exc:
        print(f"Could not connect to MySQL: {exc}")
        print("Check your BUSPASS_DB_* environment variables (see README.md).")
        sys.exit(1)
    print(f"Connected to database '{config.DB_NAME}' on {config.DB_HOST}.")

    if config.SECRET_KEY_IS_RANDOM:
        print("Note: BUSPASS_SECRET_KEY is not set, so a random key is used and "
              "everyone is logged out whenever the app restarts.")

    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=config.DEBUG)
