# Python standard libraries
import json
import os

# Third party libraries
from flask import Flask, redirect, request, url_for, render_template
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
    UserMixin,
)
from oauthlib.oauth2 import WebApplicationClient
import requests
from flask_sqlalchemy import SQLAlchemy

# Configuration
GOOGLE_CLIENT_ID = '1034434692939-4lbfgvkauc66lru8hot205q9sa5965p2.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root@/mysql?unix_socket=/cloudsql/flask-e2e-project:flask-e2e-project"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///mood_tracker.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User session management setup
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.unauthorized_handler
def unauthorized():
    return "You must be logged in to access this content.", 403

# OAuth2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

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

with app.app_context():
    db.create_all()

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route("/")
def index():
    if current_user.is_authenticated:
        entries = MoodEntry.query.filter_by(user_id=current_user.id).limit(5).all()
        myuser = { 'username': current_user.name, 'email': current_user.email, 'profile_pic': current_user.profile_pic}
        return render_template('index.html', myuser=myuser, entries=entries)
    else:
        return render_template('login.html')


@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    user = User.query.get(unique_id)

    # Doesn't exist? Add to database
    if not user:
        user = User(
        id=unique_id, name=users_name, email=users_email, profile_pic=picture
    )
        db.session.add(user)
        db.session.commit()

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route('/log_mood', methods=['POST'])
@login_required
def log_mood():
    mood = request.form['mood']
    activities = request.form['activities']

    new_mood_entry = MoodEntry(mood=mood, activities=activities, user_id=current_user.id)
    db.session.add(new_mood_entry)
    db.session.commit()

    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(ssl_context="adhoc")
