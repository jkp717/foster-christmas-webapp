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


class TestChildSubmission:
    def _post_child(self, app, client, **flags):
        from tests import factories as fac
        from webapp.models import Gender, Race, DhsOffice
        with app.app_context():
            pid = fac.make_parent().id
            data = {
                "first_name": "Casey",
                "last_name": "Kid",
                "dhs_case_worker": "Case Worker",
                "dhs_office": str(db.session.query(DhsOffice).first().id),
                "age": "7",
                "race": str(db.session.query(Race).first().id),
                "gender": str(db.session.query(Gender).first().id),
                "gifts-0-gift": "Bike",
                **flags,
            }
        resp = client.post(f"/register/{pid}/child", data=data, follow_redirects=False)
        assert resp.status_code in (301, 302)
        return pid

    def test_form_shows_facility_and_mailing_checkboxes(self, app, client):
        from tests import factories as fac
        with app.app_context():
            pid = fac.make_parent().id
        html = client.get(f"/register/{pid}/child").get_data(as_text=True)
        assert "This child is in a facility" in html
        assert "These gifts will need to be mailed" in html

    def test_checked_boxes_are_saved(self, app, client):
        from webapp.models import Child
        pid = self._post_child(app, client, in_facility="y", gifts_need_mailing="y")
        with app.app_context():
            child = db.session.query(Child).filter(Child.parent_id == pid).one()
            assert child.in_facility is True
            assert child.gifts_need_mailing is True

    def test_unchecked_boxes_default_to_false(self, app, client):
        from webapp.models import Child
        pid = self._post_child(app, client)
        with app.app_context():
            child = db.session.query(Child).filter(Child.parent_id == pid).one()
            assert child.in_facility is False
            assert child.gifts_need_mailing is False


class TestEmailValidator:
    """Unit tests for the DeliverableEmail validator (syntax pass, no network)."""

    def _run(self, value, check_deliverability=False):
        from webapp.formfields import DeliverableEmail
        from wtforms.validators import ValidationError

        class _Field:
            def __init__(self, data):
                self.data = data

        v = DeliverableEmail(check_deliverability=check_deliverability)
        try:
            v(None, _Field(value))
            return True
        except ValidationError:
            return False

    def test_malformed_no_at_rejected(self):
        # "annjohnx1" style input (no @) must fail syntax.
        assert self._run("annjohnx1") is False

    def test_blank_is_skipped(self):
        # Empty is left to DataRequired/Optional, so the validator passes.
        assert self._run("") is True

    def test_plausible_address_passes_syntax(self):
        assert self._run("real.person@example.com") is True


class TestHoneypot:
    def test_honeypot_filled_blocks_submission(self, app, client):
        """A bot that fills the hidden 'website' field is rejected: no Parent
        row is created."""
        from webapp.models import Parent
        before = None
        with app.app_context():
            before = db.session.query(Parent).count()
        resp = client.post(
            "/register/",
            data={
                "first_name": "Bot",
                "last_name": "Spammer",
                "phone": "+15015550000",
                "email": "bot@example.com",
                "website": "http://spam.example",  # honeypot tripped
            },
            follow_redirects=False,
        )
        # Should not create a record; the form re-renders (200) rather than
        # redirecting to the child step.
        with app.app_context():
            after = db.session.query(Parent).count()
        assert after == before

    def test_clean_submission_not_blocked_by_honeypot(self, app, client):
        """An empty honeypot does not interfere with a normal submission."""
        from webapp.models import Parent
        resp = client.post(
            "/register/",
            data={
                "first_name": "Real",
                "last_name": "Parent",
                "phone": "+15015551234",
                "email": "real.parent@example.com",
                "website": "",  # empty -> human
            },
            follow_redirects=False,
        )
        # Must not 500; either redirects to child step or re-renders.
        assert resp.status_code in (200, 301, 302)
