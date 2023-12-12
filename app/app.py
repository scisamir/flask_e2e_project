# app.py

from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///mood_tracker.db"
app.config['SECRET_KEY'] = 'wZMwN7LzQT6qGPI-aar2mbvklFR4a9HcMiTomgnUW9k'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

google_bp = make_google_blueprint(client_id='1034434692939-4lbfgvkauc66lru8hot205q9sa5965p2.apps.googleusercontent.com',
                                  client_secret="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",
                                  )
app.register_blueprint(google_bp, url_prefix='/login')

db.create_all()

class User(db.Model, UserMixin):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    mood_entries = db.relationship('MoodEntry', backref='user', lazy=True)

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(10), nullable=False)
    activities = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.String(50), db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/login')
def login():
    if not current_user.is_authenticated:
        return render_template('login.html')
    resp = google.get('/plus/v1/people/me')
    assert resp.ok, resp.text
    user_id = resp.json()['id']

    user = User.query.get(user_id)
    if user is None:
        user = User(id=user_id, name=resp.json()['displayName'], email=resp.json()['emails'][0]['value'])
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    entries = MoodEntry.query.filter_by(user_id=current_user.id).limit(5).all()
    return render_template('index.html', entries=entries)

@app.route('/log_mood', methods=['POST'])
@login_required
def log_mood():
    mood = request.form['mood']
    activities = request.form['activities']

    new_mood_entry = MoodEntry(mood=mood, activities=activities, user_id=current_user.id)
    db.session.add(new_mood_entry)
    db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
