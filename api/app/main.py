from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app import api, pages
from app.auth import LoginRequired
from app.config import settings
from app.db import engine
from app.rules import RuleViolation
from app.services import NotFound


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Библиотека: выдача книг", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie="library_session")
app.include_router(api.router)
app.include_router(pages.router)


def is_api(request: Request) -> bool:
    return request.url.path.startswith("/api/")


@app.exception_handler(NotFound)
async def not_found(request: Request, exc: NotFound):
    if is_api(request):
        return JSONResponse({"detail": str(exc)}, status_code=404)
    return pages.render(request, "base.html", None, 404, error=f"Не найдено: {exc}")


@app.exception_handler(RuleViolation)
async def rule_violation(request: Request, exc: RuleViolation):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(LoginRequired)
async def login_required(request: Request, exc: LoginRequired):
    return RedirectResponse("/login", status_code=303)


@app.get("/health")
async def health():
    return {"status": "ok"}
