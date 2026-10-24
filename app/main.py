import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import config as C
from .routes import admin, auth, business, common, hub
from .seed import init

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    init()
    yield


app = FastAPI(title="FoodLoop", lifespan=lifespan, docs_url=None,
              redoc_url=None, openapi_url=None)

CSP = ("default-src 'self'; img-src 'self' data: blob: "
       "https://*.tile.openstreetmap.org https://tile.openstreetmap.org; "
       "style-src 'self' 'unsafe-inline'; script-src 'self'; "
       "font-src 'self'; connect-src 'self'; media-src 'self' blob:; "
       "worker-src 'self'; manifest-src 'self'; frame-ancestors 'none'; "
       "base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def guard_and_headers(request: Request, call_next):
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin = request.headers.get("origin")
        if origin:
            host = request.headers.get(
                "x-forwarded-host") or request.headers.get("host", "")
            if origin.split("://", 1)[-1] != host:
                return JSONResponse(
                    {"detail": "Request blocked."}, status_code=403)
    resp = await call_next(request)
    h = resp.headers
    h["Content-Security-Policy"] = CSP
    h["X-Content-Type-Options"] = "nosniff"
    h["Referrer-Policy"] = "same-origin"
    h["Permissions-Policy"] = "camera=(self), geolocation=(self)"
    if C.IS_PROD:
        h["Strict-Transport-Security"] = "max-age=31536000"
    if request.url.path.startswith("/api/"):
        h["Cache-Control"] = "no-store"
    elif request.url.path.startswith("/static/") and not C.IS_PROD:
        h["Cache-Control"] = "no-cache"
    return resp


app.add_middleware(SessionMiddleware, secret_key=C.SECRET_KEY,
                   same_site="lax", https_only=C.IS_PROD,
                   max_age=C.SESSION_DAYS * 86400, session_cookie="fl")


@app.exception_handler(RequestValidationError)
async def bad_input(request, exc):
    e = exc.errors()[0]
    field = ".".join(str(x) for x in e["loc"] if x != "body")
    return JSONResponse(
        {"detail": f"Check “{field}”: {e['msg']}".replace(
            "Field required", "this is required")}, status_code=422)


for r in (auth, common, business, hub, admin):
    app.include_router(r.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/sw.js", include_in_schema=False)
def sw():
    return FileResponse("static/sw.js", media_type="text/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse("static/manifest.json",
                        media_type="application/manifest+json")


@app.get("/", include_in_schema=False)
@app.get("/verify/{code}", include_in_schema=False)
def shell(code: str = ""):
    return FileResponse("templates/app.html", media_type="text/html",
                        headers={"Cache-Control": "no-cache"})
