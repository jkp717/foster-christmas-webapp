"""
Shared pytest fixtures for the Holiday Hope Tree app.

Design goals:
  * One clean way to spin up a fully-configured app against a throwaway,
    temp-file SQLite database (closer to production than in-memory, and free of
    the multi-connection pitfalls of sqlite:///:memory:).
  * Reference tables (gender, race, fav_color, ...) seeded exactly the way the
    app seeds them, by reusing config.db_defaults -- so tests never drift from
    the real seed data.
  * Small, composable helpers (login_admin, login_readonly) and access to the
    model factories so individual test modules stay short and readable.

Adding coverage later should rarely require touching this file: new models get
exercised via tests/factories.py, new endpoints via the `client` fixture.
"""

import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

# Known test credentials. The hashes are injected into the app config, and the
# plaintext is used by the login helpers below.
TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "admin-pw-123"
TEST_READONLY_USERNAME = "readonly"
TEST_READONLY_PASSWORD = "readonly-pw-123"


def _test_config(db_path):
    """Config overrides applied on top of DevConfig for every test app."""
    return {
        "TESTING": True,
        "DEBUG": False,
        # Temp-file SQLite: a real file on disk, unique per test, deleted after.
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "DATABASE_PATH": db_path,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # Stable signing key so sessions/CSRF behave deterministically.
        "SECRET_KEY": "test-secret-key-not-for-production",
        # Disable CSRF in tests so we can POST forms directly. Security tests
        # that specifically check CSRF re-enable it on their own app instance.
        "WTF_CSRF_ENABLED": False,
        # Don't rate-limit during tests.
        "RATELIMIT_ENABLED": False,
        # Known admin + read-only credentials (hashes; verify() reads these).
        "ADMIN_USERNAME": TEST_ADMIN_USERNAME,
        "ADMIN_PASSWORD_HASH": generate_password_hash(TEST_ADMIN_PASSWORD),
        "READONLY_USERNAME": TEST_READONLY_USERNAME,
        "READONLY_PASSWORD_HASH": generate_password_hash(TEST_READONLY_PASSWORD),
        # Secure cookies require HTTPS; tests run over http.
        "SESSION_COOKIE_SECURE": False,
    }


def _seed_reference_data(db):
    """
    Seed the reference tables (gender/race/fav_color/shoe_size/clothing_size/
    dhs_office/church) using the SAME db_defaults the app uses at first-run, so
    test data matches production seed data.
    """
    from config import db_defaults

    tbl_to_cls = {}
    for mapper in db.Model.registry.mappers:
        cls = mapper.class_
        if not cls.__name__.startswith("_"):
            tbl_to_cls[cls.__tablename__] = cls

    for tbl, cols in db_defaults.items():
        model_cls = tbl_to_cls.get(tbl)
        if model_cls is None:
            continue
        for col_name, values in cols.items():
            for val in values:
                obj = model_cls()
                setattr(obj, col_name, val)
                db.session.add(obj)
    db.session.commit()


@pytest.fixture
def app():
    """
    A fresh application bound to a throwaway temp-file SQLite database, with
    reference data seeded. Yields the app; tears down the DB file afterward.

    Because create_app() only auto-creates/seeds when the DB *file* is absent,
    and here we manage schema + seed explicitly, the fixture is deterministic
    regardless of create_app's first-run logic.
    """
    from webapp import create_app
    from webapp.models import db

    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="hht_test_")
    os.close(fd)
    # Start from a clean slate so create_all() builds the full current schema.
    if os.path.exists(db_path):
        os.remove(db_path)

    application = create_app(debug=True, config_override=_test_config(db_path))

    with application.app_context():
        # create_all is idempotent; ensure the full schema exists, then seed.
        db.create_all()
        # Seed reference data only if it isn't already present (create_app may
        # have seeded if it considered the file new).
        from webapp.models import Gender
        if db.session.query(Gender).first() is None:
            _seed_reference_data(db)

    yield application

    # Teardown: drop the session and remove the temp DB file.
    with application.app_context():
        db.session.remove()
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture
def db_session(app):
    """The SQLAlchemy session, inside an app context for the test's duration."""
    from webapp.models import db
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture
def client(app):
    """A Flask test client for issuing HTTP requests at the app."""
    return app.test_client()


# --------------------------------------------------------------------------
# Auth helpers -- exposed as fixtures returning callables, so a test can do:
#   def test_x(client, login_admin):
#       login_admin()
#       ...
# --------------------------------------------------------------------------
def _do_login(client, username, password):
    return client.post(
        "/admin/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


@pytest.fixture
def login_admin(client):
    def _login():
        return _do_login(client, TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
    return _login


@pytest.fixture
def login_readonly(client):
    def _login():
        return _do_login(client, TEST_READONLY_USERNAME, TEST_READONLY_PASSWORD)
    return _login


@pytest.fixture
def logout(client):
    def _logout():
        return client.get("/admin/logout", follow_redirects=True)
    return _logout
