"""Donate page payment options, including the admin-managed Cash App $Cashtag."""

from webapp.models import db, SiteSetting


def _set_cashtag(app, tag):
    with app.app_context():
        setting = SiteSetting.get()
        setting.cashapp_cashtag = tag
        db.session.commit()


def _save_settings(client, app, login_admin, cashtag):
    login_admin()
    with app.app_context():
        sid = SiteSetting.get().id
    data = {"child_signup_open": "y", "cashapp_cashtag": cashtag}
    return client.post(f"/admin/sitesetting/edit/?id={sid}", data=data,
                       follow_redirects=True)


class TestDonatePage:
    def test_cashapp_hidden_without_cashtag(self, app, client):
        _set_cashtag(app, None)
        resp = client.get("/donate")
        assert resp.status_code == 200
        assert b'value="paypal"' in resp.data
        assert b'value="cashapp"' not in resp.data

    def test_cashapp_shown_with_cashtag(self, app, client):
        _set_cashtag(app, "HolidayHopeTree")
        resp = client.get("/donate")
        assert resp.status_code == 200
        assert b'value="cashapp"' in resp.data
        assert b"$HolidayHopeTree" in resp.data
        assert b'var CASHAPP_TAG = "HolidayHopeTree";' in resp.data


class TestCashtagSetting:
    def test_leading_dollar_is_stripped(self, app, client, login_admin):
        resp = _save_settings(client, app, login_admin, " $HolidayHopeTree ")
        assert resp.status_code == 200
        with app.app_context():
            assert SiteSetting.get().cashapp_cashtag == "HolidayHopeTree"

    def test_blank_clears_cashtag(self, app, client, login_admin):
        _set_cashtag(app, "HolidayHopeTree")
        _save_settings(client, app, login_admin, "")
        with app.app_context():
            assert SiteSetting.get().cashapp_cashtag is None

    def test_invalid_cashtag_is_rejected(self, app, client, login_admin):
        _set_cashtag(app, None)
        resp = _save_settings(client, app, login_admin, "bad tag!")
        assert b"may only contain letters" in resp.data
        with app.app_context():
            assert SiteSetting.get().cashapp_cashtag is None


ZEFFY = "https://www.zeffy.com/en-US/donation-form/holiday-hope-tree"


def _set_zeffy(app, url):
    with app.app_context():
        setting = SiteSetting.get()
        setting.zeffy_url = url
        db.session.commit()


class TestZeffyOption:
    def test_zeffy_hidden_without_link(self, app, client):
        _set_zeffy(app, None)
        resp = client.get("/donate")
        assert b'value="zeffy"' not in resp.data

    def test_zeffy_shown_with_link(self, app, client):
        _set_zeffy(app, ZEFFY)
        resp = client.get("/donate")
        assert b'value="zeffy"' in resp.data
        assert f'var ZEFFY_URL = "{ZEFFY}";'.encode() in resp.data

    def test_admin_saves_zeffy_link(self, app, client, login_admin):
        login_admin()
        with app.app_context():
            sid = SiteSetting.get().id
        client.post(f"/admin/sitesetting/edit/?id={sid}",
                    data={"child_signup_open": "y", "zeffy_url": f"  {ZEFFY} "},
                    follow_redirects=True)
        with app.app_context():
            assert SiteSetting.get().zeffy_url == ZEFFY

    def test_admin_rejects_non_zeffy_link(self, app, client, login_admin):
        _set_zeffy(app, None)
        login_admin()
        with app.app_context():
            sid = SiteSetting.get().id
        resp = client.post(f"/admin/sitesetting/edit/?id={sid}",
                           data={"child_signup_open": "y",
                                 "zeffy_url": "https://evil.example.com/zeffy.com"},
                           follow_redirects=True)
        assert b"must be an https://www.zeffy.com" in resp.data
        with app.app_context():
            assert SiteSetting.get().zeffy_url is None
