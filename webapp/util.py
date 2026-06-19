from datetime import date, datetime
from sqlalchemy import extract
from flask_admin.model import typefmt
from flask_admin.babel import lazy_gettext
from flask import current_app, has_request_context, url_for
from markupsafe import Markup
from flask_admin.contrib.sqla.filters import BaseSQLAFilter, BooleanEqualFilter, FilterLike, FilterEqual
from flask_admin.contrib.sqla import tools

from .models import db, DhsOffice, ShoeSize, ClothingSize, FavColor, Gender, Race, Church


def date_format(view, value, name):
    if value is None:
        return ''
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


def sponsor_archive_children_formatter(view, context, model, name):  # noqa
    """
    Children-count link for the SponsorArchive view. Points at the Child Archive
    list filtered by this sponsor's archive id AND season year, so it shows only
    that sponsor's children for that season.

    The query-string keys are the ones Flask-Admin actually generates for the
    archive child view's filters (confirmed from the running app):
      flt0_sponsorid_equals  -> the 'sponsor_id' filter (name slugified to
                                 'sponsorid')
      flt2_year_equals       -> the create_date-based 'Year' filter
    """
    cnt = len(model.children)
    if cnt > 0:
        base = url_for("childarchive.index_view")
        qs = (f"flt0_sponsorid_equals={model.id}"
              f"&flt2_year_equals={model.archive_year}")
        return Markup(
            f"""<a class="list-model-link" href='{base}?{qs}'>{cnt}</a>"""
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


# Number of characters to show before truncating a comment/note preview.
# Tuned to roughly fill the wider Notes column at the smaller preview font
# size (two clamped lines); the full text is always available via the tooltip.
NOTE_PREVIEW_CHARS = 160


def note_preview_formatter(view, context, model, name):
    """
    Display formatter for comment/note columns in list views. Returns a short
    preview (truncated with an ellipsis when the text is longer), wrapped so the
    full text is available as a hover tooltip and the cell can be CSS-clamped to
    a couple of lines. Empty notes render as a muted placeholder.

    The markup is intentionally simple so it works whether or not the column is
    inline-editable; CSS in admin.css handles the 2-line clamp and the edit icon.
    """
    value = getattr(model, name, None) or ''
    value = str(value).strip()
    if not value:
        return Markup('<span class="note-empty">&mdash;</span>')

    truncated = len(value) > NOTE_PREVIEW_CHARS
    preview = value[:NOTE_PREVIEW_CHARS].rstrip()
    # Escape via markupsafe by building with escaped parts.
    from markupsafe import escape
    full_attr = escape(value)
    preview_html = escape(preview)
    more = '<span class="note-more" aria-hidden="true">&hellip;</span>' if truncated else ''
    return Markup(
        f'<span class="note-cell" title="{full_attr}">'
        f'<span class="note-text">{preview_html}</span>{more}'
        f'</span>'
    )


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


def get_sponsor_archive_filters(model_cls):
    """Filters for the SponsorArchive view (name/email/phone + season year)."""
    return [
        FilterCaseLike(model_cls.last_name, 'Last Name'),
        FilterCaseLike(model_cls.first_name, 'First Name'),
        FilterCaseLike(model_cls.email, 'Email'),
        FilterLike(model_cls.phone, 'Phone'),
        FilterYear(model_cls.create_date, 'Year'),
    ]


def get_sponsor_request_archive_filters(model_cls):
    """Filters for the SponsorRequestArchive view."""
    return [
        FilterCaseLike(model_cls.last_name, 'Last Name'),
        FilterCaseLike(model_cls.first_name, 'First Name'),
        FilterCaseLike(model_cls.email, 'Email'),
        FilterLike(model_cls.phone, 'Phone'),
        FilterYear(model_cls.create_date, 'Year'),
    ]


def get_gift_fulfillment_archive_filters(model_cls, child_model_cls):
    """Filters for the GiftFulfillmentArchive view."""
    return [
        'child_id',
        FilterCaseLike(child_model_cls.first_name, 'Child First Name'),
        FilterCaseLike(child_model_cls.last_name, 'Child Last Name'),
        'is_received',
        'is_pickup',
        FilterYear(model_cls.create_date, 'Year'),
    ]


def get_parent_filters(model_cls, include_year=False):
    """Generates the column_filters list for a given Parent/ParentArchive model."""
    filters = [
        BooleanEqualFilter(model_cls.gift_delivery, 'DHS Gift Delivery'),
        FilterCaseLike(model_cls.last_name, 'Last Name'),
        FilterCaseLike(model_cls.first_name, 'First Name'),
        FilterCaseLike(model_cls.email, 'Email'),
        FilterLike(model_cls.phone, 'Phone'),
    ]
    if include_year:
        filters.append(FilterYear(model_cls.create_date, 'Year'))
    return filters


def get_gift_filters(model_cls, child_model_cls, include_year=False):
    """Generates the column_filters list for a given Gift/GiftArchive model."""
    filters = [
        'child_id',
        'child.age',
        'create_date',
        'received',
        FilterCaseLike(child_model_cls.first_name, 'Child First Name'),
        FilterCaseLike(child_model_cls.last_name, 'Child Last Name'),
        'child.gender.gender'
    ]
    if include_year:
        filters.append(FilterYear(model_cls.create_date, 'Year'))
    return filters

def get_child_filters(model_cls, sponsor_cls, parent_cls, include_year=False):
    """Generates the column_filters list for a given Child/ChildArchive model.

    When include_year is True (archive views), two filters are placed FIRST at
    fixed positions so links can target them by a known index:
      flt0 -> sponsor_id equals
      flt1 -> archive_year equals
    followed by a create_date-based Year filter at the end.
    """
    filters = []
    if include_year:
        # Fixed-position filters used by archive cross-links. The filter NAME
        # determines the URL slug Flask-Admin generates, so these are named to
        # match exactly the keys sponsor_archive_children_formatter builds:
        #   flt0_sponsor_id_equals, flt1_archive_year_equals
        filters.append(FilterEqual(model_cls.sponsor_id, 'sponsor_id'))
        filters.append(FilterEqual(model_cls.archive_year, 'archive_year'))
    filters += [
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
    if include_year:
        filters.append(FilterYear(model_cls.create_date, 'Year'))
    return filters

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


class FilterYear(BaseSQLAFilter):
    """
    Filter archive rows by the year extracted from create_date. Pass the model's
    create_date column (e.g. ChildArchive.create_date). The entered value is a
    4-digit year; rows whose create_date falls in that year match.
    """
    def apply(self, query, value, alias=None):
        try:
            year = int(value)
        except (TypeError, ValueError):
            return query
        return query.filter(extract('year', self.get_column(alias)) == year)

    def operation(self):
        return lazy_gettext('equals')