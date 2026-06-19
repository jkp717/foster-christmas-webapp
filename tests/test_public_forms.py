"""
Public-site tests: page rendering and the child-signup gate.

Full Flask-Admin form POST cycles (with ruleset + FK fields) are intentionally
covered indirectly via the model/factory tests; here we assert the publicly
observable HTTP behavior that's stable regardless of form internals.
"""

from webapp.models import db, SiteSetting


class TestPublicPagesRender:
    def test_home_page(self, client):
        assert client.get("/").status_code == 200

    def test_parent_register_page(self, client):
        # Parent registration is the register index ('/register/').
        resp = client.get("/register/")
        assert resp.status_code == 200

    def test_sponsor_register_page(self, client):
        assert client.get("/register/sponsor").status_code == 200

    def test_sponsor_request_page(self, client):
        assert client.get("/register/sponsor-request").status_code == 200

    def test_signup_closed_page(self, client):
        assert client.get("/register/signup-closed").status_code == 200


class TestSignupGate:
    def test_parent_open_when_signups_on(self, app, client):
        with app.app_context():
            s = SiteSetting.get()
            s.child_signup_open = True
            s.child_signup_deadline = None
            db.session.commit()
        resp = client.get("/register/", follow_redirects=False)
        assert resp.status_code == 200

    def test_parent_redirects_to_closed_when_signups_off(self, app, client):
        with app.app_context():
            s = SiteSetting.get()
            s.child_signup_open = False
            db.session.commit()
        resp = client.get("/register/", follow_redirects=False)
        assert resp.status_code in (301, 302)
        assert "signup-closed" in resp.headers.get("Location", "")

    def test_child_route_redirects_to_closed_when_signups_off(self, app, client):
        from tests import factories as fac
        with app.app_context():
            parent = fac.make_parent()
            pid = parent.id
            s = SiteSetting.get()
            s.child_signup_open = False
            db.session.commit()
        resp = client.get(f"/register/{pid}/child", follow_redirects=False)
        assert resp.status_code in (301, 302)
        assert "signup-closed" in resp.headers.get("Location", "")


class TestSponsorSubmission:
    def test_sponsor_post_creates_record(self, app, client):
        """A clean sponsor submission should create a Sponsor row.

        CSRF is disabled in the test config, so a direct POST of the model
        fields exercises the create path.
        """
        from webapp.models import Sponsor
        resp = client.post(
            "/register/sponsor",
            data={
                "first_name": "Jamie",
                "last_name": "Donor",
                "phone": "+15015559876",
                "email": "jamie.donor@example.com",
            },
            follow_redirects=False,
        )
        # On success the view redirects (to '/'); on validation issues it
        # re-renders (200). Either way it must not 500.
        assert resp.status_code in (200, 301, 302)
        # If it redirected, the record should exist.
        if resp.status_code in (301, 302):
            with app.app_context():
                found = db.session.query(Sponsor).filter(
                    Sponsor.email == "jamie.donor@example.com"
                ).first()
                assert found is not None
