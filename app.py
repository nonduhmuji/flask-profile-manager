

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for
)

import sqlite3
import re
import os

from werkzeug.security import generate_password_hash


# -------------------------------------------------
# 1. FLASK APPLICATION CONFIGURATION
# -------------------------------------------------

# Get the directory where app.py is located.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure Flask to find HTML templates and CSS files.
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# Store the SQLite database in the project folder.
DATABASE = os.path.join(BASE_DIR, "profiles.db")


# -------------------------------------------------
# 2. DATABASE CONNECTION
# -------------------------------------------------

def get_db_connection():
    """
    Establish a connection to the SQLite database.
    Rows can be accessed using column names.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------
# 3. CREATE DATABASE TABLE
# -------------------------------------------------

def init_db():
    """
    Create the users table if it does not exist.
    Existing user information is preserved.
    """
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# -------------------------------------------------
# 4. HOME PAGE - REGISTRATION FORM
# -------------------------------------------------

@app.route("/")
def home():
    """
    Display the registration form.
    """
    return render_template("register.html")


# -------------------------------------------------
# 5. REGISTER NEW USER
# -------------------------------------------------

@app.route("/register", methods=["POST"])
def register():

    # Retrieve and clean information from the form.
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")

    # Validate that all required fields are completed.
    if not all([name, email, phone, password]):
        return "Error: All fields are required.", 400

    # Check that the name contains at least two characters.
    if len(name) < 2:
        return "Name must contain at least 2 characters.", 400

    # Validate the email address format.
    email_pattern = r"[^@\s]+@[^@\s]+\.[^@\s]+"

    if not re.fullmatch(email_pattern, email):
        return "Error: Invalid email address.", 400

    # Validate a 10-digit phone number.
    if not re.fullmatch(r"[0-9]{10}", phone):
        return "Phone number must contain 10 digits.", 400

    # Check minimum password length.
    if len(password) < 8:
        return "Password must contain at least 8 characters.", 400

    # Hash the password before storing it.
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()

    try:
        # Insert the new user into the SQLite database.
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, phone, password)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, phone, hashed_password)
        )

        conn.commit()
        user_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        return "Error: Email address already registered.", 409

    finally:
        conn.close()

    # Redirect to the registered user's profile.
    return redirect(
        url_for("view_profile", user_id=user_id)
    )


# -------------------------------------------------
# 6. VIEW REGISTERED USER PROFILE
# -------------------------------------------------

@app.route("/profile/<int:user_id>")
def view_profile(user_id):
    """
    Retrieve and display user information dynamically.
    """

    conn = get_db_connection()

    # Retrieve the selected user's information.
    user = conn.execute(
        """
        SELECT id, name, email, phone
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    # Return an error if the user does not exist.
    if user is None:
        return "Error: User not found.", 404

    # Display information using the profile template.
    return render_template(
        "profile.html",
        user=user
    )


# -------------------------------------------------
# 7. UPDATE EXISTING USER PROFILE
# -------------------------------------------------

@app.route("/update/<int:user_id>", methods=["GET", "POST"])
def update_profile(user_id):
    """
    Display the update form and save edited information.
    """

    conn = get_db_connection()

    # Retrieve existing information from the database.
    user = conn.execute(
        "SELECT id, name, email, phone FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if user is None:
        conn.close()
        return "Error: User not found.", 404

    # Process submitted updates.
    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()

        # Validate required fields.
        if not all([name, email, phone]):
            conn.close()
            return "All fields are required.", 400

        # Validate name length.
        if len(name) < 2:
            conn.close()
            return "Name must contain at least 2 characters.", 400

        # Validate email format.
        if not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email
        ):
            conn.close()
            return "Invalid email address.", 400

        # Validate phone number.
        if not re.fullmatch(r"[0-9]{10}", phone):
            conn.close()
            return "Phone number must contain 10 digits.", 400

        try:
            # Update the user's information in SQLite.
            conn.execute(
                """
                UPDATE users
                SET name = ?, email = ?, phone = ?
                WHERE id = ?
                """,
                (name, email, phone, user_id)
            )

            conn.commit()

        except sqlite3.IntegrityError:
            return "Email address already in use.", 409

        finally:
            conn.close()

        # Return to the updated profile page.
        return redirect(
            url_for("view_profile", user_id=user_id)
        )

    # Close the connection after retrieving existing data.
    conn.close()

    # Preload existing information into the update form.
    return render_template(
        "update.html",
        user=user
    )


# -------------------------------------------------
# 8. START THE FLASK APPLICATION
# -------------------------------------------------


# Initialise database when the application starts.
init_db()

# Only use Flask's development server locally.
if __name__ == "__main__":
    app.run(debug=True)
