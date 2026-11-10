import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def get_db_connection():
    conn = sqlite3.connect("project.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with open("schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

if not os.path.exists("project.db"):
    init_db()

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    conn = get_db_connection()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC", 
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form.get("title")
    category = request.form.get("category", "General")
    priority = request.form.get("priority", "Medium")

    if not title:
        flash("Task title is required!")
        return redirect("/")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO tasks (user_id, title, category, priority) VALUES (?, ?, ?, ?)",
        (session["user_id"], title, category, priority)
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle(task_id):
    conn = get_db_connection()
    task = conn.execute(
        "SELECT status FROM tasks WHERE id = ? AND user_id = ?", 
        (task_id, session["user_id"])
    ).fetchone()

    if task:
        new_status = "Completed" if task["status"] == "Pending" else "Pending"
        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", 
            (new_status, task_id)
        )
        conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete(task_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?", 
        (task_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Must provide username and password")
            return render_template("login.html")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["hash"], password):
            flash("Invalid username and/or password")
            return render_template("login.html")

        session["user_id"] = user["id"]
        return redirect("/")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            flash("All fields are required")
            return render_template("register.html")

        if password != confirmation:
            flash("Passwords do not match")
            return render_template("register.html")

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username already exists")
            conn.close()
            return render_template("register.html")
        
        conn.close()
        flash("Registered successfully! Please log in.")
        return redirect("/login")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
    