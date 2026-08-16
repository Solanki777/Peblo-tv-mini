from fastapi import FastAPI

from app.api.auth import router as auth_router


app = FastAPI(
    title="Peblo TV Mini API",
    version="1.0.0",
)


app.include_router(auth_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "peblo-tv-mini",
    }