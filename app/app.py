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
)
from oauthlib.oauth2 import WebApplicationClient
import requests
from dotenv import load_dotenv
import logging

import sys

# Assuming that this file (app.py) is in the 'app' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from db.models import db, User, MoodEntry

# Load enviroment variables
load_dotenv()

# Configuration
GOOGLE_CLIENT_ID = os.getenv("CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or os.urandom(24)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Flask logging
app.logger.setLevel(logging.INFO)  # Set log level to INFO
handler = logging.FileHandler('../logs/app.log')  # Log to a file
app.logger.addHandler(handler)

# db = SQLAlchemy(app)
db.init_app(app)

# User session management setup
login_manager = LoginManager()
# login_manager.init_app(current_app)
login_manager.init_app(app)

@login_manager.unauthorized_handler
def unauthorized():
    return "You must be logged in to access this content.", 403

# OAuth2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

with app.app_context():
    db.create_all()

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    app.logger.info('User Initialized')
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
        app.logger.info('New user added to database successfully')

    # Begin user session by logging the user in
    login_user(user)

    app.logger.info(f'User with {user.id} Authenticated successfully')

    # Send user back to homepage
    return redirect(url_for("index"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    app.logger.info('Logged out user successfully')
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
    app.logger.info('User mood added successfully')

    return redirect(url_for('index'))

@app.errorhandler(500)
def server_error(error):
    app.logger.exception('An exception occurred during a request.')
    return 'Internal Server Error', 500

if __name__ == "__main__":
    app.run(ssl_context="adhoc")
