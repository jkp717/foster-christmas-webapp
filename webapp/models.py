import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import PhoneNumberType
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()


class Gender(db.Model):
    __tablename__ = "gender"
    id = db.Column(db.Integer, primary_key=True)
    gender = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.gender}'


class Race(db.Model):
    __tablename__ = "race"
    id = db.Column(db.Integer, primary_key=True)
    race = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.race}'


class FavColor(db.Model):
    __tablename__ = "fav_color"
    id = db.Column(db.Integer, primary_key=True)
    color = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.color}'


class ClothingSize(db.Model):
    __tablename__ = "clothing_size"
    id = db.Column(db.Integer, primary_key=True)
    size = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.size}'


class ShoeSize(db.Model):
    __tablename__ = "shoe_size"
    id = db.Column(db.Integer, primary_key=True)
    size = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.size}'


class DhsOffice(db.Model):
    __tablename__ = "dhs_office"
    id = db.Column(db.Integer, primary_key=True)
    office = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.office}'


class Church(db.Model):
    __tablename__ = "church"
    id = db.Column(db.Integer, primary_key=True)
    church = db.Column(db.String, nullable=False, unique=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.church}'


class Child(db.Model):
    __tablename__ = "child"
    id = db.Column(db.Integer, primary_key=True)
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
    sponsor = db.relationship('Sponsor', back_populates='children')
    gifts = db.relationship('Gift', back_populates='child', uselist=True, cascade="all, delete-orphan")
    note = db.Column(db.Text)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    @validates('first_name', 'last_name', 'dhs_case_worker')
    def convert_title(self, key, value):
        return value.title()

    @hybrid_property
    def has_sponsor(self):
        return self.sponsor_id is not None

    def __repr__(self):
        return f'{self.last_name.title()}, {self.first_name.title()} ({self.id})'

    def __str__(self):
        return f'{self.last_name.title()}, {self.first_name.title()} ({self.id})'


class Parent(db.Model):
    __tablename__ = "parent"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    children = db.relationship('Child', back_populates='parent', uselist=True)
    gift_delivery = db.Column(db.Boolean, default=False)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)
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


class Gift(db.Model):
    __tablename__ = "gift"
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"))
    child = db.relationship('Child', back_populates='gifts')
    gift = db.Column(db.String, nullable=False)
    received = db.Column(db.Boolean, default=False)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    @validates('gift')
    def convert_title(self, key, value):
        return value.title()

    def __repr__(self):
        return f'{self.gift.title()}'

    def __str__(self):
        return f'{self.gift.title()}'


class Sponsor(db.Model):
    __tablename__ = "sponsor"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    phone = db.Column(PhoneNumberType(), nullable=False)
    email = db.Column(db.String, nullable=False)
    children = db.relationship('Child', back_populates='sponsor', uselist=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'email', name='_sponsor_uc'),
    )