"""Model-level tests: lifecycle listeners, validators, hybrids, SiteSetting."""

import datetime

from sqlalchemy import text as sa_text

from webapp.models import db, Child, Gift, SiteSetting
from tests import factories as f


class TestChildLifecycle:
    def test_child_id_auto_assigned_on_insert(self, app):
        with app.app_context():
            child = f.make_child()
            assert child.child_id is not None
            # child_id is stored as a string business key.
            assert isinstance(child.child_id, str)

    def test_inserting_child_creates_gift_fulfillment_row(self, app):
        with app.app_context():
            child = f.make_child()
            # after_insert listener inserts a matching gift_fulfillment row.
            rows = db.session.execute(
                sa_text("SELECT child_id FROM gift_fulfillment WHERE child_id = :c"),
                {"c": child.child_id},
            ).fetchall()
            assert len(rows) == 1

    def test_child_ids_are_unique_across_children(self, app):
        with app.app_context():
            c1 = f.make_child()
            c2 = f.make_child()
            assert c1.child_id != c2.child_id


class TestValidators:
    def test_child_names_title_cased(self, app):
        with app.app_context():
            child = f.make_child(first_name="mary", last_name="smith")
            assert child.first_name == "Mary"
            assert child.last_name == "Smith"

    def test_sponsor_email_lowercased(self, app):
        with app.app_context():
            sponsor = f.make_sponsor(email="LOUD@EXAMPLE.COM")
            assert sponsor.email == "loud@example.com"


class TestHybrids:
    def test_has_sponsor_false_when_unsponsored(self, app):
        with app.app_context():
            child = f.make_child()
            assert child.has_sponsor is False

    def test_has_sponsor_true_when_sponsored(self, app):
        with app.app_context():
            sponsor = f.make_sponsor()
            child = f.make_child(sponsor=sponsor)
            assert child.has_sponsor is True

    def test_has_sponsor_expression_filters(self, app):
        with app.app_context():
            sponsor = f.make_sponsor()
            f.make_child()                      # unsponsored
            f.make_child(sponsor=sponsor)       # sponsored
            sponsored = db.session.query(Child).filter(Child.has_sponsor).all()
            assert len(sponsored) == 1


class TestSiteSetting:
    def test_get_returns_singleton(self, app):
        with app.app_context():
            s = SiteSetting.get()
            assert s is not None
            # Calling again returns the same row (singleton).
            assert SiteSetting.get().id == s.id

    def test_ordinal_suffixes(self, app):
        with app.app_context():
            o = SiteSetting._ordinal
            assert o(1) == "1st"
            assert o(2) == "2nd"
            assert o(3) == "3rd"
            assert o(4) == "4th"
            assert o(11) == "11th"
            assert o(12) == "12th"
            assert o(13) == "13th"
            assert o(21) == "21st"
            assert o(22) == "22nd"

    def test_signup_closed_when_flag_off(self, app):
        with app.app_context():
            s = SiteSetting.get()
            s.child_signup_open = False
            db.session.commit()
            assert s.is_child_signup_open is False

    def test_deadline_display_blank_when_unset(self, app):
        with app.app_context():
            s = SiteSetting.get()
            s.child_signup_deadline = None
            db.session.commit()
            # Null-safe: empty string, not an error.
            assert s.child_signup_deadline_display in ("", None)

    def test_deadline_display_formats_date(self, app):
        with app.app_context():
            s = SiteSetting.get()
            s.child_signup_deadline = datetime.date(2025, 11, 2)
            db.session.commit()
            # e.g. "Nov 2nd"
            assert "2nd" in s.child_signup_deadline_display
