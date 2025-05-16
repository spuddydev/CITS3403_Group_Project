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
def add_friend(user_a: User, user_b: User) -> None:
    if user_b not in user_a.connections:
        user_a.connections.append(user_b)
    if user_a not in user_b.connections:
        user_b.connections.append(user_a)
    db.session.commit()

def remove_friend(user_a: User, user_b: User) -> bool:
    if user_b in user_a.connections:
        user_a.connections.remove(user_b)
    if user_a in user_b.connections:
        user_b.connections.remove(user_a)
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
        user_interests = user.interests  
        user_connections = user.connections
    else:
        user_interests = None
        user_connections = None
    
    all_projects = db.session.query(Project).all()
    
    # Safely get project_matches
    project_matches = []
    if user_interests:
        interest_ids = [interest.id for interest in user_interests]
        project_matches = db.session.query(Project).join(Project.interests).filter(Interest.id.in_(interest_ids)).distinct().all()

    return render_template('dashboard.html',
                            username= session['username'],
                            user_interests= user_interests,
                            project_matches =project_matches,
                            connections = user_connections)

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
        matched_projects = []
        if user_interests:
            interest_ids = [i.id for i in user_interests]
            matched_projects = (Project.query.join(Project.interests).filter(Interest.id.in_(interest_ids)).distinct().all())
        
        return render_template('upload.html', matched_projects=matched_projects, user_interests=user_interests)

    # GET method
    user_interests = user.interests if user.interests else None
    matched_projects = []
    if user_interests:
        interest_ids = [i.id for i in user_interests]
        matched_projects = (Project.query.join(Project.interests).filter(Interest.id.in_(interest_ids)).distinct().all())
    return render_template('upload.html', matched_projects=matched_projects, user_interests=user_interests)

# Trends Page
@app.route('/trends')
@token_required
def trends():
    user = db.session.query(User).filter_by(id=session['user_id']).first()

    if not user or not user.interests:
        return render_template("trends.html",
                               user_interest_labels=[],
                               user_interest_data=[],
                               project_interest_labels=[],
                               project_interest_data=[])

    # Current user's interest IDs
    interest_ids = [interest.id for interest in user.interests]

    # User-specific project interest counts
    user_interest_results = db.session.query(
        Interest.interest_name,
        func.count(project_interest.c.project_id)
    ).join(project_interest).filter(
        Interest.id.in_(interest_ids)
    ).group_by(Interest.id).all()

    project_interest_labels = [name for name, count in user_interest_results]
    project_interest_data = [count for name, count in user_interest_results]

    # Count how many *other* users share these interests
    project_interest_results = db.session.query(
        Interest.interest_name,
        func.count(user_interest.c.user_id)
    ).join(user_interest).filter(
        Interest.id.in_(interest_ids),
        user_interest.c.user_id != user.id
    ).group_by(Interest.id).all()

    user_interest_labels = [name for name, count in project_interest_results]
    user_interest_data = [count for name, count in project_interest_results]

    return render_template("trends.html", 
                           user_interest_labels=user_interest_labels,
                           user_interest_data=user_interest_data,
                           project_interest_labels=project_interest_labels,
                           project_interest_data=project_interest_data)



# Social Hub Page
@app.route('/social')
@token_required
def social():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    # Get current user
    user = User.query.get(session['user_id'])
    
    # Get all user's connections
    connections = user.connections
    
    # Get users that current user is not connected with (suggestions)
    suggested_users = User.query.filter(User.id != user.id).all()
    suggested_users = [u for u in suggested_users if not user in connections]
    
    return render_template('social.html', 
                          username=session['username'],
                          connections=connections,
                          suggested_users=suggested_users[:5])  # Limit to 5 suggestions


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



# Projects Page
@app.route('/projects')
@token_required
def projects():
    if not session.get('user_id'):  # Check login status
        return redirect(url_for('login'))
    
    # Get all projects from database
    all_projects = db.session.query(Project).all()
    
    return render_template('projects.html', 
                          username=session['username'],
                          projects=all_projects)

# Saved Projects Page
@app.route('/saved')
@token_required
def saved():
    if not session.get('user_id'):  # Check login status
        return redirect(url_for('login'))
    
    # Get the current user
    user = db.session.query(User).filter_by(id=session['user_id']).first()
    
    # Get user's saved projects
    saved_projects = user.saved_projects if user.saved_projects else []
    
    return render_template('saved.html', 
                          username=session['username'],
                          saved_projects=saved_projects)

# Reseachers Page
@app.route('/researchers')
@token_required
def researchers():
    if not session.get('user_id'):  # Check login status
        return redirect(url_for('login'))
    
    # Get all researchers from database
    all_researchers = db.session.query(Researcher).all()
    
    return render_template('researchers.html', 
                          username=session['username'],
                          researchers=all_researchers)

# User Profile Page
@app.route('/profile')
@token_required
def profile():
    if not session.get('user_id'):  # Check login status
        return redirect(url_for('login'))
    
    # Get current user
    user = db.session.query(User).filter_by(id=session['user_id']).first()
    
    # If user.faculty is an ID, let's get the actual ResearchArea object
    if user.faculty is None and user.research_area_id is not None:
        from database.schema import ResearchArea
        user.faculty = db.session.query(ResearchArea).filter_by(id=user.research_area_id).first()
    
    return render_template('profile.html', 
                          username=session['username'],
                          user=user)

# Save Project Route (for AJAX)
@app.route('/save_project/<int:project_id>', methods=['POST'])
@token_required
def save_project(project_id):
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        user = db.session.query(User).filter_by(id=session['user_id']).first()
        project = db.session.query(Project).filter_by(id=project_id).first()
        
        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
        
        # Check if already saved
        if project in user.saved_projects:
            user.saved_projects.remove(project)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Project removed from saved', 'saved': False})
        else:
            user.saved_projects.append(project)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Project saved', 'saved': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/connect/<int:user_id>', methods=['POST'])
@token_required
def connect_user(user_id):
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        current_user = User.query.get(session['user_id'])
        other_user = User.query.get(user_id)
        
        if not other_user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        if other_user not in current_user.connections:
            add_friend(current_user, other_user)
            return jsonify({
                'success': True, 
                'message': f'Connected with {other_user.username}',
                'username': other_user.username,
                'user_id': other_user.id
            })
        else:
            return jsonify({'success': False, 'message': 'Already connected'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/disconnect/<int:user_id>', methods=['POST'])
@token_required
def disconnect_user(user_id):
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        current_user = User.query.get(session['user_id'])
        other_user = User.query.get(user_id)
        
        if not other_user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        if other_user in current_user.connections:
            remove_friend(current_user, other_user)
            return jsonify({
                'success': True, 
                'message': f'Disconnected from {other_user.username}',
                'user_id': other_user.id
            })
        else:
            return jsonify({'success': False, 'message': 'Not connected'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)