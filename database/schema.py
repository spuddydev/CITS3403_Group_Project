from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association Tables
user_interest = db.Table('user_interest',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)

# Add this association table for user connections
user_connections = db.Table('user_connections',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

project_research_area = db.Table('project_research_area',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('research_area_id', db.Integer, db.ForeignKey('research_area.id'), primary_key=True)
)

project_interest = db.Table('project_interest',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)

project_researcher = db.Table('project_researcher',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('researcher_id', db.Integer, db.ForeignKey('researcher.id'), primary_key=True)
)

user_saved_projects = db.Table('user_saved_projects',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True)
)

user_connections = db.Table('connection',  # actual table name in the DB
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('connection_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False)

    research_area_id = db.Column(db.Integer, db.ForeignKey('research_area.id'))
    faculty = db.relationship('ResearchArea', backref='users')

    # Add this connections relationship
    connections = db.relationship(
        'User', 
        secondary=user_connections,
        primaryjoin=(id == user_connections.c.user_id),
        secondaryjoin=(id == user_connections.c.friend_id),
        backref=db.backref('connected_by', lazy='dynamic'),
        lazy='dynamic'
    )

    interests = db.relationship('Interest', secondary=user_interest, backref='users')
    saved_projects = db.relationship('Project', secondary=user_saved_projects, backref='saved_by_users')
        
    connections = db.relationship(
        'User',
        secondary=user_connections,
        primaryjoin=id == user_connections.c.user_id,
        secondaryjoin=id == user_connections.c.connection_id,
        back_populates='connections_reverse'
    )

    connections_reverse = db.relationship(
        'User',
        secondary=user_connections,
        primaryjoin=id == user_connections.c.connection_id,
        secondaryjoin=id == user_connections.c.user_id,
        back_populates='connections'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def connect_with(self, user):
        if user.id == self.id:
            return False
        if not self.is_connected_to(user):
            self.connections.append(user)
            return True
        return False
    
    def disconnect_from(self, user):
        if self.is_connected_to(user):
            self.connections.remove(user)
            return True
        return False
    
    def is_connected_to(self, user):
        return self.connections.filter(user_connections.c.friend_id == user.id).count() > 0
    
    def get_all_connections(self):
        return self.connections.all()

class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interest_name = db.Column(db.String(100), nullable=False)
    
class ResearchArea(db.Model):
    __tablename__ = "research_area"
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(100), nullable=False)

class Researcher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    # Remove the backref, use back_populates instead
    projects = db.relationship('Project', secondary=project_supervisor, back_populates='supervisors')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    link = db.Column(db.String(100), nullable=False)
    is_open = db.Column(db.Boolean, nullable=False)
    summary = db.Column(db.Text, nullable=False)

    # Only for open projects
    close_date = db.Column(db.Date, nullable=True)

    research_areas = db.relationship('ResearchArea', secondary=project_research_area, backref='projects')
    interests = db.relationship('Interest', secondary=project_interest, backref='projects')
    researchers = db.relationship('Researcher', secondary=project_researcher, backref='projects')
