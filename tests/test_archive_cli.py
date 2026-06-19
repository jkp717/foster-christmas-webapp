"""
Archive-season tests: the core run_archive_season() routine.

Verifies the high-value, error-prone behaviors:
  * live data is copied into the archive tables and then wiped
  * parent/sponsor foreign keys are remapped to the NEW archive ids
  * child_id + archive_year compose correctly and gifts follow the child
  * reference tables and site_setting are left untouched
"""

from cli import run_archive_season
from webapp.models import (
    db, Child, Parent, Sponsor, Gift, GiftFulfillment, SponsorRequest,
    ChildArchive, ParentArchive, SponsorArchive, GiftArchive,
    GiftFulfillmentArchive, SponsorRequestArchive, Gender,
)
from tests import factories as f


def _build_season(app):
    """Create a small but representative live season inside app context."""
    with app.app_context():
        sponsor = f.make_sponsor(email="sp@example.com")
        parent = f.make_parent(email="par@example.com")
        child = f.make_child(parent=parent, sponsor=sponsor,
                             first_name="Archie", last_name="Veedchild")
        f.make_gift(child, gift="Skateboard")
        f.make_sponsor_request(email="req@example.com")
        return {
            "child_id": child.child_id,
            "sponsor_email": sponsor.email,
            "parent_email": parent.email,
        }


class TestArchiveSeason:
    def test_archive_copies_then_wipes_live(self, app):
        info = _build_season(app)
        with app.app_context():
            archived = run_archive_season(skip_confirm=True, echo=lambda *a, **k: None)
            assert archived > 0

            # Live tables emptied.
            assert Child.query.count() == 0
            assert Parent.query.count() == 0
            assert Sponsor.query.count() == 0
            assert Gift.query.count() == 0
            assert GiftFulfillment.query.count() == 0
            assert SponsorRequest.query.count() == 0

            # Archive tables populated.
            assert ChildArchive.query.count() == 1
            assert ParentArchive.query.count() == 1
            assert SponsorArchive.query.count() == 1
            assert GiftArchive.query.count() == 1
            assert SponsorRequestArchive.query.count() == 1
            # gift_fulfillment auto-created on child insert -> archived too.
            assert GiftFulfillmentArchive.query.count() == 1

    def test_child_fks_remapped_to_archive_ids(self, app):
        _build_season(app)
        with app.app_context():
            run_archive_season(skip_confirm=True, echo=lambda *a, **k: None)
            child_arc = ChildArchive.query.one()
            parent_arc = ParentArchive.query.one()
            sponsor_arc = SponsorArchive.query.one()
            # The archived child must point at the ARCHIVE parent/sponsor ids.
            assert child_arc.parent_id == parent_arc.id
            assert child_arc.sponsor_id == sponsor_arc.id

    def test_gift_follows_child_via_relationship(self, app):
        info = _build_season(app)
        with app.app_context():
            run_archive_season(skip_confirm=True, echo=lambda *a, **k: None)
            child_arc = ChildArchive.query.one()
            # The composite (child_id, archive_year) relationship resolves.
            assert len(child_arc.gifts) == 1
            assert child_arc.gifts[0].gift == "Skateboard"
            assert child_arc.child_id == info["child_id"]
            # archive_year stamped consistently across child and gift.
            assert child_arc.gifts[0].archive_year == child_arc.archive_year

    def test_reference_and_settings_untouched(self, app):
        _build_season(app)
        with app.app_context():
            genders_before = Gender.query.count()
            from webapp.models import SiteSetting
            assert SiteSetting.get() is not None
            run_archive_season(skip_confirm=True, echo=lambda *a, **k: None)
            # Reference data still present, settings row still present.
            assert Gender.query.count() == genders_before
            assert SiteSetting.get() is not None

    def test_archive_empty_season_is_noop(self, app):
        with app.app_context():
            archived = run_archive_season(skip_confirm=True, echo=lambda *a, **k: None)
            assert archived == 0
            assert ChildArchive.query.count() == 0


class TestMultiSeasonComposite:
    def test_same_child_id_coexists_across_two_seasons(self, app):
        import datetime as _dt
        # Season 1 (stamped 2024 via create_date).
        with app.app_context():
            parent = f.make_parent(email="p1@example.com")
            child = f.make_child(parent=parent, first_name="Yearone", last_name="Kid")
            child.create_date = _dt.datetime(2024, 11, 1, 10, 0, 0)
            db.session.commit()
            cid1 = child.child_id
            run_archive_season(skip_confirm=True, echo=lambda *a, **k: None)

        # Season 2 (stamped 2025). After the wipe, child_id assignment restarts,
        # so this child very likely reuses the same child_id as season 1.
        with app.app_context():
            parent = f.make_parent(email="p2@example.com")
            child = f.make_child(parent=parent, first_name="Yeartwo", last_name="Kid")
            child.create_date = _dt.datetime(2025, 11, 1, 10, 0, 0)
            db.session.commit()
            cid2 = child.child_id
            run_archive_season(skip_confirm=True, echo=lambda *a, **k: None)

        with app.app_context():
            # Both seasons coexist: the composite (child_id, archive_year) key
            # lets the same child_id repeat under a different season year.
            assert ChildArchive.query.count() == 2
            years = sorted({c.archive_year for c in ChildArchive.query.all()})
            assert years == [2024, 2025]
            # If child_id repeated, that's exactly the case the composite key
            # is designed to allow.
            if cid1 == cid2:
                same_id_rows = ChildArchive.query.filter(
                    ChildArchive.child_id == cid1
                ).count()
                assert same_id_rows == 2
