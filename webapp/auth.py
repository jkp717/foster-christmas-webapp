"""
Authentication for the admin interface.

Two shared logins, configured entirely from environment variables (.env). No
credentials are stored in the database.

Full admin (can do everything):
    ADMIN_USERNAME        - the admin login name (default "admin")
    ADMIN_PASSWORD_HASH   - a Werkzeug password hash (NOT the plaintext)

Read-only user (can view everything; may edit ONLY comment/note fields):
    READONLY_USERNAME       - the read-only login name (default "readonly")
    READONLY_PASSWORD_HASH  - a Werkzeug password hash (NOT the plaintext)

Generate hashes with:  python cli.py create-admin-hash
then paste each into .env as the matching *_PASSWORD_HASH.

This module exposes:
  - login_manager       : the Flask-Login manager (init in create_app)
  - AdminUser           : a UserMixin backed by env config, with a role
  - current_role()      : 'admin' | 'readonly' | None
  - is_comment_field()  : name-based test for comment/note fields
  - _SecureViewMixin    : Flask-Admin view gated behind login
  - LoginForm / login / logout helpers
"""

import re

from flask import current_app, redirect, url_for, request, flash
from flask_login import (
    LoginManager, UserMixin, current_user, login_user, logout_user,
)
from werkzeug.security import check_password_hash

login_manager = LoginManager()
# Endpoint Flask-Login redirects to when an anonymous user hits a protected page.
login_manager.login_view = "auth_login"
login_manager.login_message = "Please sign in to access the admin area."
login_manager.login_message_category = "error"

ROLE_ADMIN = "admin"
ROLE_READONLY = "readonly"

# Field names that a read-only user is still allowed to edit. Matched
# case-insensitively against the column name, so "note", "Notes", "comment",
# "Comments", "internal_notes", "case_comment", etc. all qualify.
_COMMENT_FIELD_PATTERN = re.compile(r"(note|notes|comment|comments)$", re.IGNORECASE)


def is_comment_field(name):
    """True if a column/field name is a comment/note-type field."""
    if not name:
        return False
    # Match a trailing 'note(s)'/'comment(s)' token, with or without a
    # separator prefix (e.g. 'note', 'case_notes', 'gift comment').
    cleaned = name.strip().lower().replace(" ", "_")
    if _COMMENT_FIELD_PATTERN.search(cleaned):
        return True
    # Also catch exact bare matches just in case.
    return cleaned in {"note", "notes", "comment", "comments", "memo", "remarks"}


class AdminUser(UserMixin):
    """
    A shared login identified by username, carrying a role: full 'admin' or
    'readonly'. Credentials come from env config; there is at most one of each.
    """
    def __init__(self, username, role):
        self.id = username
        self.role = role

    # --- configured account names -----------------------------------------
    @staticmethod
    def _admin_username():
        return current_app.config.get("ADMIN_USERNAME") or "admin"

    @staticmethod
    def _readonly_username():
        return current_app.config.get("READONLY_USERNAME") or "readonly"

    @classmethod
    def get(cls, username):
        """Rebuild the user (and its role) from a stored username."""
        if not username:
            return None
        if username == cls._admin_username():
            return cls(username, ROLE_ADMIN)
        # Only treat as read-only if that account is actually configured.
        if (username == cls._readonly_username()
                and current_app.config.get("READONLY_PASSWORD_HASH")):
            return cls(username, ROLE_READONLY)
        return None

    @classmethod
    def verify(cls, username, password):
        """
        Validate credentials against both configured accounts. Returns an
        AdminUser (with role) on success, else None. Always runs a hash compare
        to limit username-enumeration timing differences.
        """
        candidates = [
            (cls._admin_username(),
             current_app.config.get("ADMIN_PASSWORD_HASH") or "",
             ROLE_ADMIN),
            (cls._readonly_username(),
             current_app.config.get("READONLY_PASSWORD_HASH") or "",
             ROLE_READONLY),
        ]
        matched = None
        for expected_user, pw_hash, role in candidates:
            password_ok = bool(pw_hash) and check_password_hash(pw_hash, password or "")
            username_ok = bool(username) and username == expected_user
            if username_ok and password_ok:
                matched = cls(expected_user, role)
        return matched


