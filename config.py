import os
import logging


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY = os.environ.get('SECRET_KEY')
    SECRET_KEY = 'insecure'
    # SECRET_KEY_SALT = base64.b64decode(bytes(os.environ.get('SECRET_KEY_SALT'), "utf-8"))
    FLASK_ADMIN_FLUID_LAYOUT = True
    INSTANCE_PATH = os.path.join(basedir, 'instance')
    SQLITE_DATABASE_PATH = os.path.join(INSTANCE_PATH, 'webapp.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_PATH, SQLITE_DATABASE_PATH)}"


class DevConfig(Config):
    DEBUG = True
    TESTING = True
    LOGGING_LEVEL = logging.DEBUG


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
    LOGGING_LEVEL = logging.WARNING