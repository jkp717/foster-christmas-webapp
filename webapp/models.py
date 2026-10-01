import re
import sqlite3

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy_utils import PhoneNumberType
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property

from webapp.config import CHILD_ID_START_VALUE


db = SQLAlchemy()

def regexp_replace(source, pattern, repl):
    return re.sub(pattern, repl, source)

@event.listens_for(Engine, "connect")
def set_sqlite_custom_functions(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        # This is where you call the standard sqlite3 method
        dbapi_connection.create_function("REGEXP_REPLACE", 3, regexp_replace)


class Gender(db.Model):
    __tablename__ = "gender"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gender = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.gender}'


class Race(db.Model):
    __tablename__ = "race"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    race = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.race}'


class FavColor(db.Model):
    __tablename__ = "fav_color"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    color = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.color}'


class ClothingSize(db.Model):
    __tablename__ = "clothing_size"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    size = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.size}'


class ShoeSize(db.Model):
    __tablename__ = "shoe_size"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    size = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.size}'


class DhsOffice(db.Model):
    __tablename__ = "dhs_office"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    office = db.Column(db.String, nullable=False, unique=True)
    # Child ID number ranges new registrations for this office draw from. An
    # office can own several ranges so it can grow mid-season without
    # renumbering anyone (e.g. 1-100 plus 501-550).
    id_ranges = db.relationship(
        'DhsOfficeIdRange', back_populates='office', cascade='all, delete-orphan',
        order_by='DhsOfficeIdRange.range_start',
    )
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.office}'

    @property
    def range_pairs(self):
        return [(r.range_start, r.range_end) for r in self.id_ranges]

    @property
    def capacity(self):
        """Total number of child IDs across this office's ranges."""
        return sum(end - start + 1 for start, end in self.range_pairs)

    @property
    def ids_in_use(self):
        """How many live children hold an ID inside this office's ranges."""
        pairs = self.range_pairs
        if not pairs:
            return 0
        used = _used_child_numbers(cid for (cid,) in db.session.query(Child.child_id).all())
        return sum(1 for n in used if _in_ranges(n, pairs))


class DhsOfficeIdRange(db.Model):
    __tablename__ = "dhs_office_id_range"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    office_id = db.Column(db.Integer, db.ForeignKey("dhs_office.id"), nullable=False)
    office = db.relationship('DhsOffice', back_populates='id_ranges')
    range_start = db.Column(db.Integer, nullable=False)
    range_end = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'{self.range_start}-{self.range_end}'


def _used_child_numbers(child_ids):
    """Numeric part of each child_id; split IDs like '12A'/'12B' count as 12."""
    used = set()
    for cid in child_ids:
        digits = re.sub('[^0-9]', '', str(cid or ''))
        if digits:
            used.add(int(digits))
    return used


def _in_ranges(n, ranges):
    return any(start <= n <= end for start, end in ranges)


def next_child_id(used, office_ranges, all_ranges):
    """
    Pick the child ID number for a new registration.

    Takes the lowest free number in the office's ranges (in order). If the
    office has no ranges or they are all full, falls back to the overflow pool:
    the first free number above the highest range any office owns (or
    CHILD_ID_START_VALUE when no office has a range).
    """
    for start, end in sorted(office_ranges):
        for n in range(start, end + 1):
            if n not in used:
                return n
    n = max((end for _, end in all_ranges), default=CHILD_ID_START_VALUE - 1) + 1
    while n in used:
        n += 1
    return n


class Church(db.Model):
    __tablename__ = "church"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    church = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.church}'


