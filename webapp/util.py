from flask import current_app, has_request_context
from flask_admin.contrib.sqla.filters import BaseSQLAFilter

from .models import db, DhsOffice, ShoeSize, ClothingSize, FavColor, Gender, Race


def title_case_formatter(view, context, model, name):
    """
    `view` is current administrative view
    `context` is instance of jinja2.runtime.Context
    `model` is model instance
    `name` is property name
    """
    return getattr(model, name, '').title()


def get_dhs_office_options():
    if not has_request_context():
        return ()
    return tuple([(o.office, o.office) for o in db.session.query(DhsOffice).all()])


def get_shoe_size_options():
    if not has_request_context():
        return ()
    return tuple([(o.size, o.size) for o in db.session.query(ShoeSize).all()])


def get_clothing_size_options():
    if not has_request_context():
        return ()
    return tuple([(o.size, o.size) for o in db.session.query(ClothingSize).all()])


def get_fav_color_options():
    if not has_request_context():
        return ()
    return tuple([(o.color, o.color) for o in db.session.query(FavColor).all()])


def get_gender_options():
    if not has_request_context():
        return ()
    return tuple([(o.gender, o.gender) for o in db.session.query(Gender).all()])


def get_race_options():
    if not has_request_context():
        return ()
    return tuple([(o.race, o.race) for o in db.session.query(Race).all()])


class QuerySelectFilter(BaseSQLAFilter):

    def __init__(self, column, name, options=None, data_type=None):
        super(BaseSQLAFilter, self).__init__(name, options, data_type)
        self.column = column

    def get_options(self, view):
        with current_app.app_context():
            return [(row[0], row[0]) for row in view.session.query(self.column).all()]

    def apply(self, query, value, alias=None):
        return query.filter(self.column == value)

    def operation(self):
        return 'is'
