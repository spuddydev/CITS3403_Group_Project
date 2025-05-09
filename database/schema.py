from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Boolean

db = SQLAlchemy()

# Association Tables
user_interest = db.Table('user_interest',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)

project_research_area = db.Table('project_research_area',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('research_area_id', db.Integer, db.ForeignKey('research_area.id'), primary_key=True)
)

project_interest = db.Table('project_interest',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)

project_supervisor = db.Table('project_supervisor',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('supervisor_id', db.Integer, db.ForeignKey('supervisor.id'), primary_key=True)
)

user_saved_projects = db.Table('user_saved_projects',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True)
)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)

    research_area_id = db.Column(db.Integer, db.ForeignKey('research_area.id'))
    faculty = db.relationship('ResearchArea', backref='users')

    interests = db.relationship('Interest', secondary=user_interest, backref='users')
    saved_projects = db.relationship('Project', secondary=user_saved_projects, backref='saved_by_users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interest_name = db.Column(db.String(100), nullable=False)
    interest_number = db.Column(db.Integer, nullable=False, default=0)

class ResearchArea(db.Model):
    __tablename__ = "research_area"
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(100), nullable=False)

class Supervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    link = db.Column(db.String(100), nullable=False)
    is_open = db.Column(db.Boolean, nullable=False)

    # Open project fields
    summary = db.Column(db.Text, nullable=True)
    close_date = db.Column(db.Date, nullable=True)

    # Closed project fields
    publication_date = db.Column(db.Date, nullable=True)

    research_area = db.relationship('ResearchArea', secondary=project_research_area, backref='projects')
    interests = db.relationship('Interest', secondary=project_interest, backref='projects')
    supervisors = db.relationship('Supervisor', secondary=project_supervisor, backref='projects')
