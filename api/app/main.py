from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app import api
from app.config import settings
from app.rules import RuleViolation
from app.services import NotFound

app = FastAPI(title="Библиотека: выдача книг")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie="library_session")
app.include_router(api.router)


@app.exception_handler(NotFound)
async def not_found(request: Request, exc: NotFound):
    return JSONResponse({"detail": str(exc)}, status_code=404)


@app.exception_handler(RuleViolation)
async def rule_violation(request: Request, exc: RuleViolation):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.get("/health")
async def health():
    return {"status": "ok"}
