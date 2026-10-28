from datetime import date, timedelta


# =====================================================================
# USER  (login identity: student or admin)
# =====================================================================
class User:
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.role = row["role"]
        self.created_at = row.get("created_at")

    @staticmethod
    def create(db, name, email, password_hash, role="student"):
        query = """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """
        return db.run(query, (name, email, password_hash, role))

    @staticmethod
    def find_by_email(db, email):
        row = db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))
        return User(row) if row else None

    @staticmethod
    def find_by_id(db, user_id):
        row = db.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))
        return User(row) if row else None

    @staticmethod
    def email_exists(db, email):
        row = db.fetch_one("SELECT id FROM users WHERE email = %s", (email,))
        return row is not None

    @staticmethod
    def update_name(db, user_id, name):
        db.run("UPDATE users SET name = %s WHERE id = %s", (name, user_id))


# =====================================================================
# STUDENT PROFILE
# =====================================================================
class StudentProfile:
    @staticmethod
    def get_by_user_id(db, user_id):
        return db.fetch_one(
            "SELECT * FROM student_profiles WHERE user_id = %s", (user_id,)
        )

    @staticmethod
    def upsert(db, user_id, gender, college, phone, address, dob, age, photo_path=None):
        """
        Insert the profile row the first time, update it every time after.
        `ON DUPLICATE KEY UPDATE` relies on `user_id` having a UNIQUE
        constraint in the table (see sql/schema.sql).
        """
        existing = StudentProfile.get_by_user_id(db, user_id)

        if photo_path is None and existing:
            photo_path = existing.get("photo_path")

        query = """
            INSERT INTO student_profiles
                (user_id, gender, college, phone, address, dob, age, photo_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                gender = VALUES(gender),
                college = VALUES(college),
                phone = VALUES(phone),
                address = VALUES(address),
                dob = VALUES(dob),
                age = VALUES(age),
                photo_path = VALUES(photo_path),
                updated_at = CURRENT_TIMESTAMP
        """
        db.run(query, (user_id, gender, college, phone, address, dob, age, photo_path))


# =====================================================================
# ROUTE  (bus routes managed by admin)
# =====================================================================
class Route:
    @staticmethod
    def create(db, from_city, to_city, active=True):
        query = """
            INSERT INTO routes (from_city, to_city, active)
            VALUES (%s, %s, %s)
        """
        return db.run(query, (from_city, to_city, active))

    @staticmethod
    def exists(db, from_city, to_city):
        row = db.fetch_one(
            "SELECT id FROM routes WHERE from_city = %s AND to_city = %s",
            (from_city, to_city),
        )
        return row is not None

    @staticmethod
    def list_all(db):
        return db.fetch_all("SELECT * FROM routes ORDER BY created_at DESC")

    @staticmethod
    def list_active(db):
        return db.fetch_all(
            "SELECT * FROM routes WHERE active = 1 ORDER BY from_city"
        )

    @staticmethod
    def find_by_id(db, route_id):
        return db.fetch_one("SELECT * FROM routes WHERE id = %s", (route_id,))

    @staticmethod
    def set_active(db, route_id, active):
        db.run("UPDATE routes SET active = %s WHERE id = %s", (active, route_id))


