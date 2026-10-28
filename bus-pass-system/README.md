# 🚌 Bus Pass Management System

A web app for applying for, approving, paying for and printing student bus passes.
Built with **Flask**, **MySQL**, and HTML / CSS / JavaScript.

**Student:** sign up, edit profile, apply for a pass, pay (simulated), print the pass.
**Admin:** approve / reject requests, manage routes, view pass holders and payments.

## Setup (Windows, Python 3.9+ and MySQL 8)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

mysql -u root -p -e "source sql/schema.sql"

set BUSPASS_DB_USER=root
set BUSPASS_DB_PASSWORD=your-mysql-password
set BUSPASS_SECRET_KEY=any-long-random-text

python app.py
```

Open **http://localhost:8000**

Run these inside the folder that contains `app.py`. Run the `mysql` line only the first time.
In PowerShell, activate with `.\venv\Scripts\Activate.ps1` and set variables with `$env:BUSPASS_DB_USER = "root"`.

## Login

- **Student:** *Student Login* → *Sign Up*
- **Admin:** `admin@buspass.com` (password is stored only as a hash in the database)

## Files

`app.py` Flask routes · `models.py` SQL queries · `auth.py` password hashing · `config.py` settings ·
`sql/schema.sql` database · `templates/` pages · `static/` CSS, JS, images