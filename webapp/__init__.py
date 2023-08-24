import os
from flask import Flask
from flask_admin import Admin

from .config import db_defaults


def setup_flask_admin(app_instance, session):
    from webapp import models as mdl
    from webapp import views as vw

    admin = Admin(
        app=app_instance,
        name='Admin',
        template_mode='bootstrap4',
        endpoint='admin'
    )

    base = Admin(
        app=app_instance,
        name='Hope for the Holidays',
        template_mode='bootstrap4',
        url='/',
        index_view=vw.IndexView(name='Home', endpoint='/')   # noqa
    )
    base.add_view(vw.RegisterView(name='Register', endpoint='register'))  # noqa

    # admin views
    admin.add_view(vw.ParentView(mdl.Parent, session, name='Parents'))
    admin.add_view(vw.ChildView(mdl.Child, session, name='Children'))
    admin.add_view(vw.GiftView(mdl.Gift, session, name='Gifts'))
    admin.add_view(vw.MiscView(mdl.ShoeSize, session, name='Shoe Sizes', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.ClothingSize, session, name='Clothing Sizes', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Race, session, name='Ethnicity', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.Gender, session, name='Gender', category='Form Options'))
    admin.add_view(vw.MiscView(mdl.DhsOffice, session, name='DHS Office', category='Form Options'))

    return app_instance


def create_app(debug=True):
    app = Flask(__name__)
    if not debug:
        app.config.from_object('config.ProdConfig')
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

    return app