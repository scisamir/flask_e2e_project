# Mood Tracker

A simple flask web app designed to help users track and log thier daily moods along with associated activities. The application uses SQLAlchemy for database interaction, Flask-Login for user authentication, and oauthlib for integrating OAuth authentication with Google.

## How to run the app locally

1. Clone this repository

```
git clone https://github.com/scisamir/flask_e2e_project.git
cd flask_e2e_project
```

2. Install python virtual env (if not installed) and activate

```
pip install virtualenv
python -m venv env
source env/bin/activate
```

3. Install python requirements

```
pip install -r requirements.txt
```

4. Run the app locally

```
cd app
python app.py
```

The app should be started at `127.0.0.1:5000`


## Using docker

1. Pull the image from docker

```
docker pull scisamir/flask_e2e_project
```

2. Run the image container

```
docker run -p 5000:5000 scisamir/flask_e2e_project
```

The app should be started at `127.0.0.1:5000`