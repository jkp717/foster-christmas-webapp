"""
Custom WTForms fields for the admin.

TwelveHourTimeField is a SelectField whose options are whole-hour times on a
12-hour clock with AM/PM ("9:00 AM", "5:00 PM", ...). It coerces between the
selected option and a datetime.time. Using a stock SelectField (rather than a
custom multi-widget field) keeps Flask-Admin's form/save flow working normally
while still limiting input to valid 12-hour choices.

This module also provides an email anti-junk helper for the public
registration forms:
  * DeliverableEmail -- a WTForms validator that checks the address is
    well-formed AND that its domain can actually receive mail (MX records),
    catching both typos ("foo@gmial.com") and malformed input ("annjohnx1").

(The bot honeypot is rendered as raw HTML in ParentView.form_rules and checked
server-side in the public `parent` route, so it needs no custom field here.)
"""

from datetime import time

from wtforms import SelectField
from wtforms.validators import ValidationError

try:
    # email-validator is already a project dependency (used by WTForms-Alchemy).
    from email_validator import validate_email, EmailNotValidError
    _HAVE_EMAIL_VALIDATOR = True
except Exception:  # pragma: no cover - dependency always present in prod
    _HAVE_EMAIL_VALIDATOR = False


class DeliverableEmail:
    """
    WTForms validator: the value must be a syntactically valid email whose
    domain has deliverability (MX/A records). Catches typos and dead/misspelled
    domains in addition to malformed addresses.

    DNS is consulted for the deliverability check. If the DNS lookup itself
    fails for an environmental reason (timeout, no resolver), we DO NOT block
    the submission on that alone -- we only enforce syntax in that case, so a
    transient network problem never stops a legitimate foster parent from
    registering. A domain that resolves but has no mail records is still
    rejected.
    """

    def __init__(self, message=None, check_deliverability=True):
        self.message = message or 'Please enter a valid, reachable email address.'
        self.check_deliverability = check_deliverability

    def __call__(self, form, field):
        value = (field.data or '').strip()
        if not value:
            return  # let DataRequired/Optional handle emptiness
        if not _HAVE_EMAIL_VALIDATOR:
            return  # nothing we can do without the library; don't block
        # First pass: syntax only (no DNS). A failure here is a definite reject.
        try:
            validate_email(value, check_deliverability=False)
        except EmailNotValidError:
            raise ValidationError(self.message)
        # Second pass: deliverability (DNS). Only reject when the library tells
        # us the DOMAIN is bad; swallow environmental DNS errors.
        if self.check_deliverability:
            try:
                validate_email(value, check_deliverability=True)
            except EmailNotValidError:
                # Domain doesn't resolve / has no mail records -> reject.
                raise ValidationError(self.message)
            except Exception:
                # DNS timeout / resolver missing / etc. -> don't block on this.
                return


def _time_choices():
    """All whole hours as (value, label) pairs, value is 24h 'HH:MM'."""
    choices = [('', '--')]
    for h24 in range(0, 24):
        h12 = h24 % 12 or 12
        ampm = 'AM' if h24 < 12 else 'PM'
        choices.append((f"{h24:02d}:00", f"{h12}:00 {ampm}"))
    return choices


class TwelveHourTimeField(SelectField):
    """
    A dropdown of whole-hour times shown in 12-hour AM/PM format. Stores a
    datetime.time on the model; an empty selection stores None.
    """
    def __init__(self, label=None, validators=None, **kwargs):
        kwargs.setdefault('choices', _time_choices())
        # Coerce keeps the posted string; we convert to/from time ourselves.
        kwargs.setdefault('coerce', str)
        super().__init__(label, validators, **kwargs)

    def process_data(self, value):
        """model -> form: store the selectable string for the stored time."""
        if isinstance(value, time):
            self.data = f"{value.hour:02d}:{value.minute:02d}"
        elif value is None:
            self.data = ''
        else:
            self.data = value

    def process_formdata(self, valuelist):
        """form -> raw selected string."""
        if valuelist:
            self.data = valuelist[0]
        else:
            self.data = ''

    def populate_obj(self, obj, name):
        """form -> model: convert the selected 'HH:MM' string into a time."""
        setattr(obj, name, self._to_time(self.data))

    @staticmethod
    def _to_time(value):
        if not value:
            return None
        try:
            hh, mm = value.split(':')
            return time(hour=int(hh), minute=int(mm))
        except (ValueError, AttributeError):
            return None

    def pre_validate(self, form):
        # Allow the blank option; otherwise SelectField rejects '' as invalid.
        if self.data in ('', None):
            return
        valid = {c[0] for c in self.choices}
        if self.data not in valid:
            raise ValueError(self.gettext('Not a valid choice.'))
