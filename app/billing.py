"""Pricing rules: free trial, pay per ride, monthly plans.

All money is in paise. A business gets its first FREE_PICKUPS pickups
free. After that it needs a plan: pay per ride (billed when the pickup
is closed, on the weight the hub confirmed) or a monthly plan with a kg
quota (kg over the quota is billed at the per-ride per-kg rates)."""
import json
import re
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from . import config as C
from .clock import iso, utcnow
from .deps import notify_role
from .models import (Invoice, Org, PayPref, Pickup, PickupLine, Plan,
                     RunAssignment, Subscription, UpiClaim)
from .tiers import TIERS, tier_name

MIN_PAISE = 100        # Razorpay's smallest order is Rs 1

# Rs 50 per pickup + Rs 5 per kg (ASSUMPTION: placeholders). Monthly plans
# are priced to beat pay-per-ride for regular pickups (100 kg in 4 pickups
# is Rs 700 by ride vs Rs 499; 500 kg in 10 pickups is Rs 3,000 vs Rs 1,999).
# Edit them as admin, or in the plans table.
DEFAULT_PLANS = [
    ("ride", "Pay per ride", "ride", 5000, 0.0,
     {"B": 500, "C": 500, "D": 500, "E": 500}),
    ("starter", "Starter, monthly", "month", 49900, 100.0, {}),
    ("growth", "Growth, monthly", "month", 199900, 500.0, {}),
]
# What earlier versions seeded: rows still at one of these are upgraded;
# a price an admin changed is never touched.
OLD_DEFAULTS = {
    "ride": [(5000, 0.0, {"B": 200, "C": 200, "D": 400, "E": 300}),
             (1000, 0.0, {"B": 100, "C": 100, "D": 100, "E": 100})],
    "starter": [(99900, 100.0, {}), (9900, 100.0, {})],
    "growth": [(399900, 500.0, {}), (39900, 500.0, {})],
}


def ensure_plans(db):
    if not db.scalar(select(func.count(Plan.id))):
        for code, name, kind, base, quota, rates in DEFAULT_PLANS:
            db.add(Plan(code=code, name=name, kind=kind, base_paise=base,
                        quota_kg=quota, rates=json.dumps(rates)))
        db.commit()
        return
    for code, name, kind, base, quota, rates in DEFAULT_PLANS:
        row = db.scalar(select(Plan).where(Plan.code == code))
        if not row:
            continue
        cur = {t: v for t, v in json.loads(row.rates).items() if t in TIERS}
        if (row.base_paise, row.quota_kg, cur) in OLD_DEFAULTS[code]:
            row.base_paise, row.rates = base, json.dumps(rates)
    db.commit()


def rupees(paise: int) -> float:
    return round(paise / 100, 2)


def plan_dict(p):
    return {"code": p.code, "name": p.name, "kind": p.kind,
            "base_paise": p.base_paise, "base": rupees(p.base_paise),
            "quota_kg": p.quota_kg, "active": p.active,
            "rates": {t: rupees(v) for t, v in json.loads(p.rates).items()
                      if t in TIERS}}


METHODS = ("upi", "card", "netbanking")
VPA = re.compile(r"^[A-Za-z0-9._\-]{2,64}@[A-Za-z]{2,32}$")


def pay_pref(db, org_id):
    pr = db.scalar(select(PayPref).where(PayPref.org_id == org_id))
    return {"method": pr.method, "vpa": pr.vpa} if pr else None


def set_pay_pref(db, org_id, method, vpa=""):
    vpa = (vpa or "").strip()
    if method not in METHODS:
        raise HTTPException(422, "Choose UPI, card or net banking.")
    if method == "upi" and vpa and not VPA.match(vpa):
        raise HTTPException(
            422, "That UPI ID doesn't look right. It looks like name@bank.")
    pr = db.scalar(select(PayPref).where(PayPref.org_id == org_id))
    if not pr:
        pr = PayPref(org_id=org_id)
        db.add(pr)
    pr.method, pr.vpa = method, vpa if method == "upi" else ""
    db.commit()


def invoice_dict(db, i):
    out = {"lines": json.loads(i.breakdown or "[]"),
           "id": i.id, "kind": i.kind, "description": i.description,
           "kg": round(i.kg, 1), "amount_paise": i.amount_paise,
           "amount": rupees(i.amount_paise), "status": i.status,
           "pickup_id": i.pickup_id, "payment_id": i.payment_id,
           "at": iso(i.created_at), "paid_at": iso(i.paid_at)}
    if i.plan_id:
        out["plan"] = db.get(Plan, i.plan_id).code
    return out


