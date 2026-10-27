import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from .. import billing as B
from .. import payments as P
from ..db import get_db
from ..deps import need
from ..models import Invoice, Org, Plan
from ..security import rate_limit
from ..tiers import TIERS

router = APIRouter(prefix="/api/billing")
biz = need("business")
adm = need("admin")


def _mine(db, u, iid):
    inv = db.get(Invoice, iid)
    if not inv or inv.org_id != u.org_id:
        raise HTTPException(404, "Invoice not found.")
    return inv


@router.get("/status")
def status(db=Depends(get_db), u=Depends(biz)):
    out = B.status(db, u.org_id)
    out["gateway"] = P.public_config()
    db.commit()                      # status() may expire a finished plan
    return out


@router.get("/invoices")
def invoices(db=Depends(get_db), u=Depends(biz)):
    rows = db.scalars(select(Invoice).where(
        Invoice.org_id == u.org_id, Invoice.status != "void")
        .order_by(Invoice.id.desc()).limit(50)).all()
    return [B.invoice_dict(db, i) for i in rows]


class MethodIn(BaseModel):
    method: str
    vpa: str = ""


@router.put("/method")
def set_method(b: MethodIn, db=Depends(get_db), u=Depends(biz)):
    B.set_pay_pref(db, u.org_id, b.method, b.vpa)
    return {"pay_pref": B.pay_pref(db, u.org_id)}


@router.post("/plans/{code}/select")
def select_plan(code: str, db=Depends(get_db), u=Depends(biz)):
    inv = B.select_plan(db, u.org_id, code)
    return {"invoice": B.invoice_dict(db, inv) if inv else None}


@router.post("/invoices/{iid}/order")
def make_order(iid: int, request: Request, db=Depends(get_db),
               u=Depends(biz)):
    rate_limit(f"order:{u.id}", 20, 600)
    inv = _mine(db, u, iid)
    if inv.status != "due" or inv.amount_paise <= 0:
        raise HTTPException(409, "Nothing to pay on this invoice.")
    inv.order_id = P.create_order(
        inv.amount_paise, f"inv_{inv.id}",
        {"invoice": str(inv.id), "org": str(inv.org_id)})
    inv.gateway = P.mode()
    db.commit()
    org = db.get(Org, u.org_id)
    pref = B.pay_pref(db, u.org_id) or {}
    prefill = {"name": u.name, "contact": u.phone or "",
               "email": u.email or ""}
    if pref.get("method"):            # open the payment window on it
        prefill["method"] = pref["method"]
        if pref.get("vpa"):
            prefill["vpa"] = pref["vpa"]
    return {"order_id": inv.order_id, "amount_paise": inv.amount_paise,
            "currency": "INR", "name": "FoodLoop",
            "description": inv.description, "method": pref.get("method", ""),
            "vpa": pref.get("vpa", ""), "prefill": prefill,
            "org": org.name, **P.public_config()}


class VerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/invoices/{iid}/verify")
def verify(iid: int, b: VerifyIn, db=Depends(get_db), u=Depends(biz)):
    rate_limit(f"verify:{u.id}", 20, 600)
    inv = _mine(db, u, iid)
    if inv.status == "paid":
        return {"ok": True}
    if not inv.order_id or inv.order_id != b.razorpay_order_id:
        raise HTTPException(400, "That payment doesn't match this invoice.")
    if not P.verify(b.razorpay_order_id, b.razorpay_payment_id,
                    b.razorpay_signature):
        raise HTTPException(400, "We couldn't confirm that payment.")
    B.mark_paid(db, inv, b.razorpay_payment_id, "razorpay")
    return {"ok": True}


@router.get("/invoices/{iid}/upi")
def upi_qr(iid: int, db=Depends(get_db), u=Depends(biz)):
    """The UPI QR (with the amount filled in) for a ride bill."""
    inv = _mine(db, u, iid)
    if inv.kind != "ride" or inv.status != "due" or inv.amount_paise <= 0:
        raise HTTPException(409, "There's nothing to pay on this bill.")
    up = P.upi_payload(inv.amount_paise, f"FL{inv.id}",
                       f"FoodLoop pickup {inv.pickup_id}")
    if not up:
        raise HTTPException(
            503, "UPI QR isn't set up yet. Please pay another way.")
    return {"upi": up, "amount_paise": inv.amount_paise,
            "amount": B.rupees(inv.amount_paise)}


class UpiPaidIn(BaseModel):
    ref: str = ""


@router.post("/invoices/{iid}/upi-paid")
def upi_paid(iid: int, b: UpiPaidIn, db=Depends(get_db), u=Depends(biz)):
    rate_limit(f"upipaid:{u.id}", 20, 600)
    B.claim_upi(db, _mine(db, u, iid), u, b.ref)
    return {"ok": True}


@router.post("/invoices/{iid}/simulate-pay")
def simulate_pay(iid: int, db=Depends(get_db), u=Depends(biz)):
    """Built-in test gateway (only when no Razorpay keys are set)."""
    if P.mode() != "mock":
        raise HTTPException(404, "Not available.")
    inv = _mine(db, u, iid)
    if inv.status != "due" or not inv.order_id.startswith("order_sim_"):
        raise HTTPException(409, "Start the payment first.")
    B.mark_paid(db, inv, "pay_sim_" + inv.order_id[-8:], "mock")
    return {"ok": True}


# ---------- admin ----------
@router.get("/admin/summary")
def admin_summary(db=Depends(get_db), u=Depends(adm)):
    return B.admin_summary(db)


@router.post("/admin/upi/{iid}/{verdict}")
def check_upi(iid: int, verdict: str, db=Depends(get_db), u=Depends(adm)):
    if verdict not in ("verify", "reject"):
        raise HTTPException(404, "Not found.")
    B.check_upi(db, iid, verdict == "verify")
    return {"ok": True}


class PlanIn(BaseModel):
    name: str
    base_paise: int
    quota_kg: float = 0.0
    rates: dict[str, int] = {}
    active: bool = True


@router.put("/admin/plans/{code}")
def edit_plan(code: str, b: PlanIn, db=Depends(get_db), u=Depends(adm)):
    p = db.scalar(select(Plan).where(Plan.code == code))
    if not p:
        raise HTTPException(404, "Plan not found.")
    if not (0 <= b.base_paise <= 10_000_000) or b.quota_kg < 0:
        raise HTTPException(422, "Check the price and quota.")
    if any(t not in TIERS or not (0 <= v <= 100_000)
           for t, v in b.rates.items()):
        raise HTTPException(422, "Check the per-kg rates.")
    p.name = b.name.strip()[:60] or p.name
    p.base_paise, p.quota_kg, p.active = b.base_paise, b.quota_kg, b.active
    if p.kind == "ride":
        p.rates = json.dumps({t: int(v) for t, v in b.rates.items()})
    db.commit()
    return {"ok": True}
