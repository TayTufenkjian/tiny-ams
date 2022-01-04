# Tiny AMS
#### Video Demo:  <https://youtu.be/bMirePfVeEg>

<br>

## Description
AMS stands for "association management system." 

An AMS is a type of software application that organizations of all kinds use to manage their members and business operations. 

My day job involves quality assurance for one such software product, so I thought for my CS50x final project it would be fun to strip away all the extra features and see what building a new AMS from scratch might look like today. This is essentially a very small proof of concept (hence the "tiny" in Tiny AMS).

I built this as a SaaS web application using Python 3, Flask, SQLite 3, and Jinja2.

The application allows you to do the following things:
1. Create an association account.
2. Log in to and out of the association account.
3. Create records for members and non-members.
4. Search people records.
5. View a person record.
6. Edit a person record.
7. Delete a person record.

<br>

## Installation

To run this program, you'll need to install Python 3 and Flask.

Instructions can get lengthy and differ depending on your machine. 
This article can be a starting point:
<https://www.section.io/engineering-education/complete-guide-on-installing-flask-for-beginners/>

Jinja2 comes bundled with Flask. <br>
SQLite comes bundled with Python. <br>
So in theory you shouldn't need to worry about installing Jinja or SQLite once you're able to install Python and Flask.

### To run the program
1. Open your terminal. 
2. Navigate to the project directory.
3. Enter the following command:

```
python -m flask run
```

<br>

## Structure

This project uses a simple model–view–controller (MVC) pattern.

### Model
SQLite 3 provides a lightweight database.

There is one database for the project: **tinyams.db**.

There are two tables in this database: the **association** table and the **person** table.

The **association** table contains data about the association account: 
```
CREATE TABLE IF NOT EXISTS association (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    association_name TEXT,
    email TEXT,
    username TEXT,
    hash TEXT,
    datetime_created TEXT )
```

The **person** table contains data about the people records added to the association account.<br>
A person can be a member or a non-member.
```
CREATE TABLE IF NOT EXISTS person (
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
    FOREIGN KEY(association_id) REFERENCES association(id))
```


There is a virtual table called **person_index** for the purpose of full text search using FTS5.<br>
This table is essentially a copy of the **person** table.<br>
The tables are kept in sync via SQLite triggers.


### View
In keeping with Jinja convention, there is a **templates** folder and a **static** folder.

The templates folder contains all the Jinja templates as HTML files. <br>
The base template file is **layout.html**. <br>
This template is extended across all the other templates.

The static folder contains one CSS file: **styles.css**.

There is some JavaScript on a single page, but not enough to warrant including a separate JS file.

### Controller
This is a small project with only one Python file: **app.py**.

The app is loosely divided into three sections:
1. Database, tables, index, and triggers for full-text search.
2. Helper functions used throughout the application.
3. Routes and the functions within them.

## Notes 

I had a tricky time with @app.context_processor while creating a global variable for use across Jinja templates.  I'm not entirely sure why a nested loop solved the problem of transforming a tuple into a string, but at least it's working.