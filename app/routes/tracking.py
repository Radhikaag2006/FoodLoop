from fastapi import APIRouter, Depends, HTTPException, Request

from .. import tracking as T
from ..db import get_db
from ..deps import need
from ..models import Lot
from ..security import rate_limit

router = APIRouter(prefix="/api/track")
biz = need("business")


def _ip(request: Request) -> str:
    return request.client.host if request.client else "?"


@router.get("/lot/{lid}")
def my_lot(lid: int, request: Request, db=Depends(get_db), u=Depends(biz)):
    """The ID and QR of one of the business's own lots."""
    lot = db.get(Lot, lid)
    if not lot or lot.org_id != u.org_id:
        raise HTTPException(404, "Lot not found.")
    code = T.code_for(db, lot.id)
    db.commit()
    return T.qr_for(str(request.base_url), code)


@router.get("/{code}")
def track(code: str, request: Request, db=Depends(get_db)):
    """Public: anyone with the ID (or the QR) can see the journey."""
    rate_limit("track:" + _ip(request), 40, 60)
    lot = T.lot_by_code(db, code)
    if not lot:
        raise HTTPException(404, "No order found with that ID. Check it "
                                 "and try again.")
    return T.view(db, lot)
