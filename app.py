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
    # look for token in headers
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
                error_message = "Invalid username or password. Please try again."
                # Use flash message instead of adding to form errors
                flash(error_message, "error")
                return render_template('login.html', form=form, error=error_message)
        
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
    else:
        user_interests = None
    
    all_projects = db.session.query(Project).all()
    
    # Safely get available projects
    project_matches = []
    for i in range(min(3, len(all_projects))):
        project_matches.append(all_projects[i])

    # Get user's actual connections from database
    connections = user.get_all_connections()
    
    # Get suggested connections - don't filter out supervisors
    suggested_users = User.query.filter(User.id != user.id).limit(2).all()
    suggested_users = [u for u in suggested_users if not user.is_connected_to(u)]

    return render_template('dashboard.html',
                           username=session['username'],
                           user_interests=user_interests,
                           project_matches=project_matches,
                           connections=connections,
                           suggested_users=suggested_users,
                           is_authenticated_page=True,
                           user_name=session.get('username'))

# Upload Page (GET and POST for form)
@app.route('/upload', methods=['GET', 'POST'])
@token_required
def upload():
    user = db.session.query(User).get(session['user_id'])
    error = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'submit':
            interest_id = request.form.get('interest_id')
            keyword = request.form.get('keywords')
            
            # Validate the input
            if not interest_id or not keyword:
                error = "Please select a valid research interest from the suggestions."
            else:
                interest = Interest.query.get(interest_id)

                if interest:
                    if interest not in user.interests:
                        user.interests.append(interest)
                        db.session.commit()
                        flash(f"Added '{interest.interest_name}' to your interests.", "success")
                    else:
                        error = f"'{interest.interest_name}' is already in your interests."
                else:
                    error = "The selected interest could not be found. Please try again."

        elif action == 'refresh':
            user.interests.clear()
            db.session.commit()
            flash("Your interests have been cleared.", "success")

        # Re-fetch after changes
        user_interests = user.interests if user.interests else None
        matched_projects = []  # You can plug in matching logic here
        return render_template('upload.html', 
                              matched_projects=matched_projects, 
                              user_interests=user_interests,
                              username=session['username'],
                              is_authenticated_page=True,
                              error=error,
                              user_name=session.get('username'))

    # GET method
    user_interests = user.interests if user.interests else None
    return render_template('upload.html', 
                          matched_projects=[], 
                          user_interests=user_interests,
                          username=session['username'],
                          is_authenticated_page=True,
                          user_name=session.get('username'))

# Projects Page
@app.route('/projects')
@token_required
def projects():
    # Get page number and filters from request args
    page = request.args.get('page', 1, type=int)
    faculty = request.args.get('faculty', '')
    status = request.args.get('status', '')
    per_page = 12  # Number of projects per page
    
    # Start with base query
    query = Project.query
    
    # Apply filters if provided
    if faculty:
        query = query.join(Project.research_areas).filter(ResearchArea.area.ilike(f'%{faculty}%'))
    
    if status == 'open':
        query = query.filter(Project.is_open == True)
    elif status == 'closed':
        query = query.filter(Project.is_open == False)
    
    # Paginate the results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    projects = pagination.items
    
    return render_template('projects.html', 
                          username=session['username'],
                          projects=projects,
                          pagination=pagination,
                          faculty=faculty,
                          status=status,
                          is_authenticated_page=True,
                          user_name=session.get('username'))  # Add this for avatar

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
                          saved_projects=saved_projects,
                          is_authenticated_page=True,  # Add this
                          user_name=session.get('username'))  # Add this for avatar

# Trends Page
@app.route('/trends')
@token_required
def trends():
    user = db.session.query(User).filter_by(id=session['user_id']).first()
    if user.interests:
        user_interests = user.interests  # This will give you the list of interests
    else:
        user_interests = None

    # Initialize with empty data
    trend_labels = []
    trend_data = []

    if user_interests:
        interest_ids = [interest.id for interest in user_interests]
        results = db.session.query(
            Interest.interest_name,
            func.count(project_interest.c.project_id)
        ).join(project_interest).filter(
            Interest.id.in_(interest_ids)
        ).group_by(Interest.id).all()

        trend_labels = [name for name, count in results]
        trend_data = [count for name, count in results]

    return render_template('trends.html',
                          username=session['username'],
                          trend_labels=trend_labels,  # Now always defined
                          trend_data=trend_data,      # Now always defined
                          is_authenticated_page=True,
                          user_name=session.get('username'))



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
    # Don't exclude supervisors - show all potential connections
    suggested_users = User.query.filter(User.id != user.id).all()
    suggested_users = [u for u in suggested_users if not user.is_connected_to(u)]
    
    return render_template('social.html',
                          username=session['username'],
                          connections=connections,
                          suggested_users=suggested_users,
                          is_authenticated_page=True,
                          user_name=session.get('username'))  # Add this for avatar


# Profile Page
@app.route('/profile')
@token_required
def profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    # Get the current user with all related data
    user = User.query.get(session['user_id'])
    
    return render_template('profile.html',
                          username=session['username'],
                          user=user,
                          is_authenticated_page=True,
                          user_name=session.get('username'))

# Settings Page
@app.route('/settings')
@token_required
def settings():
    user = User.query.get(session['user_id'])
    
    return render_template('settings.html', 
                          username=session['username'],
                          user=user,
                          is_authenticated_page=True,  # Add this flag
                          user_name=session.get('username'))  # Add this for avatar

@app.route('/supervisors')
@token_required
def supervisors():
    supervisors = db.session.query(Researcher).all()
    
    return render_template('supervisors.html',
                           username=session['username'],
                           supervisors=supervisors,
                           is_authenticated_page=True,
                           user_name=session.get('username'))

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
# Modify the connect_user route to only allow connections between regular users
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
@app.route('/api/projects')
@token_required
def get_projects():
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    offset = (page - 1) * per_page
    
    projects = db.session.query(Project).offset(offset).limit(per_page).all()
    
    # Convert projects to dictionaries for JSON serialization
    project_list = []
    for project in projects:
        project_data = {
            'id': project.id,
            'title': project.title,
            'link': project.link,
            'is_open': project.is_open,
            'summary': project.summary,
            'close_date': project.close_date.isoformat() if project.close_date else None
        }
        project_list.append(project_data)
    
    return jsonify({
        'projects': project_list,
        'page': page,
        'per_page': per_page,
        'has_more': len(projects) == per_page
    })
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    
    # Create response and clear the JWT token cookie
    response = make_response(redirect(url_for('home')))
    response.set_cookie('jwt_token', '', max_age=0)
    
    flash("You have been successfully logged out.", "success")
    return response
if __name__ == '__main__':
    app.run(debug=True)