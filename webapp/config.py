from markupsafe import Markup

#
# Webapp Configurations
#

# Misc. External URLs
FACEBOOK_URL = "https://www.facebook.com/profile.php?id=61561174376000"
AMAZON_WISHLIST = "https://www.amazon.com/registries/gl/guest-view/3FC1SM55DD3KA?ref=gr_search_page_result"
VOLUNTEER_LINK = "https://signup.com/client/invitation2/0bfd78f34abc02061c408255735b7620aae22954/5457541/false?popup=true&amp;preview=true&amp;return=%2FActivities%23%2F5457541%2Fthemes&amp;theme=winter#/invitation"  # noqa
# ---------------------------------------------------------------------------
# Donation settings
# ---------------------------------------------------------------------------
# The "Donate" item in the top navigation now links to the on-site /donate
# page (see DONATE_NAV_HTML below) instead of posting directly to a single
# payment processor. The donate page lets the donor pick an amount and then
# choose between PayPal and Authorize.Net.
#
# Authorize.Net (Accept Hosted):
#   We use Accept Hosted so the amount the donor selects on our /donate page is
#   carried straight through to Authorize.Net's secure, PCI-compliant payment
#   form (no second amount selection). The flow is:
#     1. Our server calls getHostedPaymentPageRequest with the chosen amount and
#        receives a one-time form token (valid 15 minutes).
#     2. The donor's browser auto-POSTs that token to AUTHNET_HOSTED_FORM_URL,
#        which displays the hosted form.
#     3. After paying, the donor is returned to AUTHNET_RETURN_URL.
#
#   Credentials come from the Merchant Interface:
#     Account > Security Settings > General Security Settings >
#       API Credentials & Keys  (API Login ID + a new Transaction Key)
#   Put them in environment variables in production rather than hard-coding:
#     export AUTHNET_API_LOGIN_ID=...     export AUTHNET_TRANSACTION_KEY=...
#
#   Set AUTHNET_SANDBOX = True while testing with sandbox credentials, then flip
#   to False (and use live credentials) to go live.
import os  # noqa: E402

AUTHNET_API_LOGIN_ID = os.environ.get("AUTHNET_API_LOGIN_ID", "")
AUTHNET_TRANSACTION_KEY = os.environ.get("AUTHNET_TRANSACTION_KEY", "")
AUTHNET_SANDBOX = os.environ.get("AUTHNET_SANDBOX", "true").lower() in ("1", "true", "yes")

# API endpoint (where our server requests the form token) and the hosted-form
# endpoint (where the browser is sent). These switch automatically with sandbox.
if AUTHNET_SANDBOX:
    AUTHNET_API_URL = "https://apitest.authorize.net/xml/v1/request.api"
    AUTHNET_HOSTED_FORM_URL = "https://test.authorize.net/payment/payment"
else:
    AUTHNET_API_URL = "https://api.authorize.net/xml/v1/request.api"
    AUTHNET_HOSTED_FORM_URL = "https://accept.authorize.net/payment/payment"

# Where Authorize.Net returns the donor after the hosted form. Leave the path
# as-is; the scheme+host is taken from the incoming request at runtime so it
# works on localhost and in production without editing.
AUTHNET_RETURN_PATH = "/donate/thank-you"
AUTHNET_CANCEL_PATH = "/donate"

# Text shown on the hosted form / receipt.
AUTHNET_ORDER_DESCRIPTION = "Holiday Hope Tree Donation"

# --- Legacy Simple Checkout (kept for reference / quick rollback) ------------
# The old navbar button posted to this hosted catalog page using a fixed
# LinkId. Accept Hosted replaces it. To revert, point the donate page's
# Authorize.Net path back at these values.
# AUTHNET_PAYMENT_URL = "https://Simplecheckout.authorize.net/payment/CatalogPayment.aspx"
# AUTHNET_LINK_ID = "fcf83d4e-ba93-483c-9217-34cd71e93ebf"