class Child(db.Model):
    __tablename__ = "child"
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.String, unique=True)
    is_split =  db.Column(db.Boolean, default=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender_id = db.Column(db.Integer, db.ForeignKey("gender.id"), nullable=False)
    gender = db.relationship('Gender')
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"), nullable=False)
    race = db.relationship('Race')
    fav_color_id = db.Column(db.Integer, db.ForeignKey("fav_color.id"))
    fav_color = db.relationship('FavColor')
    shoe_size_id = db.Column(db.Integer, db.ForeignKey("shoe_size.id"))
    shoe_size = db.relationship('ShoeSize')
    clothing_size_id = db.Column(db.Integer, db.ForeignKey("clothing_size.id"))
    clothing_size = db.relationship('ClothingSize')
    dhs_office_id = db.Column(db.Integer, db.ForeignKey("dhs_office.id"), nullable=False)
    dhs_office = db.relationship('DhsOffice')
    dhs_case_worker = db.Column(db.String, nullable=False)
    pulaski_foster_child = db.Column(db.Boolean, default=True)
    in_facility = db.Column(db.Boolean, default=False)
    gifts_need_mailing = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent.id"))
    parent = db.relationship('Parent', back_populates='children')
    church_id = db.Column(db.Integer, db.ForeignKey("church.id"))
    church = db.relationship('Church')
    sponsor_id = db.Column(db.Integer, db.ForeignKey("sponsor.id"))
    sponsor = db.relationship('Sponsor', back_populates='children', uselist=False)
    gifts = db.relationship('Gift', back_populates='child', uselist=True, cascade="all, delete-orphan")
    interests = db.Column(db.Text)
    note = db.Column(db.Text)
    gift_fulfillment = db.relationship(
        'GiftFulfillment',
        backref=db.backref('child', uselist=False),
        cascade='all, delete-orphan',
        uselist=False,
        # 'foreign_keys' is used here to explicitly define the FK on
        # the GiftFulfillment side, pointing back to Child.
        foreign_keys='GiftFulfillment.child_id'
    )
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    @validates('first_name', 'last_name', 'dhs_case_worker')
    def convert_title(self, key, value):
        return value.title()

    @hybrid_property
    def has_sponsor(self):
        return self.sponsor_id is not None

    @has_sponsor.expression
    def has_sponsor(cls):
        return cls.sponsor_id.isnot(None)

    @hybrid_property
    def sponsor_name(self):
        if self.has_sponsor and self.sponsor:
            return f"{self.sponsor.last_name.title()}, {self.sponsor.first_name.title()}"
        return None

    @sponsor_name.expression
    def sponsor_name(cls):
        name_sql = Sponsor.last_name + ', ' + Sponsor.first_name
        return db.case(
            (cls.sponsor_id.isnot(None), name_sql),
            else_=None
        )

    @hybrid_property
    def numeric_sort_child_id(self):
        return re.sub(r'\D', '', self.child_id)

    @numeric_sort_child_id.expression
    def numeric_sort_child_id(cls):
        return db.func.cast(db.func.regexp_replace(cls.child_id, r'\D', ''), db.Integer)

    def __repr__(self):
        return f'{self.first_name.title()} (ID: {self.child_id})'

    def __str__(self):
        return f'{self.first_name.title()} (ID: {self.child_id})'


    # Assign the child ID from the selected office's ranges (see next_child_id).
@event.listens_for(Child, 'before_insert')
def child_id_before_insert(mapper, connection, target):
    if target.child_id is None:
        used = _used_child_numbers(connection.execute(
            text("SELECT child_id FROM child WHERE child_id IS NOT NULL")
        ).scalars().all())
        rows = connection.execute(
            text("SELECT office_id, range_start, range_end FROM dhs_office_id_range")
        ).all()
        all_ranges = [(start, end) for _, start, end in rows]
        office_ranges = [(start, end) for office_id, start, end in rows
                         if office_id == target.dhs_office_id]
        target.child_id = next_child_id(used, office_ranges, all_ranges)


@event.listens_for(Child, 'after_insert')
def child_id_after_insert(mapper, connection, target):
    connection.execute(
        text("INSERT INTO gift_fulfillment (child_id) VALUES (:cid)"),
        {"cid": target.child_id},
    )


@event.listens_for(Child, 'after_update')
def child_id_after_update(mapper, connection, target):
    # Cascade updates to gift child id
    old_values = inspect(target).committed_state
    new_values = {key: getattr(target, key) for key in old_values.keys() if hasattr(target, key)}
    if 'child_id' in old_values.keys() and 'is_split' not in old_values.keys():
        connection.execute(
            text("UPDATE gift SET child_id = :new_cid WHERE child_id = :old_cid"),
            {"new_cid": new_values['child_id'], "old_cid": old_values['child_id']},
        )



class ChildArchive(db.Model):
    __tablename__ = "child_archive"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # child_id repeats every season, so it is NOT unique on its own here.
    # Uniqueness is per-season via the (child_id, archive_year) constraint below.
    # It is a String to match the live Child.child_id type.
    child_id = db.Column(db.String, nullable=False)
    # Season year this row belongs to (set by the archive process). Used to make
    # child_id unique per season and to join gifts/fulfillment to the right year.
    archive_year = db.Column(db.Integer, nullable=False)
    is_split =  db.Column(db.Boolean, default=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender_id = db.Column(db.Integer, db.ForeignKey("gender.id"), nullable=False)
    gender = db.relationship('Gender')
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"), nullable=False)
    race = db.relationship('Race')
    fav_color_id = db.Column(db.Integer, db.ForeignKey("fav_color.id"))
    fav_color = db.relationship('FavColor')
    shoe_size_id = db.Column(db.Integer, db.ForeignKey("shoe_size.id"))
    shoe_size = db.relationship('ShoeSize')
    clothing_size_id = db.Column(db.Integer, db.ForeignKey("clothing_size.id"))
    clothing_size = db.relationship('ClothingSize')
    dhs_office_id = db.Column(db.Integer, db.ForeignKey("dhs_office.id"), nullable=False)
    dhs_office = db.relationship('DhsOffice')
    dhs_case_worker = db.Column(db.String, nullable=False)
    pulaski_foster_child = db.Column(db.Boolean, default=True)
    in_facility = db.Column(db.Boolean, default=False)
    gifts_need_mailing = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_archive.id"))
    parent = db.relationship('ParentArchive', back_populates='children')
    church_id = db.Column(db.Integer, db.ForeignKey("church.id"))
    church = db.relationship('Church')
    sponsor_id = db.Column(db.Integer, db.ForeignKey("sponsor_archive.id"))
    sponsor = db.relationship('SponsorArchive', back_populates='children')
    # Gifts link on BOTH child_id and archive_year (composite FK on GiftArchive)
    # so a gift attaches to the correct season's child.
    gifts = db.relationship(
        'GiftArchive', back_populates='child', uselist=True,
        cascade="all, delete-orphan",
    )
    interests = db.Column(db.Text)
    note = db.Column(db.Text)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    # When this row was moved into the archive (set by the archive process).
    archive_date = db.Column(db.DateTime, default=None)
    __table_args__ = (
        db.UniqueConstraint('child_id', 'archive_year', name='_child_archive_uc'),
    )

    @validates('first_name', 'last_name', 'dhs_case_worker')
    def convert_title(self, key, value):
        return value.title()

    @hybrid_property
    def year(self):
        if self.create_date:
            return self.create_date.year

    @year.expression
    def year(cls):
        return extract('year', cls.create_date)

    @hybrid_property
    def has_sponsor(self):
        return self.sponsor_id is not None

    @hybrid_property
    def sponsor_name(self):
        if self.has_sponsor and self.sponsor:
            return f'{self.sponsor.last_name.title()}, {self.sponsor.first_name.title()}'
        return None

    @sponsor_name.expression
    def sponsor_name(cls):
        name_sql = SponsorArchive.last_name + ', ' + SponsorArchive.first_name
        return db.case((cls.sponsor_id.isnot(None), name_sql), else_=None)

    @hybrid_property
    def numeric_sort_child_id(self):
        return re.sub(r'\D', '', self.child_id)

    @numeric_sort_child_id.expression
    def numeric_sort_child_id(cls):
        # For PostgreSQL: Strip non-digits and cast to a numeric type
        return db.func.cast(db.func.regexp_replace(cls.child_id, r'\D', ''), db.Integer)

    def __repr__(self):
        return f'{self.first_name.title()} (ID: {self.child_id})'

    def __str__(self):
        return f'{self.first_name.title()} (ID: {self.child_id})'


class Parent(db.Model):
    __tablename__ = "parent"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    children = db.relationship('Child', back_populates='parent', uselist=True)
    gift_delivery = db.Column(db.Boolean, default=False)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'email', name='_parent_uc'),
    )

    @validates('first_name', 'last_name')
    def convert_title(self, key, value):
        return value.title()

    @validates('email')
    def convert_lower(self, key, value):
        return value.lower()

    def __repr__(self):
        return f'{self.last_name.title()}, {self.first_name.title()}'

    def __str__(self):
        return f'{self.last_name.title()}, {self.first_name.title()}'


