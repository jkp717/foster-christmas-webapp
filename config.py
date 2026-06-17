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
    INSTANCE_PATH = os.path.join(basedir, 'instance')
    SQLITE_DATABASE_PATH = os.path.join(INSTANCE_PATH, 'webapp2.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_PATH, SQLITE_DATABASE_PATH)}"


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