# PayPal (hosted donate flow):
#   Easiest setup is a PayPal "Donate" hosted button. Create one at
#   https://www.paypal.com/donate/buttons and paste its hosted_button_id below.
#   With a hosted button id, PayPal renders its own amount screen, so the
#   amount the donor selects on our page is passed along as a suggestion.
#
#   Alternatively, set PAYPAL_BUSINESS to the PayPal account email to use the
#   classic _donations flow (no hosted button id required). Leave
#   PAYPAL_HOSTED_BUTTON_ID empty in that case.
PAYPAL_PAYMENT_URL = "https://www.paypal.com/donate"
PAYPAL_HOSTED_BUTTON_ID = ""          # e.g. "ABC123XYZ456" (preferred)
PAYPAL_BUSINESS = "holidayhopetreepulaski@gmail.com"  # fallback if no button id
PAYPAL_CURRENCY = "USD"

# Suggested donation amounts (in whole dollars) shown as quick-pick buttons.
DONATION_PRESET_AMOUNTS = [25, 50, 100, 250]

# Navbar entry – now just a link to the on-site donate page.
DONATE_NAV_HTML = Markup("""
      <a class="nav-item nav-link" href="/donate">Donate</a>
    """)

# Main contact info
CONTACT_NAME = "Lillie Price"
CONTACT_EMAIL = "holidayhopetreepulaski@gmail.com"
CONTACT_PHONE = "618-889-6319"

# Child key starting value in DB
CHILD_ID_START_VALUE = 1
CHILD_ID_END_VALUE = 399

# Dates & Locations
GIFT_PICKUP_DATETIME = "Friday, December 12th 9-5pm"
GIFT_PICKUP_LOCATION = "That Church Sherwood (901 E Kiehl Ave, Sherwood)"
CHILD_SIGNUP_DEADLINE = "Nov 2nd"
GIFT_DROPOFF_LOCATIONS = [
    {
        "LOCATION": "The CALL Support Center, 4020 Woodland Heights, Little Rock, AR 72212",
        "DATETIME": "Tuesday-Thursday, December 2nd-4th, from 8:30am-3:30 or please call to reserve a time to drop off gifts",
        "ADDITIONAL_INSTRUCTIONS": ""
    },
    {
        "LOCATION": "That Church Sherwood, 901 E. Kiehl, Sherwood, AR 72120",
        "DATETIME": "Sunday, Dec 7th, from 2-5pm or Monday, Dec 8th, from 8-11am",
        "ADDITIONAL_INSTRUCTIONS": Markup(f"""Please contact {CONTACT_NAME} at <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> with any questions regarding drop-offs at this location.""")
    }
]

# disclaimers
CHILD_REGISTRY_HELPER_TEXT = [
    "Please limit to 3 gifts per child",
    "Please refrain from including items exceeding a value of $200, if your child lists an item that he/she really wants and is over $200 please note that gift may be the only gift your child receives.",  # noqa,
    "No cell phones please"
]

GIFT_DELIVERY_DISCLAIMER = """
    Pickup will be Friday, December 12th from 9am-5pm at That Church in Sherwood. If you are 
    unable to make this work, DHS will be able to deliver to your location.
"""

REGISTER_CHILD_DISCLAIMER = """
    <b>PLEASE READ!</b> Thank you so much for making a difference in a child’s life! This Christmas we 
    are striving to make every child’s wish list come true! Donors and sponsors will choose wish lists to fulfill. 
    Kindly consider that these wish lists are meant for donations, and it might pose a challenge to secure sponsors 
    for highly costly lists. Please refrain from any items exceeding a value of $200 and keep total purchase amount 
    under $300 if possible.
"""

SPONSORSHIP_DISCLAIMER = """
    <b>We appreciate your sponsorship of a child!</b>
    Kindly provide us with your complete information so that we can get in touch regarding drop-off details.
"""

SPONSOR_CHILD_DISCLAIMER = """
    Please find your sponsored child(ren) by searching their name and/or #ID below
"""

SPONSOR_REQUEST_DISCLAIMER = """
    Please be looking out for an email with more info!  Wishlist(s) will be sent no later than November 19th.
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