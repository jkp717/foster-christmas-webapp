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


class TestEmailListDownloads:
    """Reports page: comma-separated email lists for email blasts."""

    def test_reports_page_links_to_email_lists(self, client, login_admin):
        login_admin()
        html = client.get("/admin/").get_data(as_text=True)
        assert "/admin/download/emails/sponsors" in html
        assert "/admin/download/emails/parents" in html

    @pytest.mark.parametrize("list_name,factory,filename", [
        ("sponsors", "make_sponsor", "sponsor-emails.txt"),
        ("parents", "make_parent", "foster-parent-emails.txt"),
    ])
    def test_email_list_is_deduped_comma_separated(self, app, client, login_admin, list_name, factory, filename):
        from tests import factories as fac
        make = getattr(fac, factory)
        with app.app_context():
            make(email="b@example.com")
            make(email="a@example.com")
            make(email="B@example.com")  # same address, different case
        login_admin()
        resp = client.get(f"/admin/download/emails/{list_name}")
        assert resp.status_code == 200
        assert filename in resp.headers["Content-Disposition"]
        emails = [e.strip().lower() for e in resp.get_data(as_text=True).split(",")]
        assert emails == ["a@example.com", "b@example.com"]

    def test_unknown_email_list_is_404(self, client, login_admin):
        login_admin()
        assert client.get("/admin/download/emails/nope").status_code == 404

    def test_email_list_requires_login(self, client):
        resp = client.get("/admin/download/emails/sponsors")
        assert resp.status_code in (302, 401, 403)
