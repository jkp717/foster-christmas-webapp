import os
from flask import Flask
from flask_admin import Admin

# Load environment variables from a .env file (project root) before any config
# is read. This makes `python cli.py run`, `flask run`, and production servers
# all pick up the .env automatically. python-dotenv is a no-op if the file is
# absent, and real (already-exported) env vars always take precedence.
try:
    from dotenv import load_dotenv
    # Look for .env in the project root (one level above this package),
    # so it loads no matter which directory the app is started from.
    _dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(_dotenv_path)
except ImportError:
    # python-dotenv not installed: fall back to real environment variables only.
    pass

from .config import (
    db_defaults, CONTACT_PHONE, CONTACT_EMAIL, CONTACT_NAME, EIN, FACEBOOK_URL, AMAZON_WISHLIST, VOLUNTEER_LINK,
    DONATE_NAV_HTML, GIFT_DROPOFF_LOCATIONS, GIFT_PICKUP_LOCATION,
    AUTHNET_API_LOGIN_ID, AUTHNET_TRANSACTION_KEY, AUTHNET_SANDBOX, AUTHNET_API_URL, AUTHNET_HOSTED_FORM_URL,
    AUTHNET_RETURN_PATH, AUTHNET_CANCEL_PATH, AUTHNET_ORDER_DESCRIPTION,
    PAYPAL_PAYMENT_URL, PAYPAL_HOSTED_BUTTON_ID, PAYPAL_BUSINESS,
    PAYPAL_CURRENCY, DONATION_PRESET_AMOUNTS
)


def setup_flask_admin(app_instance, session):
    from webapp import models as mdl
    from webapp import views as vw

    admin = Admin(
        app=app_instance,
        name='Admin',
        # template_mode='bootstrap4',
        endpoint='/admin',
        url='/admin',
        index_view=vw.AdminReportsView(name='Reports', endpoint='/admin', url='/admin')
    )

    base = Admin(
        app=app_instance,
        name='Hope for the Holidays',
        # template_mode='bootstrap4',
        url='/',
        index_view=vw.IndexView(name='Home', url='/')
    )
    base.add_view(vw.RegisterView(name='Register', endpoint='register'))  # noqa

    # admin views
    admin.add_view(vw.ParentView(mdl.Parent, session, name='Current', category='Parents'))
    admin.add_view(vw.ParentArchiveView(mdl.ParentArchive, session, name='Archive', category='Parents'))
    admin.add_view(vw.ChildView(mdl.Child, session, name='Current', category='Children'))
    admin.add_view(vw.ChildArchiveView(mdl.ChildArchive, session, name='Archive', category='Children'))
    admin.add_view(vw.GiftView(mdl.Gift, session, name='Current', category='Gifts'))
    admin.add_view(vw.GiftArchiveView(mdl.GiftArchive, session, name='Archive', category='Gifts'))
    admin.add_view(vw.SponsorView(mdl.Sponsor, session, name='Registered', category='Sponsors'))
    admin.add_view(vw.SponsorArchiveView(mdl.SponsorArchive, session, name='Registered Archive', category='Sponsors'))
    admin.add_view(vw.SponsorRequestView(mdl.SponsorRequest, session, name='Requests', category='Sponsors'))
    admin.add_view(vw.SponsorRequestArchiveView(mdl.SponsorRequestArchive, session, name='Requests Archive', category='Sponsors'))
    admin.add_view(vw.MiscView(mdl.ShoeSize, session, name='Shoe Sizes', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.ClothingSize, session, name='Clothing Sizes', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Race, session, name='Ethnicity', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Gender, session, name='Gender', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.DhsOffice, session, name='DHS Office', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Church, session, name='Church', category='Form Options'))
    admin.add_view(vw.GiftFulfillmentView(mdl.GiftFulfillment, session, name='Gift Fulfillment', category='Children'))
    admin.add_view(vw.GiftFulfillmentArchiveView(mdl.GiftFulfillmentArchive, session, name='Gift Fulfillment Archive', category='Children'))
    admin.add_view(vw.SiteSettingView(mdl.SiteSetting, session, name='Site Settings', category='Settings'))

    return app_instance