def ride_plan(db):
    return db.scalar(select(Plan).where(Plan.kind == "ride"))


def pickups_started(db, org_id, up_to=None) -> int:
    """How many pickups this org has been part of (its trial counter)."""
    q = select(func.count(func.distinct(PickupLine.pickup_id))).where(
        PickupLine.org_id == org_id)
    if up_to is not None:
        q = q.where(PickupLine.pickup_id <= up_to)
    return db.scalar(q) or 0


def active_sub(db, org_id):
    """The org's current plan, expiring a finished monthly plan."""
    sub = db.scalar(select(Subscription).where(
        Subscription.org_id == org_id, Subscription.active))
    if sub and sub.ends_at and sub.ends_at < utcnow():
        sub.active = False
        db.flush()
        return None
    return sub


def ride_dues(db, org_id):
    return db.scalars(select(Invoice).where(
        Invoice.org_id == org_id, Invoice.kind == "ride",
        Invoice.status == "due").order_by(Invoice.id)).all()


def require_access(db, org_id):
    """Gate for adding lots (HTTP 402 when payment is needed)."""
    if ride_dues(db, org_id):
        raise HTTPException(
            402, "You have an unpaid invoice. Pay it to add more lots.")
    if pickups_started(db, org_id) >= C.FREE_PICKUPS \
            and not active_sub(db, org_id):
        raise HTTPException(
            402, "Your free trial is over. Choose a plan to continue.")


def _lines(kg_by_tier, rates, base, share=1.0):
    """The itemised bill: pickup fee, then each waste type by weight."""
    out = []
    if base:
        out.append({"label": "Pickup fee", "amount_paise": base})
    for t in sorted(kg_by_tier):
        kg, r = kg_by_tier[t] * share, rates.get(t, 0)
        if kg and r:
            out.append({"label": f"{tier_name(t)}, {kg:.1f} kg × "
                                 f"₹{r / 100:g}/kg",
                        "amount_paise": round(kg * r)})
    return out


def _fit(lines, amount):
    """Make the lines add up to the amount actually charged."""
    gap = amount - sum(x["amount_paise"] for x in lines)
    if gap:
        lines.append({"label": "Minimum charge / rounding",
                      "amount_paise": gap})
    return lines


def _amount(kg_by_tier, rates, base):
    amt = base + sum(kg * rates.get(t, 0) for t, kg in kg_by_tier.items())
    amt = round(amt)
    return max(amt, MIN_PAISE) if amt > 0 else 0


def charge_pickup(db, p: Pickup):
    """Bill every business on a pickup that was just closed."""
    lines = db.scalars(select(PickupLine).where(
        PickupLine.pickup_id == p.id)).all()
    scale = p.hub_kg / p.expected_kg if p.expected_kg and p.hub_kg else 1.0
    by_org = {}
    for ln in lines:
        by_org.setdefault(ln.org_id, []).append(ln)
    ride = ride_plan(db)
    rates = json.loads(ride.rates)
    for org_id, ls in by_org.items():
        if pickups_started(db, org_id, p.id) <= C.FREE_PICKUPS:
            continue                                   # still on the trial
        if db.scalar(select(Invoice.id).where(
                Invoice.org_id == org_id, Invoice.pickup_id == p.id)):
            continue
        kg_by_tier = {}
        for ln in ls:
            kg_by_tier[ln.tier] = kg_by_tier.get(ln.tier, 0) + ln.kg * scale
        kg = sum(kg_by_tier.values())
        sub = active_sub(db, org_id)
        plan = db.get(Plan, sub.plan_id) if sub else None
        if plan and plan.kind == "month":
            room = max(0.0, plan.quota_kg - sub.kg_used)
            over = max(0.0, kg - room)
            sub.kg_used += kg
            full = _amount(kg_by_tier, rates, 0)
            amt = round(full * over / kg) if kg else 0
            if 0 < amt < MIN_PAISE:
                amt = MIN_PAISE
            what = (f"{plan.name}: covered by your plan" if not amt else
                    f"{plan.name}: {over:.1f} kg over your quota")
            lines = [{"label": f"{kg:.1f} kg within your {plan.name} plan"
                      if not amt else f"{kg - over:.1f} kg within your "
                      f"{plan.name} plan", "amount_paise": 0}]
            if amt:
                lines += _fit(_lines(kg_by_tier, rates, 0,
                                     over / kg if kg else 0), amt)
        else:
            amt = _amount(kg_by_tier, rates, ride.base_paise)
            what = "Pay per ride"
            lines = _fit(_lines(kg_by_tier, rates, ride.base_paise), amt)
        inv = Invoice(
            org_id=org_id, kind="ride", pickup_id=p.id, kg=kg,
            description=f"Pickup #{p.id} · {what}", amount_paise=amt,
            breakdown=json.dumps(lines),
            status="due" if amt else "paid", gateway="" if amt else "plan",
            paid_at=None if amt else utcnow())
        db.add(inv)
        if amt:
            notify_role(db, "business", "New invoice",
                        f"Pickup #{p.id}: Rs {rupees(amt):.2f} to pay.",
                        org_id=org_id, kind="info")


