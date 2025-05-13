from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, current_app, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text  #for raw SQL execution
from database.schema import db, User, Project, Interest
from dotenv import load_dotenv
from functools import wraps
import os
import jwt
import datetime
from forms import RegisterForm, LoginForm,Settings_ProfileForm

# Initialise environment
load_dotenv()

# Initialise flask app
app = Flask(__name__)

# Security
app.secret_key = os.getenv("SECRET_KEY", "dev_key")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  
    SESSION_COOKIE_SAMESITE='Lax'  
)

# Configure app and initialise
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///site.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False").lower() in ("true", "1")
db.init_app(app)

# If no database exists, create one !
with app.app_context():
    if not os.path.exists('site.db'):
        db.create_all()


def back_to_login():
    response = make_response(redirect('/login'))
    response.set_cookie('jwt_token', '', max_age=0)
    return response

def token_required(func):
    """
    A wrapper that checks the JWT stored in a cookie and verifies it
    before allowing the route to execute.
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.cookies.get('jwt_token', None)

        if not token:
            return back_to_login()

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            request.user = data  # optionally attach user info to request
        except jwt.ExpiredSignatureError:
            return back_to_login()
        except jwt.InvalidTokenError:
            return back_to_login()

        return func(*args, **kwargs)
    return decorated

# Home Page
@app.route('/')
def default():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

# Sign In Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    # look for token in headers (americans spell authorisation wrong)
    token = request.cookies.get('jwt_token', None)

    if not token:
        form = LoginForm()  # Instantiate the form
        if 'attempts' not in session:
            session['attempts'] = 0

        if form.validate_on_submit():  # Check if the form is valid when submitted
            username = form.username.data
            password = form.password.data

            # Find the user in the database by username
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                # Successful login: redirect to home page or dashboard
                session['attempts'] = 0  # Reset attempts on success
                # Parse credentials to session object
                session['user_id'] = user.id
                session['username'] = user.username
                session['email'] = user.email
                token_payload = {
                    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                }

                token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm="HS256")
                response = make_response(redirect('/dashboard'))

                # Set cookie to persist for 1 hour
                response.set_cookie(
                    'jwt_token', token,
                    httponly=True,
                    samesite='Lax',
                    max_age=3600  # 1 hour in seconds
                )

                return response

            else:
                # Invalid credentials
                session['attempts'] += 1
                form.password.errors.append("Invalid credentials") 
                return redirect(url_for('login'))
        
        return render_template('login.html', form=form)
    else:
        # Redirect straight to dashboard if jwt already issued
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            request.user = data  # optionally attach user info to request
        except jwt.ExpiredSignatureError:
            return back_to_login()
        except jwt.InvalidTokenError as e:
            return back_to_login()
        
        return redirect('/dashboard')

# Dashboard Page
@app.route('/dashboard')
@token_required
def dashboard():
    if not session.get('user_id'): # Check login status
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', username=session['username'],var="hello")

# Upload Page (GET and POST for form)
@app.route('/upload', methods=['GET', 'POST'])
@token_required
def upload():
    if request.method == 'POST':
        user = db.session.query(User).get(session['user_id'])  
        action = request.form.get('action')
        if action == 'submit':
            keywords = request.form.get('keywords')
            if keywords:
                # Add new interest to db
                new_interest = Interest(interest_name=keywords)
                db.session.add(new_interest)
                user.interests.append(new_interest)  
                db.session.commit()

        elif action == 'refresh': # Remove all associations in the association table
            user.interests = []
            db.session.commit()

        user = db.session.query(User).filter_by(id=session['user_id']).first()
        if user.interests:
            user_interests = user.interests  # This will give you the list of interests
        else:
            user_interests = None
        matched_projects = []
        return render_template('upload.html', matched_projects=matched_projects,user_interests=user_interests)
    else: #GET
        if not session.get('user_id'): # Check login status
            return redirect(url_for('login'))
        
        user = db.session.query(User).filter_by(id=session['user_id']).first()
        if user.interests:
            user_interests = user.interests  # This will give you the list of interests
        else:
            user_interests = ["empty"]


        return render_template('upload.html', matched_projects=[], user_interests=user_interests)

# Trends Page
@app.route('/trends')
@token_required
def trends():
    if not session.get('user_id'): # Check login status
            return redirect(url_for('login'))
    trend_labels = ["AI", "Health", "Climate", "Mining", "Neuroscience"]
    trend_data = [12, 19, 7, 5, 8]
    return render_template('trends.html', trend_labels=trend_labels, trend_data=trend_data)

# Social Hub Page
@app.route("/social")
@token_required
def social():
    current_user_id = session.get("user_id")
    if not current_user_id:
        return redirect(url_for("login"))

    # Get current user's interest IDs
    interest_ids = db.session.execute(
        text("SELECT interest_id FROM user_interest WHERE user_id = :uid"),
        {"uid": current_user_id}
    ).fetchall()
    interest_ids = [row[0] for row in interest_ids]

    # Find users with shared interests
    if interest_ids:
        result = db.session.execute(
            text("""
                SELECT DISTINCT u.id, u.name
                FROM user u
                JOIN user_interest ui ON u.id = ui.user_id
                WHERE ui.interest_id IN :ids
                AND u.id != :uid
            """),
            {"ids": tuple(interest_ids), "uid": current_user_id}
        )
    else:
        result = []

    # Format result for template
    similar_users = [{"name": row[1], "interests": "Shared interests"} for row in result]
    return render_template("social.html", similar_users=similar_users)

# Settings Page
@app.route('/settings')
@token_required
def settings():
    if not session.get('user_id'): # Check login status
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])  # or however you're getting the current user
    form = Settings_ProfileForm(obj=user)  # pre-populate with user data


    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.faculty = form.faculty.data
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('settings'))

    return render_template('settings.html', form=form, user=user)


# Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()  # Instantiate the form
    if form.validate_on_submit():  # This checks if the form is submitted and valid
        username = form.username.data
        password = form.password.data
        email = form.email.data
        # Check if username already exists
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            form.username.errors.append("Username already exists.")
            return render_template('register.html', form=form)
        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            form.email.errors.append("Email already exists.") 
            return render_template('register.html', form=form)
        

        # Create a new user and hash the password
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        # Add the user to the database
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for('login'))  # Redirect to login page after successful registration
    
    return render_template('register.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)