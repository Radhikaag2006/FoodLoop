"""Certificate scans for partner facilities.

Admins upload; anyone can view, because a certificate is a public
credential and the public tracking page links to it. Only PDF, PNG and
JPEG (checked by content, not by file name) up to 5 MB are accepted."""
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import config as C
from ..db import get_db
from ..deps import need
from ..models import Facility, FacilityDoc

router = APIRouter(prefix="/api/facilities")
adm = need("admin")

MAX_BYTES = 5 * 1024 * 1024
KINDS = ((b"%PDF-", "application/pdf", "pdf"),
         (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
         (b"\xff\xd8\xff", "image/jpeg", "jpg"))


def _dir():
    d = os.path.join(C.UPLOAD_DIR, "facility_docs")
    os.makedirs(d, exist_ok=True)
    return d


def _drop(doc):
    try:
        os.remove(os.path.join(_dir(), doc.stored))
    except OSError:
        pass


def _doc(db, fid):
    return db.scalar(select(FacilityDoc).where(FacilityDoc.facility_id == fid))


@router.get("/{fid}/document")
def view(fid: int, db=Depends(get_db)):
    doc = _doc(db, fid)
    path = doc and os.path.join(_dir(), doc.stored)
    if not doc or not os.path.isfile(path):
        raise HTTPException(404, "No certificate has been uploaded.")
    ext = doc.stored.rsplit(".", 1)[-1]
    return FileResponse(
        path, media_type=doc.content_type,
        headers={"Content-Disposition":
                 f'inline; filename="certificate-{fid}.{ext}"',
                 "Cache-Control": "private, no-store"})


@router.post("/{fid}/document")
async def upload(fid: int, file: UploadFile, db=Depends(get_db),
                 u=Depends(adm)):
    if not db.get(Facility, fid):
        raise HTTPException(404, "Facility not found.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "That file is too big. Keep it under 5 MB.")
    kind = next((k for k in KINDS if data.startswith(k[0])), None)
    if not kind:
        raise HTTPException(422, "Upload a PDF, PNG or JPEG file.")
    stored = f"{fid}-{secrets.token_hex(6)}.{kind[2]}"
    with open(os.path.join(_dir(), stored), "wb") as fh:
        fh.write(data)
    name = (file.filename or "certificate")[:120]
    doc = _doc(db, fid)
    if doc:
        _drop(doc)
        doc.stored, doc.content_type = stored, kind[1]
        doc.filename, doc.uploaded_by = name, u.id
    else:
        db.add(FacilityDoc(facility_id=fid, stored=stored, filename=name,
                           content_type=kind[1], uploaded_by=u.id))
    db.commit()
    return {"ok": True, "filename": name}


@router.delete("/{fid}/document")
def remove(fid: int, db=Depends(get_db), u=Depends(adm)):
    doc = _doc(db, fid)
    if doc:
        _drop(doc)
        db.delete(doc)
        db.commit()
    return {"ok": True}