def select_plan(db, org_id, code):
    """Returns the invoice to pay (monthly plan) or None (ride plan)."""
    plan = db.scalar(select(Plan).where(Plan.code == code, Plan.active))
    if not plan:
        raise HTTPException(404, "That plan isn't available.")
    cur = active_sub(db, org_id)
    if plan.kind == "ride":
        if not pay_pref(db, org_id):
            raise HTTPException(
                409, "Choose how you'll pay before turning on pay per ride.")
        if cur and db.get(Plan, cur.plan_id).kind == "month":
            raise HTTPException(
                409, "Your monthly plan runs until "
                f"{cur.ends_at:%d %b}. You can switch after that.")
        if cur:
            cur.active = False
        db.add(Subscription(org_id=org_id, plan_id=plan.id))
        db.commit()
        return None
    if cur and db.get(Plan, cur.plan_id).kind == "month":
        raise HTTPException(409, "You already have a monthly plan.")
    for old in db.scalars(select(Invoice).where(
            Invoice.org_id == org_id, Invoice.kind == "plan",
            Invoice.status == "due")):
        old.status = "void"
    inv = Invoice(org_id=org_id, kind="plan", plan_id=plan.id,
                  description=f"{plan.name} · {C.PLAN_DAYS} days, "
                  f"{plan.quota_kg:g} kg included",
                  amount_paise=plan.base_paise,
                  breakdown=json.dumps([{
                      "label": f"{plan.name}, {C.PLAN_DAYS} days "
                               f"({plan.quota_kg:g} kg included)",
                      "amount_paise": plan.base_paise}]))
    db.add(inv)
    db.commit()
    return inv


def mark_paid(db, inv, payment_id, gateway):
    if inv.status == "paid":
        return
    inv.status, inv.payment_id = "paid", payment_id
    inv.gateway, inv.paid_at = gateway, utcnow()
    if inv.kind == "plan":
        for s in db.scalars(select(Subscription).where(
                Subscription.org_id == inv.org_id, Subscription.active)):
            s.active = False
        db.add(Subscription(
            org_id=inv.org_id, plan_id=inv.plan_id,
            ends_at=utcnow() + timedelta(days=C.PLAN_DAYS)))
    notify_role(db, "business", "Payment received",
                f"Rs {rupees(inv.amount_paise):.2f}: {inv.description}",
                org_id=inv.org_id, kind="info")
    db.commit()


REF = re.compile(r"^[A-Za-z0-9]{6,30}$")


def claim_upi(db, inv, user, ref=""):
    """A merchant paid a ride bill through the UPI QR."""
    if inv.kind != "ride" or inv.status != "due":
        raise HTTPException(409, "There's nothing to pay on this bill.")
    ref = (ref or "").strip()
    if ref and not REF.match(ref):
        raise HTTPException(
            422, "That reference doesn't look right. Use the 12-digit UPI "
                 "reference (UTR) from your payment app, or leave it blank.")
    old = db.scalar(select(UpiClaim).where(UpiClaim.invoice_id == inv.id))
    if old:                       # claimed before and rejected: try again
        old.ref, old.state, old.claimed_by = ref, "claimed", user.id
        old.claimed_at, old.checked_at = utcnow(), None
    else:
        db.add(UpiClaim(invoice_id=inv.id, ref=ref, claimed_by=user.id))
    mark_paid(db, inv, "UPI-" + (ref or f"INV{inv.id}"), "upi_qr")


