import datetime
from flask_sqlalchemy import SQLAlchemy


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


class Child(db.Model):
    __tablename__ = "child"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    age = db.Column(db.Integer)
    gender_id = db.Column(db.Integer, db.ForeignKey("gender.id"))
    gender = db.relationship('Gender')
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))
    race = db.relationship('Race')
    fav_color_id = db.Column(db.Integer, db.ForeignKey("fav_color.id"))
    fav_color = db.relationship('FavColor')
    shoe_size_id = db.Column(db.Integer, db.ForeignKey("shoe_size.id"))
    shoe_size = db.relationship('ShoeSize')
    clothing_size_id = db.Column(db.Integer, db.ForeignKey("clothing_size.id"))
    clothing_size = db.relationship('ClothingSize')
    dhs_office_id = db.Column(db.Integer, db.ForeignKey("dhs_office.id"))
    dhs_office = db.relationship('DhsOffice')
    dhs_case_worker = db.Column(db.String)
    pulaski_foster_child = db.Column(db.Boolean, default=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent.id"))
    parent = db.relationship('Parent', back_populates='children')
    gifts = db.relationship('Gift', back_populates='child', uselist=True, cascade="all, delete-orphan")
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.last_name}, {self.first_name}'


class Parent(db.Model):
    __tablename__ = "parent"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    phone = db.Column(db.Integer)
    email = db.Column(db.String)
    children = db.relationship('Child', back_populates='parent', uselist=True, cascade="all, delete-orphan")
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.last_name}, {self.first_name}'


class Gift(db.Model):
    __tablename__ = "gift"
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"))
    child = db.relationship('Child', back_populates='gifts')
    gift = db.Column(db.String, nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modify_date = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'{self.gift}'