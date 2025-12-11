import re
import sqlite3

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy_utils import PhoneNumberType
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property

from webapp.config import CHILD_ID_START_VALUE, CHILD_ID_END_VALUE


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
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.office}'


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


    # create the starting key on table creation
@event.listens_for(Child, 'before_insert')
def child_id_before_insert(mapper, connection, target):
    if target.child_id is None:
        potential_values = list(range(CHILD_ID_START_VALUE, CHILD_ID_END_VALUE + 1))
        existing_values = connection.execute(db.DDL(
            f"SELECT child_id FROM child where child_id;")
        ).scalars().all()

        # Remove non-numeric characters from the child ids
        stripped_existing_val = []

        for ex in existing_values:
            stripped_existing_val.append(int(re.sub('[^0-9]', '', ex)))

        existing_set = set(stripped_existing_val)
        for value in potential_values:
            if value not in existing_set:
                target.child_id = value
                return


@event.listens_for(Child, 'after_insert')
def child_id_after_insert(mapper, connection, target):
    connection.execute(db.DDL(
        f"INSERT INTO gift_fulfillment (child_id) values ('{target.child_id}');")
    )


@event.listens_for(Child, 'after_update')
def child_id_after_update(mapper, connection, target):
    # Cascade updates to gift child id
    old_values = inspect(target).committed_state
    new_values = {key: getattr(target, key) for key in old_values.keys() if hasattr(target, key)}
    if 'child_id' in old_values.keys() and 'is_split' not in old_values.keys():
        connection.execute(db.DDL(
            f"UPDATE gift SET child_id = '{new_values['child_id']}' WHERE child_id = '{old_values['child_id']}';")
        )



class ChildArchive(db.Model):
    __tablename__ = "child_archive"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    child_id = db.Column(db.Integer, unique=True, nullable=False)
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
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_archive.id"))
    parent = db.relationship('ParentArchive', back_populates='children')
    church_id = db.Column(db.Integer, db.ForeignKey("church.id"))
    church = db.relationship('Church')
    sponsor_id = db.Column(db.Integer, db.ForeignKey("sponsor_archive.id"))
    sponsor = db.relationship('SponsorArchive', back_populates='children')
    gifts = db.relationship('GiftArchive', back_populates='child', uselist=True, cascade="all, delete-orphan")
    interests = db.Column(db.Text)
    note = db.Column(db.Text)
    create_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    modify_date = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc))

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
    child_id = db.Column(db.String, db.ForeignKey("child_archive.child_id"))
    child = db.relationship('ChildArchive', back_populates='gifts')
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
            sql_rec_datetime = "DATETIME('now')"
        else:
            sql_rec_datetime = "NULL"
        connection.execute(db.DDL(
            f"UPDATE gift_fulfillment SET received_date = {sql_rec_datetime} WHERE id = '{target.id}';")
        )
    if 'is_pickup' in old_values.keys():
        if new_values.get('is_pickup'):
            sql_pu_datetime = "DATETIME('now')"
        else:
            sql_pu_datetime = "NULL"
        connection.execute(db.DDL(
            f"UPDATE gift_fulfillment SET pickup_date = {sql_pu_datetime} WHERE id = '{target.id}';")
        )


@event.listens_for(GiftFulfillment.__table__, 'after_create')
def gift_fulfillment_after_create(target, connection, **kw):
    existing_children_ids = connection.execute(db.DDL(
        f"SELECT child_id FROM child;")
    ).scalars().all()

    for cid in existing_children_ids:
        connection.execute(db.DDL(
            f"INSERT INTO gift_fulfillment (child_id) values ('{cid}');")
        )