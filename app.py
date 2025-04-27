from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv("SQLALCEHMY_TRACK_MODIFICATIONS").lower() in ("true", 1)

db = SQLAlchemy(app)

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# Dashboard Page
@app.route('/dashboard')
def dashboard():
    user_name = "ashane"  # Example user name
    return render_template('dashboard.html', user_name=user_name)

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

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