def upi_pending(db):
    """UPI payments waiting for an admin to match against the bank."""
    rows = db.scalars(select(UpiClaim).where(UpiClaim.state == "claimed")
                      .order_by(UpiClaim.id)).all()
    names = {o.id: o.name for o in db.scalars(select(Org))}
    out = []
    for c in rows:
        i = db.get(Invoice, c.invoice_id)
        out.append({"invoice_id": i.id, "org": names.get(i.org_id, ""),
                    "description": i.description, "ref": c.ref,
                    "amount_paise": i.amount_paise,
                    "amount": rupees(i.amount_paise), "at": iso(c.claimed_at)})
    return out


def check_upi(db, invoice_id, received):
    c = db.scalar(select(UpiClaim).where(
        UpiClaim.invoice_id == invoice_id, UpiClaim.state == "claimed"))
    if not c:
        raise HTTPException(404, "Nothing waiting to be checked.")
    inv = db.get(Invoice, invoice_id)
    c.checked_at = utcnow()
    if received:
        c.state = "verified"
    else:                              # not in the bank: the bill is due again
        c.state = "rejected"
        inv.status, inv.paid_at, inv.payment_id = "due", None, ""
        inv.gateway = ""
        notify_role(db, "business", "Payment not received",
                    f"We couldn't find your UPI payment for pickup "
                    f"#{inv.pickup_id}. Please pay Rs "
                    f"{rupees(inv.amount_paise):.2f} again.",
                    org_id=inv.org_id, kind="warn")
    db.commit()


def status(db, org_id):
    n = pickups_started(db, org_id)
    sub = active_sub(db, org_id)
    plan = db.get(Plan, sub.plan_id) if sub else None
    dues = ride_dues(db, org_id)
    pending_plan = db.scalar(select(Invoice).where(
        Invoice.org_id == org_id, Invoice.kind == "plan",
        Invoice.status == "due").order_by(Invoice.id.desc()))
    try:
        require_access(db, org_id)
        can_add, reason = True, ""
    except HTTPException as e:
        can_add, reason = False, e.detail
    return {
        "trial": {"total": C.FREE_PICKUPS, "pickups": n,
                  "left": max(0, C.FREE_PICKUPS - n)},
        "plan": {**plan_dict(plan), "since": iso(sub.started_at),
                 "ends": iso(sub.ends_at),
                 "kg_used": round(sub.kg_used, 1)} if plan else None,
        "pay_pref": pay_pref(db, org_id),
        "dues": [invoice_dict(db, i) for i in dues],
        "due_paise": sum(i.amount_paise for i in dues),
        "pending_plan": invoice_dict(db, pending_plan)
        if pending_plan else None,
        "can_add": can_add, "reason": reason,
        "plans": [plan_dict(p) for p in db.scalars(
            select(Plan).where(Plan.active).order_by(Plan.id))],
        "tiers": TIERS,
    }


def admin_summary(db):
    paid = db.scalars(select(Invoice).where(
        Invoice.status == "paid", Invoice.amount_paise > 0)).all()
    due = db.scalars(select(Invoice).where(Invoice.status == "due")).all()
    recent = db.scalars(select(Invoice).order_by(Invoice.id.desc())
                        .limit(30)).all()
    fares = db.scalars(select(RunAssignment.fare_paise).join(
        Pickup, Pickup.id == RunAssignment.pickup_id).where(
        Pickup.status == "closed",
        RunAssignment.fare_paise.is_not(None))).all()
    names = {o.id: o.name for o in db.scalars(select(Org))}
    return {
        "paid": rupees(sum(i.amount_paise for i in paid)),
        "paid_count": len(paid),
        "upi_pending": upi_pending(db),
        "driver_cost": rupees(sum(fares)), "driver_runs": len(fares),
        "due": rupees(sum(i.amount_paise for i in due)),
        "due_count": len(due),
        "active_monthly": db.scalar(
            select(func.count(Subscription.id)).join(
                Plan, Plan.id == Subscription.plan_id).where(
                Subscription.active, Plan.kind == "month")) or 0,
        "recent": [{**invoice_dict(db, i), "org": names.get(i.org_id, "")}
                   for i in recent],
        "plans": [plan_dict(p) for p in db.scalars(
            select(Plan).order_by(Plan.id))],
    }
