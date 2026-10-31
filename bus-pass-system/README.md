# 🚌 Bus Pass Management System (Flask + MySQL)

A full-stack web application that digitises the student bus-pass process. Students can register, apply for bus passes, track application status, make simulated payments, and download printable passes. Administrators can manage applications, routes, students, and payments.

Built using **Python Flask, MySQL, HTML, CSS, Bootstrap, and JavaScript**.

## 🚀 Features

### Student

* Student registration and login with PBKDF2 password hashing.
* View and update profile with photo upload.
* Apply for bus passes by selecting routes, plans, and pass types.
* Track application status.
* Make simulated payments for approved requests.
* View and print generated bus passes.

### Admin

* Separate administrator login.
* Dashboard with live database statistics.
* Approve, reject, and delete pass requests.
* Add, activate, and deactivate bus routes.
* View registered students, pass holders, and payment records.

## 🛠️ Technologies Used

| Layer             | Technology                       |
| ----------------- | -------------------------------- |
| Frontend          | HTML, CSS, Bootstrap, JavaScript |
| Backend           | Python 3, Flask                  |
| Database          | MySQL 8                          |
| Database Driver   | mysql-connector-python           |
| Template Engine   | Jinja2                           |
| API Communication | JavaScript Fetch API             |

**Python dependencies:** Flask, mysql-connector-python.

## 📁 Project Structure

```text
bus-pass-system/
│
├── app.py                 # Flask application and API routes
├── config.py              # Application configuration
├── database.py            # MySQL connection management
├── models.py              # Database models and SQL queries
├── auth.py                # Authentication and validation
├── route_service.py       # Bus route management
├── pass_service.py        # Bus pass business logic
├── requirements.txt
│
├── sql/
│   └── schema.sql         # Database and table creation
│
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, JavaScript and images
└── uploads/
    └── profile/           # Uploaded profile photos
```

## ⚙️ Installation & Setup

### 1. Prerequisites

* Python 3.9 or newer
* MySQL Server 8.x
* MySQL command-line client

### 2. Clone the repository

```bash
git clone <repository-url>
cd bus-pass-system
```

### 3. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Create the database

```bash
mysql -u root -p -e "source sql/schema.sql"
```

This creates the database, required tables, a sample admin account, and sample bus routes.

### 6. Configure database credentials

Set your MySQL credentials and Flask secret key in PowerShell:

```powershell
$env:BUSPASS_DB_USER = "root"
$env:BUSPASS_DB_PASSWORD = "your-password"
$env:BUSPASS_SECRET_KEY = "your-random-secret-key"
```

The application also supports environment-based configuration for the database host, port, name, server port, debug mode, and secure cookies.

### 7. Run the application

```bash
python app.py
```

Open your browser:

```text
http://localhost:8000
```

## 🔐 Demo Admin Account

The following administrator account is created through `sql/schema.sql`:

* **Email:** [admin@buspass.com](mailto:admin@buspass.com)
* **Password:** Admin@123

Change the default password before deploying the application publicly.

## 🔄 Application Workflow

1. Student registers and logs in.
2. Student updates their profile.
3. Student submits a bus-pass application.
4. Admin reviews and approves or rejects the request.
5. Student makes a simulated payment after approval.
6. System generates the bus pass.
7. Student views and prints the pass.

## 🏗️ Application Architecture

```text
Browser (HTML, CSS, JavaScript)
              |
              | Fetch API
              ▼
       Flask Application
            app.py
              |
       -----------------
       |       |       |
      Auth   Services  Models
                       |
                       ▼
                  MySQL Database
```

* **Flask:** Handles page rendering, routing, authentication, and JSON APIs.
* **Services:** Manage application workflows and business logic.
* **Models:** Handle database operations using parameterized SQL queries.
* **MySQL:** Stores users, routes, applications, payments, and passes.

## 🔒 Security & Validation

* PBKDF2 password hashing.
* Parameterized SQL queries to prevent SQL injection.
* Flask signed session cookies.
* Role-based access control for students and administrators.
* Server-side input validation.
* Server-calculated prices and pass expiration dates.
* Profile photo type and size validation.
* Students can access only their own application data.

## 📝 Important Notes

* Payments are simulated; no real money is processed.
* MySQL credentials and Flask secret keys are configured through environment variables.
* Flask's built-in development server is intended for local development and demonstrations. Use a production server such as Waitress or Gunicorn for deployment.
