# Import libraries and tools 
import re
import sqlite3
from datetime import datetime
from flask import Flask, json, redirect, render_template, request, session, url_for
from flask_session import Session
from functools import wraps
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

# Configure application
app = Flask(__name__)

# Configure session to use filesystem instead of signed cookies
# Commented out SESSION_FILE_DIR for deploying to Heroku so the "filesystem" defaults to the "flask_session" folder in the current working directory. 
# app.config["SESSION_FILE_DIR"] = mkdtemp() 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQLite database
db = sqlite3.connect("tinyams.db")

# Create association table
db.execute("""CREATE TABLE IF NOT EXISTS association (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    association_name TEXT,
    email TEXT,
    username TEXT,
    hash TEXT,
    datetime_created TEXT )""")

# Create person table
db.execute("""CREATE TABLE IF NOT EXISTS person (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    association_id INTEGER,
    is_member INTEGER,
    username TEXT,
    hash TEXT,
    datetime_created TEXT,
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    employer TEXT,
    job_title TEXT, 
    FOREIGN KEY(association_id) REFERENCES association(id))""")

# Create virtual person table for full text search index
db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS person_index USING fts5(
    association_id,
    is_member,
    username,
    hash UNINDEXED,
    datetime_created,
    first_name,
    middle_name,
    last_name,
    email,
    phone,
    employer,
    job_title,
    content='person',
    content_rowid='id')""")

# Create triggers for keeping the person index in sync with the person table
# Trigger for INSERT
db.execute("""CREATE TRIGGER IF NOT EXISTS person_ai AFTER INSERT ON person
    BEGIN
        INSERT INTO person_index (
            rowid,
            association_id,
            is_member,
            username,
            datetime_created,
            first_name,
            middle_name,
            last_name,
            email,
            phone,
            employer,
            job_title)
        VALUES (
            new.id,
            new.association_id,
            new.is_member,
            new.username,
            new.datetime_created,
            new.first_name,
            new.middle_name,
            new.last_name,
            new.email,
            new.phone,
            new.employer,
            new.job_title);
    END; """)

# Trigger for UPDATE
db.execute("""CREATE TRIGGER IF NOT EXISTS person_au AFTER UPDATE ON person 
    BEGIN
        INSERT INTO person_index (
            person_index, 
            rowid,
            association_id,
            is_member,
            username,
            datetime_created,
            first_name,
            middle_name,
            last_name,
            email,
            phone,
            employer,
            job_title)
        VALUES (
            'delete',
            old.id,
            old.association_id,
            old.is_member,
            old.username,
            old.datetime_created,
            old.first_name,
            old.middle_name,
            old.last_name,
            old.email,
            old.phone,
            old.employer,
            old.job_title);
        INSERT INTO person_index (
            rowid,
            association_id,
            is_member,
            username,
            datetime_created,
            first_name,
            middle_name,
            last_name,
            email,
            phone,
            employer,
            job_title)
        VALUES (
            new.id,
            new.association_id,
            new.is_member,
            new.username,
            new.datetime_created,
            new.first_name,
            new.middle_name,
            new.last_name,
            new.email,
            new.phone,
            new.employer,
            new.job_title); 
    END; """)

# Trigger for DELETE
db.execute("""CREATE TRIGGER IF NOT EXISTS person_ad AFTER DELETE ON person 
    BEGIN
        INSERT INTO person_index (
            person_index, 
            rowid,
            association_id,
            is_member,
            username,
            datetime_created,
            first_name,
            middle_name,
            last_name,
            email,
            phone,
            employer,
            job_title)
        VALUES (
            'delete',
            old.id,
            old.association_id,
            old.is_member,
            old.username,
            old.datetime_created,
            old.first_name,
            old.middle_name,
            old.last_name,
            old.email,
            old.phone,
            old.employer,
            old.job_title);
    END; """ )

#/////////////////////// HELPER FUNCTIONS ///////////////////////#

# Function to select from the database and return results as a list of dictionaries
def select_dict(query, variables):
    with sqlite3.connect("tinyams.db") as db:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        cursor.execute(query, variables)
        return cursor.fetchall()

# Function to display a contextual error message
def apology(message, code=400):
    """Render message as an apology to user."""

    return render_template("apology.html", error=code, message=message), code

# Function to require login for a route
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Function to inject the association_name variable into the context of all Jinja templates
@app.context_processor
def inject_association_name():

    with sqlite3.connect("tinyams.db") as db:
        cursor = db.cursor()
        cursor.execute("SELECT association_name FROM association WHERE id = :id", {"id": session.get("user_id")})
        association_tuple = cursor.fetchall()

    # Convert tuple to string
    string = ''
    for i in association_tuple:
        for j in i:
            string = string + j

    return dict(association_name = string)

#/////////////////////// END HELPER FUNCTIONS ///////////////////////#

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    """Create an association account"""

    # User reached route via POST (as by submitting a form)
    if request.method == "POST":

        # Get association information from the submitted form
        name = request.form.get("name")
        email = request.form.get("email")
        username = request.form.get("username")
        hash = generate_password_hash(request.form.get("password"))

        # Get datetime of form submission as UTC
        submitted = datetime.utcnow()
        
        # Insert db record for the association
        with sqlite3.connect("tinyams.db") as db:
            cursor = db.cursor()
            cursor.execute("""INSERT INTO association (association_name, email, username, hash, datetime_created) 
                              VALUES (:name, :email, :username, :hash, :submitted)""", 
                              {"name": name, "email": email, "username": username, "hash": hash, "submitted": submitted})
            db.commit()

        # Redirect to the login page
        return redirect("/login")

    # User reached route via GET (by clicking a link or via redirect)
    else:
        return render_template("create_account.html")


@app.route("/create_person", methods=["GET", "POST"])
@login_required
def create_person():
    """Create a person record"""

    # User reached route via POST (as by submitting a form)
    if request.method == "POST":

        # Get person information from the submitted form
        is_member = request.form.get("is_member")
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        username = request.form.get("username")
        hash = generate_password_hash(request.form.get("password"))
        phone = request.form.get("phone")
        employer = request.form.get("employer")
        job_title = request.form.get("job_title")

        # Get datetime of form submission as UTC
        submitted = datetime.utcnow()

        # Insert db record for the person
        with sqlite3.connect("tinyams.db") as db:
            cursor = db.cursor()
            cursor.execute(""" 
                INSERT INTO person (
                    association_id,
                    is_member,
                    username,
                    hash,
                    datetime_created,
                    first_name,
                    middle_name,
                    last_name,
                    email,
                    phone,
                    employer,
                    job_title )
                VALUES (
                    :association_id,
                    :is_member,
                    :username,
                    :hash,
                    :datetime_created,
                    :first_name,
                    :middle_name,
                    :last_name,
                    :email,
                    :phone,
                    :employer,
                    :job_title) """,
                {
                    "association_id": session["user_id"],
                    "is_member": is_member,
                    "username": username,
                    "hash": hash,
                    "datetime_created": submitted,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "employer": employer,
                    "job_title": job_title   
                }
            )
            
            db.commit()

        # Redirect to the association dashboard
        return redirect("/dashboard")

    # User reached route via GET (by clicking a link or via redirect)
    else:    
        return render_template("create_person.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

     # Clear browing session, forget any user currently logged in
    session.clear()

    # User reached route via POST (as by submitting a form)
    if request.method == "POST":

        # Ensure that username was submitted
        if not request.form.get("username"):
            return apology("Please enter a username", 403)

        # Ensure that password was submitted
        elif not request.form.get("password"):
            return apology("Please enter a password", 403)

        # Query database for username
        query = "SELECT * FROM association WHERE username = :username"
        variables = {"username": request.form.get("username")}
        association = select_dict(query, variables)[0]

        # Ensure username exists and password is correct
        if len(association) < 1 or not check_password_hash(association["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403)

        # Remember which user (association) has logged in
        session["user_id"] = association["id"]

        # Redirect to the dashboard
        return redirect("/dashboard")

    else:
        return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    """Log user out"""

    # Clear browing session, forget any user currently logged in
    session.clear()

    # Redirect to the login page
    return redirect("/login")


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Display dashboard for the association"""
    
    # Get the association id of the user who is logged in
    association_id = session["user_id"]

    # Get the person count, member count, and non-member count for the association
    with sqlite3.connect("tinyams.db") as db:
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(id) FROM person WHERE association_id = ?", (association_id,))
        person_count = (cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(id) FROM person WHERE is_member = 1 and association_id = ?", (association_id,))
        member_count = (cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(id) FROM person WHERE is_member = 0 and association_id = ?", (association_id,))
        nonmember_count = (cursor.fetchone()[0])

    return render_template("dashboard.html", person_count = person_count, member_count = member_count, nonmember_count = nonmember_count)


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Search for a person who is connected to the association"""

    # User reached route via POST (as by submitting a form)
    if request.method == "POST":

        # Get search criteria from form
        criteria = request.form.get("search_criteria")

        # If the user entered some search criteria, execute full text search
        if criteria and criteria.strip():
            criteria_prefix = f"{criteria}*"
            query = "SELECT rowid, * FROM person_index WHERE association_id = :association_id AND person_index MATCH :criteria_prefix ORDER BY rank"
            variables = {"association_id": session["user_id"], "criteria_prefix": criteria_prefix}
            results = select_dict(query, variables)
        
        # Otherwise return all people records (when criteria is blank or only contains spaces)
        else:
            query = "SELECT rowid, * FROM person_index WHERE association_id = :association_id"
            variables = {"association_id": session["user_id"]}
            results = select_dict(query, variables)

        return render_template("search_results.html", results = results)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("search.html")


@app.route("/profile/<int:id>", methods=["GET"])
@login_required
def person_profile(id):
    """Load profile page for the person whose ID is in the URL"""

    # Get person data to display on the profile page
    profile = select_dict("SELECT * FROM person WHERE association_id = :association_id AND id = :id", {"association_id": session["user_id"], "id": id})[0]

    return render_template("profile.html", 
                            id = id,
                            first_name = profile["first_name"], 
                            middle_name = profile["middle_name"],
                            last_name = profile["last_name"], 
                            is_member = profile["is_member"], 
                            username = profile["username"], 
                            datetime_created = profile["datetime_created"],
                            email = profile["email"], 
                            phone = profile["phone"],
                            employer = profile["employer"],
                            job_title = profile["job_title"])


@app.route("/edit_profile/<int:id>", methods=["GET", "POST"])
@login_required
def edit_person(id):
    """Edit a person record"""

    # User reached route via POST (as by submitting a form)
    if request.method == "POST":

        # Get data from submitted form
        is_member = request.form.get("is_member")
        username = request.form.get("username")
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        employer = request.form.get("employer")
        job_title = request.form.get("job_title")
        
        # Update the person record in the database
        with sqlite3.connect("tinyams.db") as db:
            cursor = db.cursor()
            cursor.execute("""UPDATE person 
                SET is_member = :is_member,
                    username = :username,
                    first_name = :first_name,
                    middle_name = :middle_name,
                    last_name = :last_name,
                    email = :email,
                    phone = :phone,
                    employer = :employer,
                    job_title = :job_title    
                WHERE id = :id """,
                {
                    "is_member": is_member,
                    "username": username,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "employer": employer,
                    "job_title": job_title,
                    "id": id
                })

            db.commit()

            # Redirect to the profile page for the person record that was just updated
            return redirect(url_for("person_profile", id = id))

    # User reached route via GET (by clicking a link or via redirect)
    else:
        profile = select_dict("SELECT * FROM person WHERE association_id = :association_id AND id = :id", {"association_id": session["user_id"], "id": id})[0]
        
        return render_template("edit_person.html", 
                        id = id,
                        first_name = profile["first_name"], 
                        middle_name = profile["middle_name"],
                        last_name = profile["last_name"], 
                        is_member = profile["is_member"], 
                        username = profile["username"], 
                        datetime_created = profile["datetime_created"],
                        email = profile["email"], 
                        phone = profile["phone"],
                        employer = profile["employer"],
                        job_title = profile["job_title"])

@app.route("/delete_person/<int:id>", methods=["GET"])
@login_required
def delete_person(id):
    """Delete a person record"""

    # Delete person record from the database
    with sqlite3.connect("tinyams.db") as db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM person WHERE id = :id", {"id": id})
    
    return redirect("/dashboard")


    
  