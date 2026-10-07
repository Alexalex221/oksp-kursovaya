from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app import api
from app.config import settings

app = FastAPI(title="Библиотека: выдача книг")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie="library_session")
app.include_router(api.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