class ParentArchive(db.Model):
    __tablename__ = "parent_archive"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    children = db.relationship('ChildArchive', back_populates='parent', uselist=True)
    gift_delivery = db.Column(db.Boolean, default=False)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    archive_date = db.Column(db.DateTime, default=None)
    archive_year = db.Column(db.Integer)
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'email', name='_parent_archive_uc'),
    )

    @validates('first_name', 'last_name')
    def convert_title(self, key, value):
        return value.title()

    @validates('email')
    def convert_lower(self, key, value):
        return value.lower()

    @hybrid_property
    def year(self):
        if self.create_date:
            return self.create_date.year

    @year.expression
    def year(cls):
        return extract('year', cls.create_date)

    def __repr__(self):
        return f'{self.last_name.title()}, {self.first_name.title()}'

    def __str__(self):
        return f'{self.last_name.title()}, {self.first_name.title()}'


class Gift(db.Model):
    __tablename__ = "gift"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    child_id = db.Column(db.String, db.ForeignKey("child.child_id"))
    child = db.relationship('Child', back_populates='gifts')
    gift = db.Column(db.String, nullable=False)
    received = db.Column(db.Boolean, default=False)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    @validates('gift')
    def convert_title(self, key, value):
        return value.title()

    @hybrid_property
    def year(self):
        if self.create_date:
            return self.create_date.year

    @year.expression
    def year(cls):
        return extract('year', cls.create_date)

    def __repr__(self):
        return f'{self.gift.title()}'

    def __str__(self):
        return f'{self.gift.title()}'


