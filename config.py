import os
import logging


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY is read from the environment (loaded from .env at startup; see
    # webapp/__init__.py). It signs session cookies and CSRF tokens, so in
    # production it MUST be a long random value kept secret. The fallback below
    # is only for local development convenience -- never rely on it in prod.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-change-me')
    FLASK_ADMIN_FLUID_LAYOUT = True

    # Database location.
    #   DATABASE_URL, if set, wins outright (e.g. a full sqlite:/// path or a
    #   Postgres URL). Otherwise we build a SQLite URL from DATABASE_PATH, which
    #   defaults to the in-repo instance/ folder for local development.
    #
    #   In PRODUCTION, set DATABASE_PATH (in .env) to a location OUTSIDE the
    #   git checkout -- e.g. /var/lib/holidayhopetree/webapp2.db -- so deploys
    #   can never touch the data.
    INSTANCE_PATH = os.path.join(basedir, 'instance')
    DATABASE_PATH = os.environ.get(
        'DATABASE_PATH', os.path.join(INSTANCE_PATH, 'webapp2.db')
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{DATABASE_PATH}"
    )

    # Admin login (single shared account), read from the environment.
    #   ADMIN_USERNAME       - login name (default "admin")
    #   ADMIN_PASSWORD_HASH  - a Werkzeug hash, NOT the plaintext password.
    # Generate the hash with:  python cli.py create-admin-hash
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')

    # Read-only login (optional second account). Can view everything and edit
    # ONLY comment/note-type fields. Leave the hash blank to disable it.
    READONLY_USERNAME = os.environ.get('READONLY_USERNAME', 'readonly')
    READONLY_PASSWORD_HASH = os.environ.get('READONLY_PASSWORD_HASH', '')

    # Session cookie hardening. SECURE is overridden to True in ProdConfig so
    # local http development still works.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    # Keep admin sessions reasonably short-lived.
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours

    # Don't expire CSRF tokens on a separate, shorter clock. By default Flask-WTF
    # tokens expire after 1 hour, which breaks inline edits on a list page that
    # has been left open (you'd get "The CSRF token has expired" on save). With
    # this set to None the token is still bound to the session and secret key
    # (so it remains secure) and stays valid for the life of the session.
    WTF_CSRF_TIME_LIMIT = None


class DevConfig(Config):
    DEBUG = True
    TESTING = True
    LOGGING_LEVEL = logging.DEBUG


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
    LOGGING_LEVEL = logging.WARNING

    # In production, never fall back to the insecure development key. Read it
    # from the environment (.env). The actual "fail fast if missing" check runs
    # in create_app() when ProdConfig is selected -- see webapp/__init__.py --
    # so that merely importing this module in development never errors.
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Only send cookies over HTTPS in production.
    SESSION_COOKIE_SECURE = True