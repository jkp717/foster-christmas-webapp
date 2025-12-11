from datetime import date, datetime
from flask_admin.model import typefmt
from flask_admin.babel import lazy_gettext
from flask import current_app, has_request_context, url_for
from markupsafe import Markup
from flask_admin.contrib.sqla.filters import BaseSQLAFilter, BooleanEqualFilter, FilterLike, FilterEqual
from flask_admin.contrib.sqla import tools

from .models import db, DhsOffice, ShoeSize, ClothingSize, FavColor, Gender, Race, Church


def date_format(view, value, name):
    return value.strftime('%m/%d/%Y')


DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
DEFAULT_FORMATTERS.update({date: date_format})

def gift_list_formatter(view, context, model, name):  # noqa
    cnt = len(model.gifts)
    filter_txt = 'flt0_child_id_equals'
    if cnt > 0:
        return Markup(
            f"""<a class="list-model-link" href='{url_for("gift.index_view")}?{filter_txt}={model.child_id}'>{cnt}</a>"""
        )
    return "0"


def child_id_formatter(view, context, model, name):  # noqa
    if model.is_split:
        return Markup(
            f"""<div class="disabled">{getattr(model, name)}</a>"""
        )
    return Markup(getattr(model, name))


def sponsor_children_formatter(view, context, model, name):  # noqa
    cnt = len(model.children)
    filter_txt = 'flt0_sponsor_id_equals'
    if cnt > 0:
        return Markup(
            f"""<a class="list-model-link" href='{url_for("child.index_view")}?{filter_txt}={model.id}'>{cnt}</a>"""
        )
    return "0"

def gift_list_export_formatter(view, context, model, name):  # noqa
    return getattr(model, name)


def title_case_formatter(view, context, model, name):
    """
    `view` is current administrative view
    `context` is instance of jinja2.runtime.Context
    `model` is model instance
    `name` is property name
    """
    return getattr(model, name, '').title()


def datetime_formatter(view, context, model, name):
    if isinstance(getattr(model, name), datetime):
        return getattr(model, name).strftime('%m/%d/%Y %I:%M %p')


def get_dhs_office_options():
    if not has_request_context():
        return ()
    return tuple([(o.office, o.office) for o in db.session.query(DhsOffice).all()])


def get_church_options():
    if not has_request_context():
        return ()
    return tuple([(o.church, o.church) for o in db.session.query(Church).all()])

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


def get_parent_filters(model_cls):
    """Generates the column_filters list for a given Parent/ParentArchive model."""
    return [
        BooleanEqualFilter(model_cls.gift_delivery, 'DHS Gift Delivery'),
        FilterCaseLike(model_cls.last_name, 'Last Name'),
        FilterCaseLike(model_cls.first_name, 'First Name'),
        FilterCaseLike(model_cls.email, 'Email'),
        FilterLike(model_cls.phone, 'Phone'),
    ]


def get_gift_filters(model_cls, child_model_cls):
    """Generates the column_filters list for a given Gift/GiftArchive model."""
    return [
        'child_id',
        'child.age',
        'create_date',
        'received',
        FilterCaseLike(child_model_cls.first_name, 'Child First Name'),
        FilterCaseLike(child_model_cls.last_name, 'Child Last Name'),
        'child.gender.gender'
    ]

def get_child_filters(model_cls, sponsor_cls, parent_cls):
    """Generates the column_filters list for a given Child/ChildArchive model."""
    return [
        'child_id',
        'age',
        # BooleanEqualFilter(Child.has_sponsor, 'Sponsored'),
        BooleanFilter(model_cls.has_sponsor, 'Sponsored'),
        FilterCaseLike(model_cls.interests, 'Child Interests'),
        FilterCaseLike(sponsor_cls.last_name, 'Sponsor Last Name'),
        FilterCaseLike(sponsor_cls.first_name, 'Sponsor First Name'),
        FilterCaseLike(parent_cls.last_name, 'Parent Last Name'),
        FilterCaseLike(parent_cls.first_name, 'Parent First Name'),
        FilterCaseLike('dhs_case_worker', 'Case Worker'),
        FilterCaseLike(model_cls.first_name, 'Child First Name'),
        FilterCaseLike(model_cls.last_name, 'Child Last Name'),
        FilterEqual(DhsOffice.office, 'DHS Office', options=get_dhs_office_options),
        FilterEqual(Race.race, 'Child Race', options=get_race_options),
        FilterEqual(Gender.gender, 'Child Gender', options=get_gender_options),
        FilterEqual(ShoeSize.size, 'Shoe Size', options=get_shoe_size_options),
        FilterEqual(ClothingSize.size, 'Clothing Size', options=get_clothing_size_options),
        FilterEqual(FavColor.color, 'Favorite Color', options=get_fav_color_options),
        FilterEqual(Church.church, 'Assigned Church', options=get_church_options)
    ]

def get_gift_fulfillment_filters(model_cls, child_model_cls):
    """Generates the column_filters list for a given Gift/GiftArchive model."""
    return [
        'child_id',
        FilterCaseLike(child_model_cls.first_name, 'Child First Name'),
        FilterCaseLike(child_model_cls.last_name, 'Child Last Name'),
        'is_received',
        'is_pickup',
        'received_date',
        'pickup_date',
    ]

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


class FilterCaseLike(BaseSQLAFilter):
    def apply(self, query, value, alias=None):

        if isinstance(value, str):
            value = value.lower()

        stmt = tools.parse_like_term(value)
        return query.filter(self.get_column(alias).ilike(stmt))

    def operation(self):
        return lazy_gettext('contains')

class BooleanFilter(BooleanEqualFilter):
    def apply(self, query, value, alias=None):
        return query.filter(self.get_column(alias) == int(value))

    def operation(self):
        return lazy_gettext('equals')