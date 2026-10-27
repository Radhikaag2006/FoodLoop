from datetime import datetime, date
from typing import Optional

from sqlalchemy import ForeignKey, String, Float, Integer, Boolean, Date
from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .clock import utcnow


def now():
    return utcnow()


class Org(Base):
    __tablename__ = "orgs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))  # society|institution|business
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    address: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(40), default="")
    join_code: Mapped[Optional[str]] = mapped_column(
        String(12), unique=True, nullable=True)
    schedule: Mapped[str] = mapped_column(String(160), default="")
    collection_point: Mapped[str] = mapped_column(String(160), default="")
    business_type: Mapped[str] = mapped_column(String(30), default="")
    fssai_no: Mapped[str] = mapped_column(String(20), default="")
    contact_phone: Mapped[str] = mapped_column(String(15), default="")
    # pending|verified|rejected (set by platform admin)
    verify_status: Mapped[str] = mapped_column(String(10), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Flat(Base):
    __tablename__ = "flats"
    __table_args__ = (UniqueConstraint("org_id", "label"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    label: Mapped[str] = mapped_column(String(20))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[Optional[str]] = mapped_column(
        String(120), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(
        String(15), unique=True, nullable=True)
    pw_hash: Mapped[str] = mapped_column(String(200))
    # resident|guard|society_admin|business|hub|admin
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(10), default="active")  # active|pending|rejected|disabled
    org_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orgs.id"), nullable=True)
    flat_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("flats.id"), nullable=True)
    sv: Mapped[int] = mapped_column(Integer, default=1)  # session version
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)


class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    role: Mapped[str] = mapped_column(String(20))  # guard|hub
    org_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orgs.id"), nullable=True)
    note: Mapped[str] = mapped_column(String(80), default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    used_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ResetCode(Base):
    __tablename__ = "reset_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(String(240), default="")
    kind: Mapped[str] = mapped_column(String(20), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Reward(Base):
    __tablename__ = "rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(200), default="")
    cost: Mapped[int] = mapped_column(Integer)
    stock: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Redemption(Base):
    __tablename__ = "redemptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id"))
    title: Mapped[str] = mapped_column(String(80))
    points: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(10), default="requested")  # requested|fulfilled|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    done_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)


class WeighIn(Base):
    __tablename__ = "weighins"
    id: Mapped[int] = mapped_column(primary_key=True)
    flat_id: Mapped[int] = mapped_column(ForeignKey("flats.id"))
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    item: Mapped[str] = mapped_column(String(30))
    condition: Mapped[str] = mapped_column(String(20))
    expired: Mapped[bool] = mapped_column(Boolean, default=False)
    weight_kg: Mapped[float] = mapped_column(Float)
    # accepted|rejected|voided
    status: Mapped[str] = mapped_column(String(12))
    reject_reason: Mapped[str] = mapped_column(String(80), default="")
    tier: Mapped[str] = mapped_column(String(1), default="")
    points: Mapped[int] = mapped_column(Integer, default=0)
    photo: Mapped[str] = mapped_column(String(200), default="")
    pickup_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pickups.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class WalletEntry(Base):
    __tablename__ = "wallet"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    points: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Lot(Base):
    __tablename__ = "lots"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    item: Mapped[str] = mapped_column(String(30))
    condition: Mapped[str] = mapped_column(String(20))
    qty_kg: Mapped[float] = mapped_column(Float)
    expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tier: Mapped[str] = mapped_column(String(1))
    pickup_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pickups.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Facility(Base):
    __tablename__ = "facilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))
    tiers: Mapped[str] = mapped_column(String(10))  # e.g. "B" or "AB"
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    capacity_kg: Mapped[float] = mapped_column(Float)
    certified: Mapped[bool] = mapped_column(Boolean, default=False)
    cert_no: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(15), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # >0 facility pays per kg, <0 gate fee per kg
    rate_per_kg: Mapped[float] = mapped_column(Float, default=0.0)


class Pickup(Base):
    __tablename__ = "pickups"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    status: Mapped[str] = mapped_column(String(12), default="planned")
    expected_kg: Mapped[float] = mapped_column(Float, default=0.0)
    hub_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    facility_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mismatch: Mapped[bool] = mapped_column(Boolean, default=False)
    route_km: Mapped[float] = mapped_column(Float, default=0.0)
    route: Mapped[str] = mapped_column(Text, default="[]")  # json stops
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)