# =====================================================================
# PASS REQUEST
# =====================================================================
class PassRequest:

    # How many months each plan adds - used to calculate end_date
    # on the BACKEND, never trusting a value sent by the browser.
    PLAN_MONTHS = {
        "1 Month": 1,
        "3 Months": 3,
        "6 Months": 6,
        "1 Year": 12,
    }

    @staticmethod
    def calculate_end_date(start_date, plan):
        """start_date is a date object. Returns a date object."""
        months = PassRequest.PLAN_MONTHS.get(plan)
        if months is None:
            return None

        month_index = start_date.month - 1 + months
        year = start_date.year + month_index // 12
        month = month_index % 12 + 1

        # Handle months with fewer days (e.g. 31 Jan + 1 month -> 28/29 Feb)
        day = start_date.day
        while True:
            try:
                return date(year, month, day)
            except ValueError:
                day -= 1

    @staticmethod
    def create(db, user_id, route_id, start_date, plan, pass_type):
        end_date = PassRequest.calculate_end_date(start_date, plan)
        query = """
            INSERT INTO pass_requests
                (user_id, route_id, start_date, end_date, plan, pass_type, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """
        request_id = db.run(
            query, (user_id, route_id, start_date, end_date, plan, pass_type)
        )
        return request_id, end_date

    @staticmethod
    def find_by_id(db, request_id):
        return db.fetch_one(
            "SELECT * FROM pass_requests WHERE id = %s", (request_id,)
        )

    @staticmethod
    def list_for_user(db, user_id):
        query = """
            SELECT pr.*, r.from_city, r.to_city
            FROM pass_requests pr
            JOIN routes r ON r.id = pr.route_id
            WHERE pr.user_id = %s
            ORDER BY pr.created_at DESC
        """
        return db.fetch_all(query, (user_id,))

    @staticmethod
    def list_all_with_student(db):
        """Used by the admin 'Requests' page - joins in student name/email."""
        query = """
            SELECT pr.*, u.name AS student_name, u.email AS student_email,
                   r.from_city, r.to_city
            FROM pass_requests pr
            JOIN users u ON u.id = pr.user_id
            JOIN routes r ON r.id = pr.route_id
            ORDER BY pr.created_at DESC
        """
        return db.fetch_all(query)

    @staticmethod
    def update_status(db, request_id, status):
        db.run(
            "UPDATE pass_requests SET status = %s WHERE id = %s",
            (status, request_id),
        )

    @staticmethod
    def delete(db, request_id):
        db.run("DELETE FROM pass_requests WHERE id = %s", (request_id,))


# =====================================================================
# PAYMENT
# =====================================================================
class Payment:
    @staticmethod
    def create(db, pass_request_id, user_id, amount, payment_method, transaction_id):
        query = """
            INSERT INTO payments
                (pass_request_id, user_id, amount, payment_method,
                 transaction_id, payment_status, paid_at)
            VALUES (%s, %s, %s, %s, %s, 'success', NOW())
        """
        return db.run(
            query,
            (pass_request_id, user_id, amount, payment_method, transaction_id),
        )

    @staticmethod
    def exists_for_request(db, pass_request_id):
        row = db.fetch_one(
            "SELECT id FROM payments WHERE pass_request_id = %s",
            (pass_request_id,),
        )
        return row is not None

    @staticmethod
    def list_all_with_student(db):
        query = """
            SELECT p.*, u.name AS student_name, u.email AS student_email
            FROM payments p
            JOIN users u ON u.id = p.user_id
            ORDER BY p.paid_at DESC
        """
        return db.fetch_all(query)


# =====================================================================
# BUS PASS
# =====================================================================
class BusPass:
    @staticmethod
    def generate_pass_number(db):
        """
        Example format: BP202600001
        BP + current year + a zero-padded running number.
        """
        year = date.today().year
        row = db.fetch_one("SELECT COUNT(*) AS total FROM bus_passes")
        running_number = row["total"] + 1
        return f"BP{year}{running_number:05d}"

    @staticmethod
    def create(db, pass_request_id, user_id, valid_from, valid_until):
        pass_number = BusPass.generate_pass_number(db)
        query = """
            INSERT INTO bus_passes
                (pass_request_id, user_id, pass_number, valid_from, valid_until)
            VALUES (%s, %s, %s, %s, %s)
        """
        db.run(query, (pass_request_id, user_id, pass_number, valid_from, valid_until))
        return pass_number

    @staticmethod
    def find_latest_for_user(db, user_id):
        query = """
            SELECT bp.*, pr.plan, pr.pass_type, pr.status,
                   r.from_city, r.to_city
            FROM bus_passes bp
            JOIN pass_requests pr ON pr.id = bp.pass_request_id
            JOIN routes r ON r.id = pr.route_id
            WHERE bp.user_id = %s
            ORDER BY bp.created_at DESC
            LIMIT 1
        """
        return db.fetch_one(query, (user_id,))

    @staticmethod
    def list_all_with_student(db):
        query = """
            SELECT bp.*, u.name AS student_name, u.email AS student_email,
                   sp.dob, sp.age, sp.address,
                   pr.plan, pr.pass_type, r.from_city, r.to_city
            FROM bus_passes bp
            JOIN users u ON u.id = bp.user_id
            LEFT JOIN student_profiles sp ON sp.user_id = bp.user_id
            JOIN pass_requests pr ON pr.id = bp.pass_request_id
            JOIN routes r ON r.id = pr.route_id
            ORDER BY bp.created_at DESC
        """
        return db.fetch_all(query)
