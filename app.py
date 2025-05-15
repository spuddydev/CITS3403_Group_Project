from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, current_app, make_response
from flask_sqlalchemy import SQLAlchemy
from database.schema import db, User, Project, Interest, Supervisor
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
    
    user = db.session.query(User).filter_by(id=session['user_id']).first()
    if user.interests:
        user_interests = user.interests  # This will give you the list of interests
    else:
        user_interests = None
    
    all_projects = db.session.query(Project).all()
    
    # Safely get available projects
    project_matches = []
    for i in range(min(3, len(all_projects))):
        project_matches.append(all_projects[i])

    connections = ["person1", "person2"]

    return render_template('dashboard.html',
                            username=           session['username'],
                            user_interests=     user_interests,
                            project_matches=    project_matches,
                            connections=        connections)

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
            user_interests = None


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
@app.route('/social')
@token_required
def social():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    # Get current user
    user = User.query.get(session['user_id'])
    
    # Get all user's connections
    connections = user.get_all_connections()
    
    # Get users that current user is not connected with (suggestions)
    suggested_users = User.query.filter(User.id != user.id).all()
    suggested_users = [u for u in suggested_users if not user.is_connected_to(u)]
    
    return render_template('social.html', 
                          username=session['username'],
                          connections=connections,
                          suggested_users=suggested_users[:5])  # Limit to 5 suggestions
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

# Supervisors Page
@app.route('/supervisors')
@token_required
def supervisors():
    if not session.get('user_id'):  # Check login status
        return redirect(url_for('login'))
    
    # Get all supervisors from database
    all_supervisors = db.session.query(Supervisor).all()
    
    return render_template('supervisors.html', 
                          username=session['username'],
                          supervisors=all_supervisors)

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
            
        if current_user.connect_with(other_user):
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'Connected with {other_user.username}',
                'username': other_user.username,
                'user_id': other_user.id
            })
        else:
            return jsonify({'success': False, 'message': 'Already connected or invalid operation'}), 400
            
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
            
        if current_user.disconnect_from(other_user):
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'Disconnected from {other_user.username}',
                'user_id': other_user.id
            })
        else:
            return jsonify({'success': False, 'message': 'Not connected or invalid operation'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)