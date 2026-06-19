"""
Custom WTForms fields for the admin.

TwelveHourTimeField is a SelectField whose options are whole-hour times on a
12-hour clock with AM/PM ("9:00 AM", "5:00 PM", ...). It coerces between the
selected option and a datetime.time. Using a stock SelectField (rather than a
custom multi-widget field) keeps Flask-Admin's form/save flow working normally
while still limiting input to valid 12-hour choices.
"""

from datetime import time

from wtforms import SelectField


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
