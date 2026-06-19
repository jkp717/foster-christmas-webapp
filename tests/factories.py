"""
Lightweight model factories for tests.

Each make_* function returns a persisted instance with sensible, valid defaults,
and accepts keyword overrides. They commit so downstream lookups and the Child
insert-listeners (which auto-assign child_id and create a gift_fulfillment row)
fire exactly as they do in production.

Adding a new model later: write one make_* function here and the rest of the
suite can build that record without repeating field boilerplate.
"""

from webapp.models import (
    db, Parent, Child, Sponsor, SponsorRequest, Gift,
    Gender, Race, DhsOffice,
)

# A valid US phone number string for the sqlalchemy_utils PhoneNumberType.
VALID_PHONE = "+15015551234"

# Monotonic counter so repeated factory calls produce records that don't trip
# the (first_name, last_name, email) unique constraints on Parent / Sponsor /
# SponsorRequest. Tests can still override any field explicitly.
_seq = 0


def _next():
    global _seq
    _seq += 1
    return _seq


def _first_id(model_cls):
    row = db.session.query(model_cls).first()
    assert row is not None, (
        f"{model_cls.__name__} reference data missing -- the conftest seed "
        f"should have created it."
    )
    return row.id


def make_parent(**kw):
    n = _next()
    defaults = dict(
        first_name="Test",
        last_name=f"Parent{n}",
        phone=VALID_PHONE,
        email=f"parent{n}@example.com",
        gift_delivery=False,
    )
    defaults.update(kw)
    obj = Parent(**defaults)
    db.session.add(obj)
    db.session.commit()
    return obj


def make_sponsor(**kw):
    n = _next()
    defaults = dict(
        first_name="Test",
        last_name=f"Sponsor{n}",
        phone=VALID_PHONE,
        email=f"sponsor{n}@example.com",
    )
    defaults.update(kw)
    obj = Sponsor(**defaults)
    db.session.add(obj)
    db.session.commit()
    return obj


def make_sponsor_request(**kw):
    n = _next()
    defaults = dict(
        first_name="Hopeful",
        last_name=f"Sponsor{n}",
        phone=VALID_PHONE,
        email=f"request{n}@example.com",
        request_count=1,
    )
    defaults.update(kw)
    obj = SponsorRequest(**defaults)
    db.session.add(obj)
    db.session.commit()
    return obj


def make_child(parent=None, sponsor=None, **kw):
    """
    Create a Child. parent/sponsor may be passed as instances; otherwise a
    parent is created and the child is left unsponsored. Reference FKs
    (gender/race/dhs_office) default to the first seeded row.
    """
    if parent is None:
        parent = make_parent()
    defaults = dict(
        first_name="Test",
        last_name="Child",
        age=8,
        gender_id=_first_id(Gender),
        race_id=_first_id(Race),
        dhs_office_id=_first_id(DhsOffice),
        dhs_case_worker="Case Worker",
        parent_id=parent.id,
    )
    if sponsor is not None:
        defaults["sponsor_id"] = sponsor.id
    defaults.update(kw)
    obj = Child(**defaults)
    db.session.add(obj)
    db.session.commit()  # fires before_insert (child_id) + after_insert (fulfillment)
    return obj


def make_gift(child, **kw):
    defaults = dict(
        child_id=child.child_id,
        gift="Bicycle",
        received=False,
    )
    defaults.update(kw)
    obj = Gift(**defaults)
    db.session.add(obj)
    db.session.commit()
    return obj
