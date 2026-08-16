from fastapi import FastAPI
from app.api.shows import router as shows_router
from app.api.auth import router as auth_router
from app.api.seasons import router as seasons_router
from app.api.episodes import router as episodes_router


app = FastAPI(
    title="Peblo TV Mini API",
    version="1.0.0",
)

app.include_router(shows_router)
app.include_router(auth_router)
app.include_router(seasons_router)
app.include_router(episodes_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "peblo-tv-mini",
    }