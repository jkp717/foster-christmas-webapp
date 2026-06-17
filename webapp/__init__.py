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
    db_defaults, CONTACT_PHONE, CONTACT_EMAIL, CONTACT_NAME, FACEBOOK_URL, AMAZON_WISHLIST, VOLUNTEER_LINK,
    DONATE_NAV_HTML, GIFT_DROPOFF_LOCATIONS, GIFT_PICKUP_DATETIME, GIFT_PICKUP_LOCATION, CHILD_SIGNUP_DEADLINE,
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
    admin.add_view(vw.SponsorRequestView(mdl.SponsorRequest, session, name='Requests', category='Sponsors'))
    admin.add_view(vw.MiscView(mdl.ShoeSize, session, name='Shoe Sizes', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.ClothingSize, session, name='Clothing Sizes', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Race, session, name='Ethnicity', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Gender, session, name='Gender', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.DhsOffice, session, name='DHS Office', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Church, session, name='Church', category='Form Options'))
    admin.add_view(vw.GiftFulfillmentView(mdl.GiftFulfillment, session, name='Gift Fulfillment', category='Children'))

    return app_instance


def create_app(debug=True):
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
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from .models import db

    # initialize flask addons
    db.init_app(app)

    # first time database setup
    with app.app_context():
        # Create the database if it doesn't already exist
        if not os.path.exists(app.config['SQLITE_DATABASE_PATH']):
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

    app = setup_flask_admin(app, db.session)

    # define contact for use in jinja templates
    app.config['CONTACT_PHONE'] = CONTACT_PHONE
    app.config['CONTACT_EMAIL'] = CONTACT_EMAIL
    app.config['CONTACT_NAME'] = CONTACT_NAME

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
    app.config['GIFT_PICKUP_DATETIME'] = GIFT_PICKUP_DATETIME
    app.config['CHILD_SIGNUP_DEADLINE'] = CHILD_SIGNUP_DEADLINE

    @app.shell_context_processor
    def shell_context():
        return {'app': app, 'db': db}

    return app