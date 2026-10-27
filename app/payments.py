"""Payment gateway: Razorpay in TEST mode, or a built-in simulator.

Safety rules (nobody is ever billed by accident):
  * keys starting rzp_live_ are refused unless ALLOW_LIVE_PAYMENTS=1;
  * with no keys the simulator is used, and only outside production.
The amount always comes from our own invoice, never from the browser."""
import hmac
import hashlib
import secrets
from urllib.parse import quote, urlencode

import httpx
import segno
from fastapi import HTTPException

from . import config as C

ORDERS_URL = "https://api.razorpay.com/v1/orders"


def mode() -> str:
    """razorpay | mock | off"""
    kid, sec = C.RAZORPAY_KEY_ID, C.RAZORPAY_KEY_SECRET
    if kid and sec:
        if kid.startswith("rzp_live_") and not C.ALLOW_LIVE_PAYMENTS:
            return "off"
        if not kid.startswith(("rzp_test_", "rzp_live_")):
            return "off"
        return "razorpay"
    return "off" if C.IS_PROD else "mock"


def public_config() -> dict:
    m = mode()
    return {"mode": m,
            "key_id": C.RAZORPAY_KEY_ID if m == "razorpay" else "",
            "test": not C.RAZORPAY_KEY_ID.startswith("rzp_live_")}


def _need_ready():
    if mode() == "off":
        raise HTTPException(
            503, "Payments aren't set up yet. Please try again later.")


def create_order(amount_paise: int, receipt: str, notes: dict) -> str:
    _need_ready()
    if mode() == "mock":
        return "order_sim_" + secrets.token_hex(8)
    try:
        r = httpx.post(
            ORDERS_URL, auth=(C.RAZORPAY_KEY_ID, C.RAZORPAY_KEY_SECRET),
            json={"amount": int(amount_paise), "currency": "INR",
                  "receipt": receipt[:40], "notes": notes}, timeout=15)
    except httpx.HTTPError:
        raise HTTPException(502, "Couldn't reach the payment service.")
    if r.status_code != 200:
        raise HTTPException(502, "The payment service refused the order.")
    return r.json()["id"]


def signature(order_id: str, payment_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(),
                    hashlib.sha256).hexdigest()


def verify(order_id: str, payment_id: str, sig: str) -> bool:
    """Razorpay Checkout signs `order_id|payment_id` with the key secret."""
    if mode() != "razorpay":
        return False
    good = signature(order_id, payment_id, C.RAZORPAY_KEY_SECRET)
    return hmac.compare_digest(good, sig or "")


DEMO_VPA = "foodloop.demo@upi"


def upi_payload(amount_paise: int, ref: str, note: str):
    """UPI QR for a fixed amount, or None when it can't be offered.

    Without UPI_VPA a demo ID is used (never in production): scanning it
    with a real UPI app fails, so no money can move by accident."""
    demo = not C.UPI_VPA
    if demo and C.IS_PROD:
        return None
    vpa = C.UPI_VPA or DEMO_VPA
    q = urlencode({"pa": vpa, "pn": C.UPI_NAME,
                   "am": f"{amount_paise / 100:.2f}", "cu": "INR",
                   "tn": note[:50], "tr": ref[:35]}, quote_via=quote)
    uri = "upi://pay?" + q
    return {"uri": uri, "vpa": vpa, "name": C.UPI_NAME, "demo": demo,
            "amount": round(amount_paise / 100, 2),
            "qr": segno.make(uri, error="m").svg_data_uri(
                scale=6, border=2)}