class GiftArchive(db.Model):
    __tablename__ = "gift_archive"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Links to ChildArchive on (child_id, archive_year) -- see the relationship.
    # No single-column FK because child_id is not unique on its own here.
    child_id = db.Column(db.String, nullable=False)
    archive_year = db.Column(db.Integer, nullable=False)
    child = db.relationship('ChildArchive', back_populates='gifts')
    gift = db.Column(db.String, nullable=False)
    received = db.Column(db.Boolean, default=False)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    archive_date = db.Column(db.DateTime, default=None)
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['child_id', 'archive_year'],
            ['child_archive.child_id', 'child_archive.archive_year'],
        ),
    )

    @validates('gift')
    def convert_title(self, key, value):
        return value.title()

    @hybrid_property
    def year(self):
        if self.create_date:
            return self.create_date.year

    @year.expression
    def year(cls):
        return extract('year', cls.create_date)

    def __repr__(self):
        return f'{self.gift.title()}'

    def __str__(self):
        return f'{self.gift.title()}'


class Sponsor(db.Model):
    __tablename__ = "sponsor"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    children = db.relationship('Child', back_populates='sponsor', uselist=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'email', name='_sponsor_uc'),
    )

    @validates('first_name', 'last_name')
    def normalize_names(self, key, value):
        if value is not None:
            return value.title()
        return value

    @validates('email')
    def normalize_email(self, key, value):
        if value is not None:
            return value.lower()
        return value

    def __repr__(self):
        return f'{self.last_name.title(), self.first_name.title()}'

    def __str__(self):
        return f'{self.last_name.title(), self.first_name.title()}'


class SponsorArchive(db.Model):
    __tablename__ = "sponsor_archive"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    children = db.relationship('ChildArchive', back_populates='sponsor', uselist=True)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    archive_date = db.Column(db.DateTime, default=None)
    # Season year (set by the archive process), for consistency with the other
    # archive tables and to support cross-links/filtering by season.
    archive_year = db.Column(db.Integer)
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'email', name='_sponsor_archive_uc'),
    )

    @validates('first_name', 'last_name')
    def normalize_names(self, key, value):
        if value is not None:
            return value.title()
        return value

    @validates('email')
    def normalize_email(self, key, value):
        if value is not None:
            return value.lower()
        return value

    @hybrid_property
    def year(self):
        if self.create_date:
            return self.create_date.year

    @year.expression
    def year(cls):
        return extract('year', cls.create_date)

    def __repr__(self):
        return f'{self.last_name.title(), self.first_name.title()}'

    def __str__(self):
        return f'{self.last_name.title(), self.first_name.title()}'


