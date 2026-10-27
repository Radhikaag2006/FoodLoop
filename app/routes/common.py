import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from datetime import date
from typing import Optional
from sqlalchemy import select

from .. import config as C
from ..db import get_db
from ..models import Record
from ..records import record_pdf, verify_record
from ..tiers import (CATALOG, CONDITIONS, TIERS, TIER_ROUTES, classify)

router = APIRouter(prefix="/api")


def _photo(key):
    """URL of a photo for a category, if someone added one."""
    for ext in ("webp", "jpg", "jpeg", "png"):
        if os.path.isfile(os.path.join("static", "img", "items",
                                       f"{key}.{ext}")):
            return f"/static/img/items/{key}.{ext}"
    return ""


def _demo_logins():
    """The demo accounts and their password, sent only when demo mode is on
    (never in production). The website's own files contain none of it."""
    if not C.DEMO_MODE:
        return {"demo_accounts": [], "demo_password": ""}
    keep_admin = not (C.ADMIN_EMAIL and C.ADMIN_PASSWORD)
    return {"demo_password": C.DEMO_PASSWORD,
            "demo_accounts": [list(a) for a in C.DEMO_LOGINS
                              if keep_admin or a[0] != "FoodLoop admin"]}


@router.get("/catalog")
def catalog():
    items = [{"key": k, "label": v["label"], "dated": v["dated"],
              "fixed": v.get("fixed", ""), "image": _photo(k)}
             for k, v in CATALOG.items()]
    return {"items": items, "conditions": CONDITIONS, "tiers": TIERS,
            "routes": TIER_ROUTES,
            "cities": {k: list(v) for k, v in C.CITIES.items()},
            "demo": C.DEMO_MODE,
            # the demo admin exists only while no real admin login is set
            "demo_admin": C.DEMO_MODE and not (
                C.ADMIN_EMAIL and C.ADMIN_PASSWORD),
            **_demo_logins()}


class ClassifyIn(BaseModel):
    item: str
    condition: str = "fresh"
    expiry: Optional[date] = None
    expired: bool = False


@router.post("/classify")
def classify_api(b: ClassifyIn):
    try:
        return classify(b.item, b.condition, b.expiry, expired=b.expired)
    except ValueError as e:
        raise HTTPException(422, str(e))


def _rec(db, code):
    rec = db.scalar(select(Record).where(Record.code == code.upper()))
    if not rec:
        raise HTTPException(404, "No record with that code.")
    return rec


@router.get("/records/{code}")
def record(code: str, db=Depends(get_db)):
    rec = _rec(db, code)
    out = json.loads(rec.payload)
    out.update(verify_record(db, rec))
    out["hash"], out["prev_hash"] = rec.hash, rec.prev_hash
    return out


@router.get("/records/{code}/pdf")
def record_file(code: str, request: Request, db=Depends(get_db)):
    rec = _rec(db, code)
    base = str(request.base_url).rstrip("/")
    return Response(
        record_pdf(rec, base), media_type="application/pdf",
        headers={"Content-Disposition":
                 f'inline; filename="{rec.code}.pdf"'})
