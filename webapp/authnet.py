"""
Authorize.Net Accept Hosted integration.

This module contains the single network call we need for Accept Hosted:
requesting a one-time *form token* from Authorize.Net for a donation of a
specific amount. The donor's browser then POSTs that token to the hosted
payment form (see views.donate_authnet), so the amount is fixed server-side
and cannot be tampered with by the client.

Docs: https://developer.authorize.net/api/reference/features/accept-hosted.html

No third-party SDK is required -- this is a plain JSON POST using the standard
library, which keeps the project's dependency list unchanged.
"""

import json
import uuid
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError


class AuthnetError(Exception):
    """Raised when a form token cannot be obtained from Authorize.Net."""


def normalize_amount(raw):
    """
    Validate and normalize a donation amount to a 2-decimal string.

    Accepts int/float/str. Returns a string like "50.00". Raises AuthnetError
    if the value is missing, non-numeric, or not positive.
    """
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        raise AuthnetError("Donation amount is not a valid number.")
    if amount <= 0:
        raise AuthnetError("Donation amount must be greater than zero.")
    # Round to cents.
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_request_payload(
    api_login_id,
    transaction_key,
    amount,
    return_url,
    cancel_url,
    order_description,
):
    """
    Construct the getHostedPaymentPageRequest JSON body.

    `hostedPaymentSettings` values must themselves be JSON-encoded strings,
    per the Authorize.Net spec.
    """
    settings = [
        {
            "settingName": "hostedPaymentReturnOptions",
            "settingValue": json.dumps(
                {
                    "showReceipt": True,
                    "url": return_url,
                    "urlText": "Return to Holiday Hope Tree",
                    "cancelUrl": cancel_url,
                    "cancelUrlText": "Cancel",
                }
            ),
        },
        {
            "settingName": "hostedPaymentButtonOptions",
            "settingValue": json.dumps({"text": "Donate"}),
        },
        {
            "settingName": "hostedPaymentPaymentOptions",
            "settingValue": json.dumps(
                {"cardCodeRequired": True, "showCreditCard": True, "showBankAccount": False}
            ),
        },
        {
            "settingName": "hostedPaymentOrderOptions",
            "settingValue": json.dumps({"show": True, "merchantName": "Holiday Hope Tree"}),
        },
        {
            "settingName": "hostedPaymentStyleOptions",
            # Holiday red to match the site.
            "settingValue": json.dumps({"bgColor": "#af1e2c"}),
        },
        {
            "settingName": "hostedPaymentSecurityOptions",
            "settingValue": json.dumps({"captcha": False}),
        },
    ]

    return {
        "getHostedPaymentPageRequest": {
            "merchantAuthentication": {
                "name": api_login_id,
                "transactionKey": transaction_key,
            },
            # A unique ref helps with idempotency/troubleshooting.
            "refId": uuid.uuid4().hex[:20],
            "transactionRequest": {
                "transactionType": "authCaptureTransaction",
                "amount": amount,
                "order": {"description": order_description},
            },
            "hostedPaymentSettings": {"setting": settings},
        }
    }


def get_form_token(
    api_login_id,
    transaction_key,
    api_url,
    amount,
    return_url,
    cancel_url,
    order_description="Holiday Hope Tree Donation",
    timeout=20,
):
    """
    Request a hosted-payment form token for the given amount.

    Returns the token string on success. Raises AuthnetError otherwise.
    """
    if not api_login_id or not transaction_key:
        raise AuthnetError(
            "Authorize.Net API credentials are not configured. Set "
            "AUTHNET_API_LOGIN_ID and AUTHNET_TRANSACTION_KEY."
        )

    amount = normalize_amount(amount)
    payload = build_request_payload(
        api_login_id=api_login_id,
        transaction_key=transaction_key,
        amount=amount,
        return_url=return_url,
        cancel_url=cancel_url,
        order_description=order_description,
    )

    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        api_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except HTTPError as exc:  # pragma: no cover - network failure path
        raise AuthnetError(f"Authorize.Net returned HTTP {exc.code}.")
    except URLError as exc:  # pragma: no cover - network failure path
        raise AuthnetError(f"Could not reach Authorize.Net: {exc.reason}.")

    return parse_token_response(raw)


def parse_token_response(raw_bytes):
    """
    Pull the form token out of a getHostedPaymentPageResponse body.

    Authorize.Net prefixes JSON responses with a UTF-8 BOM, which breaks a
    naive json.loads, so we strip it first.
    """
    text = raw_bytes.decode("utf-8-sig") if isinstance(raw_bytes, (bytes, bytearray)) else raw_bytes
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        raise AuthnetError("Authorize.Net response was not valid JSON.")

    result = body.get("messages", {}).get("resultCode")
    if result != "Ok":
        msgs = body.get("messages", {}).get("message", [])
        detail = "; ".join(
            f"{m.get('code', '')}: {m.get('text', '')}".strip(": ") for m in msgs
        ) or "Unknown error."
        raise AuthnetError(f"Authorize.Net declined the request ({detail}).")

    token = body.get("token")
    if not token:
        raise AuthnetError("Authorize.Net response did not contain a form token.")
    return token
