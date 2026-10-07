from fastapi import FastAPI

app = FastAPI(title="Библиотека: выдача книг")


@app.get("/health")
async def health():
    return {"status": "ok"}
