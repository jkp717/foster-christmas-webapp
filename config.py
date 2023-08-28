import os
import logging


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY = os.environ.get('SECRET_KEY')
    SECRET_KEY = 'insecure'
    # SECRET_KEY_SALT = base64.b64decode(bytes(os.environ.get('SECRET_KEY_SALT'), "utf-8"))
    FLASK_ADMIN_FLUID_LAYOUT = True
    SQLITE_DATABASE_PATH = os.path.join(basedir, 'instance', 'webapp.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{SQLITE_DATABASE_PATH}"
    REGISTER_CHILD_DISCLAIMER = """
        <b>PLEASE READ!</b> Thank you so much for making a difference in a child’s life!
        This Christmas we are striving to make every child’s wish list come true!
        Donors and sponsors will choose wish lists to fulfill. Kindly consider that these
        wish lists are meant for donations, and it might pose a challenge to secure sponsors for highly costly lists.
        Please refrain from including electronics exceeding a value of $200.
    """


class DevConfig(Config):
    DEBUG = True
    TESTING = True
    LOGGING_LEVEL = logging.DEBUG


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
    LOGGING_LEVEL = logging.WARNING