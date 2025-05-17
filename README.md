# Research match
github: https://github.com/spuddydev/CITS3403_Group_Project

## Authors 
24264717    Zeel Vavliya Vavliya    
23883137	Ashaen Damunupola   
24270797	Harrison Lisle
23103979	Joshua Patton

## GitHub Usernames
Zeel Vavaliya Vavaliya: @ZeelVavliya 
Ashaen Damunupola: @Ashaen3909
Harrison Lisle: @spuddydev
Joshua Patton: @Joshua-Patton

## Description
Research match is a applcation for researchers, supervisors and students for collaboration by providing a way to find new research projects and to connect with similar interested students, aswell as share project proposals.

## Installation

### 1. Install Dependencies

Make sure you have Python installed. Then, install the required Python packages:

```bash
pip install -r requirements.txt
```

### 2. Install Playwright

Install Playwright and its browser dependencies:

```bash
pip install playwright
playwright install
```

### 3. Create a .env file
This project uses a .env file to manage environment-specific settings such as database configuration and secret keys. This allows for secure and flexible configuration without hardcoding values.
What is a .env file?

A .env file is a plain text file that contains key-value pairs of configuration variables. These values are loaded into your environment when the app starts, allowing you to change settings without modifying the source code.
Setting Up Your .env File

    In the root of the project, create a file named .env (no filename, just .env).

    Add the following lines:

SQLALCHEMY_DATABASE_URI=sqlite:///site.db
SQLALCHEMY_TRACK_MODIFICATIONS=False
SECRET_KEY=dev-placeholder

Modify values as needed:

    SQLALCHEMY_DATABASE_URI: path to your database. Replace with your production DB URI if needed.

    SECRET_KEY: used for session signing. Replace dev-placeholder with a secure random string in production.

To generate a secure key:

python -c "import secrets; print(secrets.token_hex(32))"

### 4. Run Flask

Run the Flask server:

```bash
export FLASK_APP=app.py
flask run
```

control + right click on the provided local host link to connect to website.