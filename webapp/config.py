#
# Webapp Configurations
#

# disclaimers
GIFT_DELIVERY_DISCLAIMER = """
    Pickup will be Friday, December 15th from 8:30am-6pm and Saturday Dec 16th from 8:30am-2pm at That Church in 
    Sherwood. If you are unable to make this work, DHS will be able to deliver to your location.
"""

REGISTER_CHILD_DISCLAIMER = """
    <b>PLEASE READ!</b> Thank you so much for making a difference in a child’s life!
    This Christmas we are striving to make every child’s wish list come true!
    Donors and sponsors will choose wish lists to fulfill. Kindly consider that these
    wish lists are meant for donations, and it might pose a challenge to secure sponsors for highly costly lists.
    Please refrain from any items exceeding a value of $200.
"""

SPONSORSHIP_DISCLAIMER = """
    <b>We appreciate your sponsorship of a child!</b>
    Kindly provide us with your complete information so that we can get in touch regarding drop-off details.
"""

SPONSOR_CHILD_DISCLAIMER = """
    Please find your sponsored child(ren) by searching their name (last, first) or ID below
"""

# database defaults
db_defaults = {
    'race': {
        'race': [
            "American Indian or Alaska Native",
            "Asian",
            "Black or African American",
            "Native Hawaiian or Other Pacific Islander",
            "White",
        ]
    },
    'gender': {
        'gender': [
            "Male",
            "Female"
        ]
    },
    'fav_color': {
        'color': [
            "Red",
            "Blue",
            "Yellow",
            "Orange",
            "Green",
            "Pink",
            "Purple",
            "Black",
            "Grey",
        ]
    },
    'shoe_size': {
        'size': [
            '1C',
            '2C',
            '3C',
            '4C',
            '5C',
            '6C',
            '7C',
            '8C',
            '9C',
            '10C',
            '10.5C',
            '11C',
            '11.5C',
            '12C',
            '12.5C',
            '13C',
            '13.5C',
            '1Y',
            '1.5Y',
            '2Y',
            '2.5Y',
            '3Y',
            '3.5Y',
            '4Y',
            '4.5Y',
            '5Y',
            '5.5Y',
            '6Y',
            '6.5Y',
            '7Y',
            '7M',
            '7.5M',
            '8M',
            '8.5M',
            '9M',
            '9.5M',
            '10M',
            '10.5M',
            '11M',
            '11.5M',
            '12M',
            '13M',
            '14M',
            '15M',
            '7W',
            '7.5W',
            '8W',
            '8.5W',
            '9W',
            '9.5W',
            '10W',
            '10.5W',
            '11W',
            '11.5W',
            '12W',
            '13W',
            '14W',
            '15W',
        ]
    },
    'clothing_size': {
        'size': [
            "Preemie",
            "Newborn",
            "3M",
            "6M",
            "9M",
            "12M",
            "18M",
            "24M",
            "2T",
            "3T",
            "4T",
            "Y5",
            "Y6",
            "Y6X-7",
            "Y8",
            "Y10",
            "Y12",
            "Y14",
            "Y16"
        ]
    },
    'dhs_office': {
        'office': [
            'North',
            'South',
            'Southeast',
            'Jacksonville',
            'Not Sure'
        ]
    }
}