@login_manager.user_loader
def load_user(user_id):
    return AdminUser.get(user_id)


def admin_logged_in():
    """True when the current request is from any authenticated admin user."""
    return current_user.is_authenticated


def current_role():
    """Return the role of the logged-in user, or None."""
    if current_user.is_authenticated:
        return getattr(current_user, "role", ROLE_ADMIN)
    return None


def is_readonly_user():
    return current_role() == ROLE_READONLY


# ---------------------------------------------------------------------------
# Secure Flask-Admin view mixin
# ---------------------------------------------------------------------------
class _SecureViewMixin:
    """
    Mixin that gates a Flask-Admin view behind the admin login. Applied to the
    ModelView / BaseView / AdminIndexView subclasses used for /admin.
    """
    def is_accessible(self):
        return admin_logged_in()

    def inaccessible_callback(self, name, **kwargs):
        # Send anonymous users to the login page, preserving where they were
        # headed so they return there after signing in.
        return redirect(url_for("auth_login", next=request.url))


# ---------------------------------------------------------------------------
# Login form + routes
# ---------------------------------------------------------------------------
from flask_wtf import FlaskForm  # noqa: E402
from wtforms import StringField, PasswordField, SubmitField  # noqa: E402
from wtforms.validators import DataRequired  # noqa: E402


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")


def _is_safe_next(target):
    """
    Only allow same-site relative redirects after login, to prevent an open
    redirect via the ?next= parameter.
    """
    if not target:
        return False
    # Reject absolute URLs and protocol-relative URLs ("//evil.com").
    if target.startswith("//") or "://" in target:
        return False
    return target.startswith("/")


def register_auth(app, limiter=None):
    """
    Register the login/logout routes on the app. If a Flask-Limiter instance is
    passed, the login route is rate-limited to slow brute-force attempts.
    """
    from flask import render_template_string

    login_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sign In · Holiday Hope Tree</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/style.css') }}?v=16" rel="stylesheet">
  <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='img/favicon.ico') }}">
</head>
<body>
  <header class="site-nav solid">
    <div class="nav-inner">
      <a class="brand" href="/">
        <span class="brand-mark">&#10022;</span>
        <span class="brand-name">Holiday Hope Tree</span>
      </a>
    </div>
  </header>
  <main>
    <section class="page-shell">
      <div class="wrap" style="max-width: 440px;">
        <div class="page-head">
          <span class="eyebrow">Admin</span>
          <h1 class="page-title">Sign In</h1>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        <form method="post" class="admin-form">
          {{ form.hidden_tag() }}
          <div class="form-group">
            {{ form.username.label(class="control-label") }}
            {{ form.username(class="form-control", autocomplete="username") }}
          </div>
          <div class="form-group">
            {{ form.password.label(class="control-label") }}
            {{ form.password(class="form-control", autocomplete="current-password") }}
          </div>
          <div class="submit-row">
            {{ form.submit(class="btn btn-primary") }}
          </div>
        </form>
      </div>
    </section>
  </main>
</body>
</html>
    """

    def _login_view():
        if current_user.is_authenticated:
            return redirect("/admin")
        form = LoginForm()
        if form.validate_on_submit():
            user = AdminUser.verify(form.username.data, form.password.data)
            if user is None:
                flash("Invalid username or password.", "error")
            else:
                login_user(user)
                nxt = request.args.get("next")
                return redirect(nxt if _is_safe_next(nxt) else "/admin")
        return render_template_string(login_template, form=form)

    # Apply rate limiting to the login POST if a limiter is available.
    if limiter is not None:
        _login_view = limiter.limit("10 per minute; 50 per hour")(_login_view)

    app.add_url_rule("/admin/login", endpoint="auth_login",
                     view_func=_login_view, methods=["GET", "POST"])

    def _logout_view():
        logout_user()
        flash("You have been signed out.", "success")
        return redirect("/")

    app.add_url_rule("/admin/logout", endpoint="auth_logout",
                     view_func=_logout_view, methods=["GET", "POST"])