def create_app(debug=True, config_override=None):
    app = Flask(__name__)
    if not debug:
        app.config.from_object('config.ProdConfig')
        # Fail fast if a real production secret key wasn't provided, so the app
        # can never run with a missing or guessable session/CSRF signing key.
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'dev-insecure-change-me':
            raise RuntimeError(
                "SECRET_KEY is not set for production. Add a long random "
                "SECRET_KEY to your .env file (see .env.example). Generate one "
                "with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
    else:
        app.config.from_object('config.DevConfig')
    # Allow tests (or other callers) to override config AFTER the base config is
    # loaded but BEFORE extensions and the database are initialized. This is how
    # the test suite injects an in-memory SQLite URL, a known SECRET_KEY, and
    # disables CSRF / rate limiting. Has no effect in normal use.
    if config_override:
        app.config.update(config_override)

    # Behind nginx (production), the app is reached over a Unix socket and nginx
    # forwards the real scheme/client IP via X-Forwarded-Proto / X-Forwarded-For.
    # Without ProxyFix, Flask would treat every request as plain HTTP from
    # 127.0.0.1: url_for(_external=True) would emit http:// links, request.is_
    # secure would be False, and Flask-Limiter would rate-limit on the proxy's
    # IP (so per-IP limits become effectively global). Trust exactly ONE proxy
    # hop (our single nginx layer). Not applied in debug/dev, where there is no
    # proxy in front of the app.
    if not debug:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=0
        )
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from .models import db, SiteSetting

    # initialize flask addons
    db.init_app(app)

    # --- security extensions: login, CSRF, rate limiting --------------------
    from .auth import login_manager, register_auth
    login_manager.init_app(app)

    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect(app)
    app.extensions['csrf'] = csrf

    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[],  # no global limit; we apply limits per-route
        storage_uri="memory://",
    )
    app.extensions['limiter'] = limiter

    # Register login/logout routes (login route is rate-limited).
    register_auth(app, limiter=limiter)

    # first time database setup
    with app.app_context():
        # Ensure the directory that will hold the SQLite file exists. This
        # matters when DATABASE_PATH points outside the repo (production), where
        # the target folder (e.g. /var/lib/holidayhopetree) must be present.
        db_path = app.config.get('DATABASE_PATH')
        if db_path:
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        # Create the database only if it doesn't already exist, so an existing
        # production database is never overwritten or re-seeded on deploy.
        if db_path and not os.path.exists(db_path):
            db.create_all()
            # create a table name to class mapper
            tbl_to_cls = {}
            for mapper in db.Model.registry.mappers:
                cls = mapper.class_
                classname = cls.__name__
                if not classname.startswith('_'):
                    tbl_to_cls[cls.__tablename__] = cls
            # create default models
            for tbl, col in db_defaults.items():
                for col_name, itr in col.items():
                    for val in itr:
                        model = tbl_to_cls[tbl]()
                        setattr(model, col_name, val)
                        db.session.add(model)
                    db.session.commit()

        # Ensure newly added tables exist even on a pre-existing database.
        # create_all() only creates missing tables; it never alters or drops
        # existing ones, so running it every startup is safe and idempotent.
        # Column/type changes to EXISTING tables are handled out-of-band by the
        # `python cli.py db-update-schema` command (Alembic), run on deploy --
        # not on every startup.
        db.create_all()

        # Ensure the single SiteSetting row exists with safe, neutral defaults
        # (signups open, no deadline, no pickup window). The admin sets the real
        # deadline and pickup window in the "Site Settings" screen. We never
        # seed dates from code, so a new season never starts with stale values.
        if db.session.query(SiteSetting).first() is None:
            db.session.add(SiteSetting(child_signup_open=True,
                                       amazon_wishlist=AMAZON_WISHLIST))
            db.session.commit()

    app = setup_flask_admin(app, db.session)

    # Rate-limit the public, unauthenticated form endpoints to curb spam and
    # automated abuse. Limits are applied by registered endpoint name on the
    # view functions Flask-Admin created.
    _public_form_endpoints = [
        'register.parent', 'register.child',
        'register.sponsor', 'register.sponsor_request',
        'admin.donate_authnet',  # IndexView donate POST (base Admin index endpoint)
    ]
    for _ep in _public_form_endpoints:
        _vf = app.view_functions.get(_ep)
        if _vf is not None:
            app.view_functions[_ep] = limiter.limit(
                "8 per minute; 40 per hour"
            )(_vf)

    # define contact for use in jinja templates
    app.config['CONTACT_PHONE'] = CONTACT_PHONE
    app.config['CONTACT_EMAIL'] = CONTACT_EMAIL
    app.config['CONTACT_NAME'] = CONTACT_NAME
    app.config['EIN'] = EIN

    # define external urls for use in jinja templates
    app.config['FACEBOOK_URL'] = FACEBOOK_URL
    app.config['AMAZON_WISHLIST'] = AMAZON_WISHLIST
    app.config['VOLUNTEER_LINK'] = VOLUNTEER_LINK
    app.config['DONATE_NAV_HTML'] = DONATE_NAV_HTML

    # donation / payment settings
    app.config['AUTHNET_API_LOGIN_ID'] = AUTHNET_API_LOGIN_ID
    app.config['AUTHNET_TRANSACTION_KEY'] = AUTHNET_TRANSACTION_KEY
    app.config['AUTHNET_SANDBOX'] = AUTHNET_SANDBOX
    app.config['AUTHNET_API_URL'] = AUTHNET_API_URL
    app.config['AUTHNET_HOSTED_FORM_URL'] = AUTHNET_HOSTED_FORM_URL
    app.config['AUTHNET_RETURN_PATH'] = AUTHNET_RETURN_PATH
    app.config['AUTHNET_CANCEL_PATH'] = AUTHNET_CANCEL_PATH
    app.config['AUTHNET_ORDER_DESCRIPTION'] = AUTHNET_ORDER_DESCRIPTION
    app.config['PAYPAL_PAYMENT_URL'] = PAYPAL_PAYMENT_URL
    app.config['PAYPAL_HOSTED_BUTTON_ID'] = PAYPAL_HOSTED_BUTTON_ID
    app.config['PAYPAL_BUSINESS'] = PAYPAL_BUSINESS
    app.config['PAYPAL_CURRENCY'] = PAYPAL_CURRENCY
    app.config['DONATION_PRESET_AMOUNTS'] = DONATION_PRESET_AMOUNTS

    app.config['GIFT_DROPOFF_LOCATIONS'] = GIFT_DROPOFF_LOCATIONS
    app.config['GIFT_PICKUP_LOCATION'] = GIFT_PICKUP_LOCATION

    @app.context_processor
    def inject_site_settings():
        # Make the admin-managed gift pickup and signup deadline available to
        # every template, formatted like the old config strings. Also expose the
        # admin-editable Amazon wish list link (falling back to the config
        # constant if it hasn't been set in the database yet).
        try:
            setting = SiteSetting.get()
            return {
                'gift_pickup_datetime': setting.gift_pickup_display,
                'child_signup_deadline': setting.child_signup_deadline_display,
                'amazon_wishlist': setting.amazon_wishlist or AMAZON_WISHLIST,
            }
        except Exception:
            # If the settings row/table isn't available yet, fail soft.
            return {
                'gift_pickup_datetime': '',
                'child_signup_deadline': '',
                'amazon_wishlist': AMAZON_WISHLIST,
            }

    @app.shell_context_processor
    def shell_context():
        return {'app': app, 'db': db}

    return app