class SponsorRequest(db.Model):
    __tablename__ = "sponsor_request"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    request_count = db.Column(db.Integer, default=1)
    preferences = db.Column(db.Text)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'email', name='_sponsor_request_uc'),
    )

    @validates('first_name', 'last_name')
    def normalize_names(self, key, value):
        if value is not None:
            return value.title()
        return value

    @validates('email')
    def normalize_email(self, key, value):
        if value is not None:
            return value.lower()
        return value

    def __str__(self):
        if self.first_name and self.last_name:
            return f'{self.last_name.title(), self.first_name.title()}'
        else:
            return 'Name missing!'


class SponsorRequestArchive(db.Model):
    __tablename__ = "sponsor_request_archive"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    request_count = db.Column(db.Integer, default=1)
    preferences = db.Column(db.Text)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))
    archive_date = db.Column(db.DateTime, default=None)
    archive_year = db.Column(db.Integer)
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'email', name='_sponsor_request_archive_uc'),
    )

    @validates('first_name', 'last_name')
    def normalize_names(self, key, value):
        if value is not None:
            return value.title()
        return value

    @validates('email')
    def normalize_email(self, key, value):
        if value is not None:
            return value.lower()
        return value

    @hybrid_property
    def year(self):
        if self.create_date:
            return self.create_date.year

    @year.expression
    def year(cls):
        return extract('year', cls.create_date)

    def __str__(self):
        if self.first_name and self.last_name:
            return f'{self.last_name.title(), self.first_name.title()}'
        else:
            return 'Name missing!'


class GiftFulfillment(db.Model):
    __tablename__ = "gift_fulfillment"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    child_id = db.Column(db.String, db.ForeignKey("child.child_id"), unique=True)
    is_received = db.Column(db.Boolean, default=False)
    received_date = db.Column(db.DateTime, default=None)
    is_pickup = db.Column(db.Boolean, default=False)
    pickup_date = db.Column(db.DateTime, default=None)


@event.listens_for(GiftFulfillment, 'after_update')
def gift_fulfillment_after_update(mapper, connection, target):
    old_values = inspect(target).committed_state
    new_values = {key: getattr(target, key) for key in old_values.keys() if hasattr(target, key)}
    if 'is_received' in old_values.keys():
        if new_values.get('is_received'):
            connection.execute(
                text("UPDATE gift_fulfillment SET received_date = DATETIME('now') WHERE id = :id"),
                {"id": target.id},
            )
        else:
            connection.execute(
                text("UPDATE gift_fulfillment SET received_date = NULL WHERE id = :id"),
                {"id": target.id},
            )
    if 'is_pickup' in old_values.keys():
        if new_values.get('is_pickup'):
            connection.execute(
                text("UPDATE gift_fulfillment SET pickup_date = DATETIME('now') WHERE id = :id"),
                {"id": target.id},
            )
        else:
            connection.execute(
                text("UPDATE gift_fulfillment SET pickup_date = NULL WHERE id = :id"),
                {"id": target.id},
            )


@event.listens_for(GiftFulfillment.__table__, 'after_create')
def gift_fulfillment_after_create(target, connection, **kw):
    existing_children_ids = connection.execute(
        text("SELECT child_id FROM child")
    ).scalars().all()

    for cid in existing_children_ids:
        connection.execute(
            text("INSERT INTO gift_fulfillment (child_id) VALUES (:cid)"),
            {"cid": cid},
        )


class GiftFulfillmentArchive(db.Model):
    __tablename__ = "gift_fulfillment_archive"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Links to ChildArchive on (child_id, archive_year); no single-column FK
    # because child_id repeats across seasons.
    child_id = db.Column(db.String, nullable=False)
    archive_year = db.Column(db.Integer, nullable=False)
    is_received = db.Column(db.Boolean, default=False)
    received_date = db.Column(db.DateTime, default=None)
    is_pickup = db.Column(db.Boolean, default=False)
    pickup_date = db.Column(db.DateTime, default=None)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    archive_date = db.Column(db.DateTime, default=None)
    # Explicit relationship to the season's child (composite key) so list views
    # can show child.first_name / child.last_name.
    child = db.relationship(
        'ChildArchive',
        primaryjoin="and_(foreign(GiftFulfillmentArchive.child_id) == ChildArchive.child_id, "
                    "foreign(GiftFulfillmentArchive.archive_year) == ChildArchive.archive_year)",
        viewonly=True,
        uselist=False,
    )
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['child_id', 'archive_year'],
            ['child_archive.child_id', 'child_archive.archive_year'],
        ),
    )

    @hybrid_property
    def year(self):
        if self.create_date:
            return self.create_date.year

    @year.expression
    def year(cls):
        return extract('year', cls.create_date)

