from fastapi import FastAPI
from app.api.shows import router as shows_router
from app.api.auth import router as auth_router
from app.api.seasons import router as seasons_router
from app.api.episodes import router as episodes_router
from app.api.artworks import router as artworks_router
from app.api.publish import router as publish_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Peblo TV Mini API",
    version="1.0.0",
)

app.include_router(shows_router)
app.include_router(auth_router)
app.include_router(seasons_router)
app.include_router(episodes_router)
app.include_router(artworks_router)
app.include_router(publish_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "peblo-tv-mini",
    }