-- =====================================================================
-- Bus Pass Management System - Database Schema
-- =====================================================================
-- Run this whole file once to set up the database:
--     mysql -u root -p < sql/schema.sql
--
-- It creates the database, every table, their relationships and
-- constraints, one sample admin account, and a couple of sample
-- routes so the app has something to show immediately after setup.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS bus_pass_system;
USE bus_pass_system;

-- ---------------------------------------------------------------
-- USERS  (every login: students AND admins live in one table,
-- distinguished by the `role` column)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)        NOT NULL,
    email           VARCHAR(150)        NOT NULL UNIQUE,
    password_hash   VARCHAR(255)        NOT NULL,
    role            ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    created_at      TIMESTAMP           DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------
-- STUDENT PROFILES  (one row per student, one-to-one with users)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_profiles (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NOT NULL UNIQUE,
    gender          VARCHAR(20),
    college         VARCHAR(150),
    phone           VARCHAR(15),
    address         TEXT,
    dob             DATE,
    age             INT,
    photo_path      VARCHAR(255),
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------
-- ROUTES  (managed by admin)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS routes (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    from_city       VARCHAR(100)    NOT NULL,
    to_city         VARCHAR(100)    NOT NULL,
    active          BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_route (from_city, to_city)
);

-- ---------------------------------------------------------------
-- PASS REQUESTS  (a student's application for a pass)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pass_requests (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NOT NULL,
    route_id        INT             NOT NULL,
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    plan            VARCHAR(20)     NOT NULL,
    pass_type       VARCHAR(50)     NOT NULL,
    status          ENUM('pending', 'approved', 'rejected',
                         'paid', 'cancelled', 'expired')
                                    NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (route_id) REFERENCES routes(id),
    INDEX idx_pass_requests_user (user_id),
    INDEX idx_pass_requests_status (status)
);

-- ---------------------------------------------------------------
-- PAYMENTS  (simulated payment against an approved request)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    pass_request_id INT             NOT NULL UNIQUE,
    user_id         INT             NOT NULL,
    amount          DECIMAL(8, 2)   NOT NULL,
    payment_method  VARCHAR(30)     NOT NULL,
    transaction_id  VARCHAR(50)     NOT NULL UNIQUE,
    payment_status  ENUM('success', 'failed') NOT NULL DEFAULT 'success',
    paid_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pass_request_id) REFERENCES pass_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ---------------------------------------------------------------
-- BUS PASSES  (generated automatically right after a successful payment)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bus_passes (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    pass_request_id INT             NOT NULL UNIQUE,
    user_id         INT             NOT NULL,
    pass_number     VARCHAR(20)     NOT NULL UNIQUE,
    valid_from      DATE            NOT NULL,
    valid_until     DATE            NOT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pass_request_id) REFERENCES pass_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ---------------------------------------------------------------
-- SESSIONS  (NOT USED by the Flask version)
-- The old http.server backend kept login sessions in this table. Flask now
-- keeps the login in its own signed session cookie, so nothing reads or
-- writes this table any more. It is left in place (and harmless) so no
-- existing table is dropped; you may delete it later if you want:
--     DROP TABLE sessions;
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id              VARCHAR(64)     PRIMARY KEY,   -- random session id
    user_id         INT             NOT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME        NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_sessions_expires (expires_at)
);

-- =====================================================================
-- SAMPLE DATA
-- =====================================================================

-- Sample admin account
-- Email:    admin@buspass.com
-- Password: ""
-- (This hash was generated by auth.py's hash_password() function -
--  see README "Security" section for how PBKDF2 hashing works.)
INSERT INTO users (name, email, password_hash, role)
VALUES (
    'System Admin',
    'admin@buspass.com',
    '5271c76400585450fc17984debfce67a$7a452ceff64ee7df11c88c26e5af163e9576138277fe544097626284f6f0c1df',
    'admin'
)
ON DUPLICATE KEY UPDATE name = name;

-- Sample routes
INSERT INTO routes (from_city, to_city, active) VALUES
    ('Mumbai', 'Virar', TRUE),
    ('Virar', 'Mumbai', TRUE),
    ('Thane', 'Panvel', TRUE)
ON DUPLICATE KEY UPDATE active = active;


-- =====================================================================
-- SAMPLE SQL QUERIES  (for SQL interview preparation - see spec section 26)
-- These are examples only; they are not required for the app to run.
-- =====================================================================

-- SELECT + WHERE: find every pending pass request
-- SELECT * FROM pass_requests WHERE status = 'pending';

-- JOIN: pass requests together with the student's name and route
-- SELECT pr.id, u.name, r.from_city, r.to_city, pr.status
-- FROM pass_requests pr
-- JOIN users u ON u.id = pr.user_id
-- JOIN routes r ON r.id = pr.route_id;

-- GROUP BY + COUNT: how many requests are in each status
-- SELECT status, COUNT(*) AS total
-- FROM pass_requests
-- GROUP BY status;

-- SUM: total revenue collected so far
-- SELECT SUM(amount) AS total_revenue FROM payments;

-- ORDER BY: most recent payments first
-- SELECT * FROM payments ORDER BY paid_at DESC;

-- UPDATE: approve a specific request
-- UPDATE pass_requests SET status = 'approved' WHERE id = 5;

-- DELETE: remove a rejected request older than 30 days
-- DELETE FROM pass_requests
-- WHERE status = 'rejected' AND created_at < NOW() - INTERVAL 30 DAY;
