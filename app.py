from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, current_app, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from database.schema import *
from dotenv import load_dotenv
from functools import wraps
import os
import jwt
import datetime
from forms import RegisterForm, LoginForm, Settings_ProfileForm



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

# Helper functions
def add_mutual_friend(user_a: User, user_b: User) -> None:
    if user_b not in user_a.connections:
        user_a.connections.append(user_b)
    if user_a not in user_b.connections:
        user_b.connections.append(user_a)
    db.session.commit()


# Routing functions
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

@app.route('/autocomplete_interests')
def autocomplete_interests():
    q = request.args.get('q', '')
    if not q:
        return jsonify([])
    interests = Interest.query.filter(Interest.interest_name.ilike(f'%{q}%')).limit(10).all()
    return jsonify([{"id": i.id, "name": i.interest_name} for i in interests])



# Unprotected pages
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
                    'user_id': user.id,
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



# Protected pages
# Dashboard Page
@app.route('/dashboard')
@token_required
def dashboard():
    user = db.session.query(User).filter_by(id=session['user_id']).first()
    if user.interests:
        user_interests = user.interests  # This will give you the list of interests
    else:
        user_interests = None
    
    all_projects = db.session.query(Project).all() # DEVELOPEMENT----getting example projects for now
    project_matches = [all_projects[0],all_projects[1],all_projects[2]]

    connections = ["person1", "person2"]

    return render_template('dashboard.html',
                            username= session['username'],
                            user_interests= user_interests,
                            project_matches =project_matches,
                            connections = connections)

# Upload Page (GET and POST for form)
@app.route('/upload', methods=['GET', 'POST'])
@token_required
def upload():
    user = db.session.query(User).get(session['user_id'])

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'submit':
            interest_id = request.form.get('interest_id')
            interest = Interest.query.get(interest_id)

            if interest:
                if interest not in user.interests:
                    user.interests.append(interest)
                    db.session.commit()
            else:
                pass
                # Add an invalid interest notifier here

        elif action == 'refresh':
            user.interests.clear()
            db.session.commit()

        # Re-fetch after changes
        user_interests = user.interests if user.interests else None
        matched_projects = []  # You can plug in matching logic here
        return render_template('upload.html', matched_projects=matched_projects, user_interests=user_interests)

    # GET method
    user_interests = user.interests if user.interests else None
    return render_template('upload.html', matched_projects=[], user_interests=user_interests)

# Trends Page
@app.route('/trends')
@token_required
def trends():
    user = db.session.query(User).filter_by(id=session['user_id']).first()
    if user.interests:
        user_interests = user.interests  # This will give you the list of interests
    else:
        user_interests = None

    interest_ids = [interest.id for interest in user_interests]
    if user_interests:
        results = db.session.query(
            Interest.interest_name,
            func.count(project_interest.c.project_id)
        ).join(project_interest).filter(
            Interest.id.in_(interest_ids)
        ).group_by(Interest.id).all()

        trend_labels = [name for name, count in results]
        trend_data = [count for name, count in results]

    return render_template("trends.html", trend_labels=trend_labels, trend_data=trend_data)



# Social Hub Page
@app.route('/social')
@token_required
def social():
    similar_users = [
        {'name': 'John Doe', 'interests': 'AI, Robotics'},
        {'name': 'Jane Smith', 'interests': 'Health, Neuroscience'}
    ]
    return render_template('social.html', similar_users=similar_users)

# Settings Page
@app.route('/settings')
@token_required
def settings():
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



if __name__ == '__main__':
    app.run(debug=True)