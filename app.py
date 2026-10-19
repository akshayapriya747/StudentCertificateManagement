from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key"

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        college_id = request.form["college_id"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        department = request.form["department"].strip()
        academic_year = request.form["academic_year"].strip()

        if not all([full_name, college_id, email, password]):
            flash("Please fill in all required fields.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """INSERT INTO students
                (full_name, college_id, email, password, department, academic_year)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    full_name,
                    college_id,
                    email,
                    generate_password_hash(password),
                    department,
                    academic_year
                )
            )
            connection.commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:
            connection.rollback()
            flash("That college ID or email is already registered.")
            return redirect(url_for("register"))

        finally:
            cursor.close()
            connection.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM students WHERE email = %s",
                (email,)
            )
            student = cursor.fetchone()

        finally:
            cursor.close()
            connection.close()

        if student and check_password_hash(student["password"], password):
            session["student_id"] = student["student_id"]
            session["student_name"] = student["full_name"]
            session["role"] = student["role"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """SELECT student_id, full_name, college_id, email,
                      department, academic_year
               FROM students WHERE student_id = %s""",
            (session["student_id"],)
        )
        student = cursor.fetchone()

        if student is None:
            session.clear()
            flash("Student account not found.")
            return redirect(url_for("login"))

        cursor.execute(
            """SELECT certificate_id, certificate_name,
                      certificate_type, status, uploaded_at
               FROM certificates WHERE student_id = %s
               ORDER BY uploaded_at DESC""",
            (session["student_id"],)
        )
        certificates = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "dashboard.html",
        student=student,
        certificates=certificates
    )

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully.")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)