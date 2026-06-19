"""
Admin view tests: list pages load for authenticated users (live + archive),
and archive list pages render without write affordances.

These are smoke-level HTTP tests -- they catch view wiring/regressions (a
template break, a bad column, a broken relationship) without asserting on exact
markup.
"""

import pytest

# (url path, needs data) for the live + archive list views.
LIVE_VIEW_PATHS = [
    "/admin/child/",
    "/admin/parent/",
    "/admin/gift/",
    "/admin/sponsor/",
    "/admin/sponsorrequest/",
    "/admin/giftfulfillment/",
]

ARCHIVE_VIEW_PATHS = [
    "/admin/childarchive/",
    "/admin/parentarchive/",
    "/admin/giftarchive/",
    "/admin/sponsorarchive/",
    "/admin/sponsorrequestarchive/",
    "/admin/giftfulfillmentarchive/",
]


class TestAdminListViewsLoad:
    @pytest.mark.parametrize("path", LIVE_VIEW_PATHS)
    def test_live_view_loads_for_admin(self, client, login_admin, path):
        login_admin()
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} did not load (got {resp.status_code})"

    @pytest.mark.parametrize("path", ARCHIVE_VIEW_PATHS)
    def test_archive_view_loads_for_admin(self, client, login_admin, path):
        login_admin()
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} did not load (got {resp.status_code})"

    @pytest.mark.parametrize("path", ARCHIVE_VIEW_PATHS)
    def test_archive_view_loads_for_readonly(self, client, login_readonly, path):
        login_readonly()
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} did not load (got {resp.status_code})"


class TestAdminViewsWithData:
    def test_child_list_shows_seeded_child(self, app, client, login_admin):
        from tests import factories as fac
        with app.app_context():
            fac.make_child(first_name="Visible", last_name="Kid")
        login_admin()
        resp = client.get("/admin/child/")
        assert resp.status_code == 200
        assert b"Visible" in resp.data

    def test_sponsor_archive_loads_with_archived_rows(self, app, client, login_admin):
        """Render the sponsor archive after inserting an archived sponsor with
        a season year, exercising the children-count formatter path."""
        from webapp.models import db, SponsorArchive
        with app.app_context():
            arc = SponsorArchive(
                first_name="Past", last_name="Sponsor",
                phone="+15015550000", email="past@example.com",
                archive_year=2024,
            )
            db.session.add(arc)
            db.session.commit()
        login_admin()
        resp = client.get("/admin/sponsorarchive/")
        assert resp.status_code == 200
        assert b"Past" in resp.data