class SiteSetting(db.Model):
    """
    Single-row table holding site-wide settings the admin can edit.

    Controls whether child signup is open (signup is open when
    child_signup_open is True AND today is on/before child_signup_deadline,
    or no deadline is set), and holds the gift pickup date/time text shown on
    the site. The admin can let the date close signups automatically, force it
    closed early, reopen/extend it, and edit the pickup details.
    """
    __tablename__ = "site_setting"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Master on/off switch for child signup (manual override).
    child_signup_open = db.Column(db.Boolean, nullable=False, default=True)
    # Last day signups are accepted (inclusive). Null means "no date limit".
    child_signup_deadline = db.Column(db.Date, default=None)
    # Gift pickup window, stored as native date/time fields. Rendered on the
    # site as e.g. "Friday, December 12th 9am-5pm" by gift_pickup_display.
    gift_pickup_date = db.Column(db.Date, default=None)
    gift_pickup_start = db.Column(db.Time, default=None)
    gift_pickup_end = db.Column(db.Time, default=None)
    # Amazon wish list link shown on the Get Involved page. Null falls back to
    # the AMAZON_WISHLIST config constant.
    amazon_wishlist = db.Column(db.String(500), default=None)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return "Site Settings"

    @classmethod
    def get(cls):
        """Return the singleton settings row, creating it if absent."""
        setting = db.session.query(cls).order_by(cls.id.asc()).first()
        if setting is None:
            setting = cls(child_signup_open=True, child_signup_deadline=None)
            db.session.add(setting)
            db.session.commit()
        return setting

    @hybrid_property
    def is_child_signup_open(self):
        """True if child signup should currently accept submissions."""
        if not self.child_signup_open:
            return False
        if self.child_signup_deadline is None:
            return True
        return datetime.now(timezone.utc).date() <= self.child_signup_deadline

    @staticmethod
    def _ordinal(n):
        # 1 -> "1st", 2 -> "2nd", 11 -> "11th", 22 -> "22nd", etc.
        if 11 <= (n % 100) <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    @property
    def child_signup_deadline_display(self):
        """
        Format the deadline with the full month name (e.g. "November 2nd").
        Returns an empty string when no deadline is set.
        """
        if self.child_signup_deadline is None:
            return ""
        d = self.child_signup_deadline
        return f"{d.strftime('%B')} {self._ordinal(d.day)}"

    @staticmethod
    def _format_time(t, with_meridiem=True):
        """
        Format a time like the legacy string: hour only when minutes are zero
        ("9", "5"), hour:minutes otherwise ("9:30"), lowercase am/pm appended
        only when with_meridiem is True ("5pm"). 12-hour clock, no leading zero.
        """
        if t is None:
            return ""
        hour12 = t.hour % 12 or 12
        if t.minute:
            base = f"{hour12}:{t.minute:02d}"
        else:
            base = f"{hour12}"
        if with_meridiem:
            base += "am" if t.hour < 12 else "pm"
        return base

    @property
    def gift_pickup_display(self):
        """
        Rebuild the display string from the date/time parts, e.g.
        "Friday, December 12th 9am-5pm". Each piece is optional: if only the
        date is set you get "Friday, December 12th"; if only times are set you
        get the time range alone. Returns "" when nothing is set.
        """
        parts = []

        if self.gift_pickup_date is not None:
            d = self.gift_pickup_date
            parts.append(f"{d.strftime('%A, %B')} {self._ordinal(d.day)}")

        start, end = self.gift_pickup_start, self.gift_pickup_end
        time_str = ""
        if start is not None and end is not None:
            time_str = f"{self._format_time(start)}-{self._format_time(end)}"
        elif start is not None:
            time_str = self._format_time(start)
        elif end is not None:
            time_str = self._format_time(end)

        if time_str:
            parts.append(time_str)

        return " ".join(parts)
