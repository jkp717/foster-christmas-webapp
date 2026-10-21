"""
Security tests: role-based write permissions, archive read-only enforcement,
CSRF protection, and the child-registration IDOR ownership check.

These focus on observable security contracts rather than Flask-Admin form
internals, so they stay robust as the admin UI evolves.
"""

import pytest

from webapp import create_app
from webapp.models import db
from webapp import views as vw
from webapp.auth import ROLE_ADMIN, ROLE_READONLY
from tests.conftest import _test_config, TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD


# --------------------------------------------------------------------------
# Role-based write permissions.
# can_create / can_delete are properties that depend on the *current user's*
# role via is_readonly_user(); we exercise them under a faked login context.
# --------------------------------------------------------------------------
class _FakeUser:
    def __init__(self, role):
        self.role = role
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return self.role


def _permission_under_role(app, role, model_cls, view_cls):
    """Instantiate a view and read can_create/can_delete as the given role."""
    from flask_login import login_user
    with app.test_request_context():
        login_user(_FakeUser(role))
        view = view_cls(model_cls, db.session)
        return bool(view.can_create), bool(view.can_delete), bool(view.can_edit)


class TestRolePermissions:
    def test_admin_can_create_and_delete_live_view(self, app):
        with app.app_context():
            from webapp.models import Child
            create, delete, edit = _permission_under_role(
                app, ROLE_ADMIN, Child, vw.ChildView
            )
            assert create is True
            assert delete is True
            assert edit is True

    def test_readonly_cannot_create_or_delete_live_view(self, app):
        with app.app_context():
            from webapp.models import Child
            create, delete, edit = _permission_under_role(
                app, ROLE_READONLY, Child, vw.ChildView
            )
            assert create is False
            assert delete is False
            # read-only users keep edit access (limited to comment fields by
            # update_model), so can_edit stays True.
            assert edit is True


# --------------------------------------------------------------------------
# Archive views are read-only for EVERYONE, including full admins.
# --------------------------------------------------------------------------
ARCHIVE_VIEWS = [
    ("ChildArchive", "ChildArchiveView"),
    ("ParentArchive", "ParentArchiveView"),
    ("GiftArchive", "GiftArchiveView"),
    ("SponsorArchive", "SponsorArchiveView"),
    ("SponsorRequestArchive", "SponsorRequestArchiveView"),
    ("GiftFulfillmentArchive", "GiftFulfillmentArchiveView"),
]


class TestArchiveReadOnly:
    @pytest.mark.parametrize("model_name,view_name", ARCHIVE_VIEWS)
    def test_archive_view_locked_even_for_admin(self, app, model_name, view_name):
        import webapp.models as mdl
        with app.app_context():
            model_cls = getattr(mdl, model_name)
            view_cls = getattr(vw, view_name)
            create, delete, edit = _permission_under_role(
                app, ROLE_ADMIN, model_cls, view_cls
            )
            assert create is False, f"{view_name} create should be locked"
            assert delete is False, f"{view_name} delete should be locked"
            assert edit is False, f"{view_name} edit should be locked"

    @pytest.mark.parametrize("model_name,view_name", ARCHIVE_VIEWS)
    def test_archive_view_blocks_bulk_actions(self, app, model_name, view_name):
        import webapp.models as mdl
        with app.app_context():
            model_cls = getattr(mdl, model_name)
            view_cls = getattr(vw, view_name)
            view = view_cls(model_cls, db.session)
            assert view.is_action_allowed("delete") is False


# --------------------------------------------------------------------------
# CSRF protection: with CSRF enabled, an admin POST without a token is rejected.
# We build a dedicated app with WTF_CSRF_ENABLED=True (the default test app
# disables it so other tests can POST freely).
# --------------------------------------------------------------------------
class TestCSRF:
    def test_login_post_without_token_blocked_when_csrf_enabled(self, tmp_path):
        db_path = str(tmp_path / "csrf_test.db")
        overrides = _test_config(db_path)
        overrides["WTF_CSRF_ENABLED"] = True
        application = create_app(debug=True, config_override=overrides)
        with application.app_context():
            db.create_all()
        client = application.test_client()
        resp = client.post(
            "/admin/login",
            data={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
            follow_redirects=False,
        )
        # CSRF failure is a 400 (and definitely not a successful redirect to admin)
        assert resp.status_code == 400

    def test_rules_based_admin_forms_render_csrf_token(self, app):
        # Flask-Admin drops fields missing from form_rules; the CSRF token must
        # survive or saving the child edit form fails with "token is missing".
        import re
        from tests import factories as fac
        app.config["WTF_CSRF_ENABLED"] = True
        with app.app_context():
            child_id = fac.make_child().id
        client = app.test_client()
        login_page = client.get("/admin/login").text
        token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', login_page).group(1)
        client.post("/admin/login", data={
            "username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD, "csrf_token": token,
        })
        for url in (f"/admin/child/edit/?id={child_id}", "/admin/child/new/"):
            page = client.get(url).text
            assert 'id="csrf_token"' in page, url


# --------------------------------------------------------------------------
# IDOR: the child-registration page must not let one parent's URL operate on
# another parent's child record.
# --------------------------------------------------------------------------
class TestChildIDOR:
    def test_child_route_rejects_mismatched_parent(self, app, client):
        from tests import factories as fac
        with app.app_context():
            parent_a = fac.make_parent(email="a@example.com")
            parent_b = fac.make_parent(email="b@example.com")
            child_of_b = fac.make_child(parent=parent_b)
            a_id, b_child_id = parent_a.id, child_of_b.id

        # Attempt to delete parent B's child while acting under parent A's URL.
        # The route reads the child id from the query string (request.args).
        resp = client.post(
            f"/register/{a_id}/child?id={b_child_id}",
            data={"delete": "1"},
            follow_redirects=False,
        )
        # The ownership check redirects rather than acting on the foreign record.
        assert resp.status_code in (301, 302)

        # And the child still exists (was not deleted).
        with app.app_context():
            from webapp.models import Child
            assert db.session.get(Child, b_child_id) is not None