class PickupLine(Base):
    __tablename__ = "pickup_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    pickup_id: Mapped[int] = mapped_column(ForeignKey("pickups.id"))
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    ref_type: Mapped[str] = mapped_column(String(10))  # weighin|lot
    ref_id: Mapped[int] = mapped_column(Integer)
    kg: Mapped[float] = mapped_column(Float)
    tier: Mapped[str] = mapped_column(String(1))


class Tracking(Base):
    """The unique tracking ID (and QR) of a lot, shown to its owner."""
    __tablename__ = "tracking"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), unique=True)
    code: Mapped[str] = mapped_column(String(14), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class RunEvent(Base):
    """When a run reached a stage, so the journey can show real times."""
    __tablename__ = "run_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    pickup_id: Mapped[int] = mapped_column(ForeignKey("pickups.id"))
    kind: Mapped[str] = mapped_column(String(12))  # planned|scheduled|...
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
    by_user: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True)


class CollectorProfile(Base):
    """A collector's vehicle and home base, used to assign runs."""
    __tablename__ = "collector_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    vehicle: Mapped[str] = mapped_column(String(40), default="")
    capacity_kg: Mapped[float] = mapped_column(Float, default=0.0)
    base_lat: Mapped[float] = mapped_column(Float, default=0.0)
    base_lng: Mapped[float] = mapped_column(Float, default=0.0)
    base_label: Mapped[str] = mapped_column(String(60), default="")
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class RunAssignment(Base):
    """Which collector owns a run (NULL = nobody fits, anyone may claim)."""
    __tablename__ = "run_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    pickup_id: Mapped[int] = mapped_column(
        ForeignKey("pickups.id"), unique=True)
    collector_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True)
    declined: Mapped[str] = mapped_column(Text, default="[]")  # json user ids
    fare_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)       # NULL = offered, not yet accepted
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PickupSchedule(Base):
    """Who collects a pickup and when (a 2-hour window from starts_at)."""
    __tablename__ = "pickup_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    pickup_id: Mapped[int] = mapped_column(
        ForeignKey("pickups.id"), unique=True)
    collector_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class FacilityDoc(Base):
    """Scan of a facility's certificate, uploaded by a platform admin."""
    __tablename__ = "facility_docs"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.id"), unique=True)
    filename: Mapped[str] = mapped_column(String(120))
    stored: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(40))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Plan(Base):
    """Price list. All money is stored in paise (1/100 rupee).
    kind=ride:  base_paise per pickup + rates (paise per kg, by tier).
    kind=month: base_paise per month, quota_kg included; kg above the
                quota is billed at the ride plan's per-kg rates."""
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(6))  # ride|month
    base_paise: Mapped[int] = mapped_column(Integer, default=0)
    quota_kg: Mapped[float] = mapped_column(Float, default=0.0)
    rates: Mapped[str] = mapped_column(Text, default="{}")  # json tier->paise
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base):
    """The plan an org is on. A ride plan has no end date."""
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    kg_used: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("org_id", "pickup_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"))
    kind: Mapped[str] = mapped_column(String(6))  # ride|plan
    pickup_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pickups.id"), nullable=True)
    plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("plans.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(160))
    kg: Mapped[float] = mapped_column(Float, default=0.0)
    amount_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(8), default="due")  # due|paid|void
    gateway: Mapped[str] = mapped_column(String(10), default="")
    order_id: Mapped[str] = mapped_column(String(60), default="")
    payment_id: Mapped[str] = mapped_column(String(60), default="")
    # json [{"label": ..., "amount_paise": ...}], the itemised bill
    breakdown: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)


class UpiClaim(Base):
    """A merchant says they paid a ride bill by UPI QR. The money goes
    straight to our UPI ID, so an admin checks it against the bank."""
    __tablename__ = "upi_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id"), unique=True)
    ref: Mapped[str] = mapped_column(String(30), default="")
    state: Mapped[str] = mapped_column(
        String(10), default="claimed")  # claimed|verified|rejected
    claimed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    claimed_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)


class PayPref(Base):
    """How a business prefers to pay its ride bills (no card details are
    ever stored: the gateway collects those)."""
    __tablename__ = "pay_prefs"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), unique=True)
    method: Mapped[str] = mapped_column(String(12))  # upi|card|netbanking
    vpa: Mapped[str] = mapped_column(String(80), default="")


class Record(Base):
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(primary_key=True)
    pickup_id: Mapped[int] = mapped_column(
        ForeignKey("pickups.id"), unique=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    payload: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
