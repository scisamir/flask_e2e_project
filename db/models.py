from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    profile_pic = db.Column(db.String(100))
    mood_entries = db.relationship('MoodEntry', backref='user', lazy=True)

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(10), nullable=False)
    activities = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.String(50), db.ForeignKey('user.id'), nullable=False)