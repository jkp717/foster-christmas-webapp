"""Authentication tests: credential verification, roles, login/logout, gating."""

from webapp.auth import AdminUser, ROLE_ADMIN, ROLE_READONLY
from tests.conftest import (
    TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD,
    TEST_READONLY_USERNAME, TEST_READONLY_PASSWORD,
)


class TestVerify:
    def test_admin_credentials_verify_with_admin_role(self, app):
        with app.app_context():
            user = AdminUser.verify(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
            assert user is not None
            assert user.role == ROLE_ADMIN

    def test_readonly_credentials_verify_with_readonly_role(self, app):
        with app.app_context():
            user = AdminUser.verify(TEST_READONLY_USERNAME, TEST_READONLY_PASSWORD)
            assert user is not None
            assert user.role == ROLE_READONLY

    def test_wrong_password_fails(self, app):
        with app.app_context():
            assert AdminUser.verify(TEST_ADMIN_USERNAME, "nope") is None

    def test_unknown_user_fails(self, app):
        with app.app_context():
            assert AdminUser.verify("ghost", TEST_ADMIN_PASSWORD) is None

    def test_empty_credentials_fail(self, app):
        with app.app_context():
            assert AdminUser.verify("", "") is None
            assert AdminUser.verify(None, None) is None


class TestLoginFlow:
    def test_login_page_renders(self, client):
        resp = client.get("/admin/login")
        assert resp.status_code == 200

    def test_admin_login_succeeds(self, client, login_admin):
        resp = login_admin()
        assert resp.status_code == 200

    def test_bad_login_does_not_authenticate(self, client):
        resp = client.post(
            "/admin/login",
            data={"username": TEST_ADMIN_USERNAME, "password": "wrong"},
            follow_redirects=True,
        )
        # Still on a page (login), but the protected area stays blocked.
        assert resp.status_code in (200, 401)
        probe = client.get("/admin/child/", follow_redirects=False)
        assert probe.status_code in (301, 302)  # redirected to login

    def test_logout_clears_session(self, client, login_admin, logout):
        login_admin()
        # authenticated: should reach the admin list (200)
        assert client.get("/admin/child/").status_code == 200
        logout()
        # after logout: protected view redirects to login again
        resp = client.get("/admin/child/", follow_redirects=False)
        assert resp.status_code in (301, 302)


class TestAccessGating:
    def test_anonymous_redirected_from_admin_view(self, client):
        resp = client.get("/admin/child/", follow_redirects=False)
        assert resp.status_code in (301, 302)
        assert "/admin/login" in resp.headers.get("Location", "")

    def test_admin_can_access_admin_view(self, client, login_admin):
        login_admin()
        assert client.get("/admin/child/").status_code == 200

    def test_readonly_can_access_admin_view(self, client, login_readonly):
        login_readonly()
        assert client.get("/admin/child/").status_code == 200
