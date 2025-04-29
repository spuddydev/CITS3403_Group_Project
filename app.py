from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from database.schema import db
from dotenv import load_dotenv
import os

# Initialise environment
load_dotenv()

# Initialise flask app
app = Flask(__name__)

# Configure app and initialise

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///site.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False").lower() in ("true", "1")
db.init_app(app)

# If no database exists, create one !
with app.app_context():
    if not os.path.exists('site.db'):
        db.create_all()

# Home Page
@app.route('/')
def default():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

# Dashboard Page
@app.route('/dashboard')
def dashboard():
    username = "ashane"  # Example user name
    return render_template('dashboard.html', user_name=username)

# Upload Page (GET and POST for form)
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        keywords = request.form.get('keywords')
        # Example: Pretend to match projects based on keywords
        matched_projects = [
            {'title': 'AI in Healthcare', 'supervisor': 'Dr. Smith', 'link': '#'},
            {'title': 'Robotics in Mining', 'supervisor': 'Dr. Lee', 'link': '#'}
        ]
        return render_template('upload.html', matched_projects=matched_projects)
    else:
        matched_projects = []  # No results on GET
        return render_template('upload.html', matched_projects=matched_projects)

# Trends Page
@app.route('/trends')
def trends():
    trend_labels = ["AI", "Health", "Climate", "Mining", "Neuroscience"]
    trend_data = [12, 19, 7, 5, 8]
    return render_template('trends.html', trend_labels=trend_labels, trend_data=trend_data)

# Social Hub Page
@app.route('/social')
def social():
    similar_users = [
        {'name': 'John Doe', 'interests': 'AI, Robotics'},
        {'name': 'Jane Smith', 'interests': 'Health, Neuroscience'}
    ]
    return render_template('social.html', similar_users=similar_users)

# Settings Page
@app.route('/settings')
def settings():
    # Mock data for demonstration purposes
    user = {
        'username': 'ashane',
        'email': 'ashane@example.com',
        'faculty': 'Computer Science'
    }
    
    preferences = {
        'new_matches': True,
        'connection_requests': True,
        'trending_updates': False
    }
    
    return render_template('settings.html', user=user, preferences=preferences)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)