from fastapi import FastAPI

app = FastAPI(
    title="Peblo TV Mini API",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "peblo-tv-mini"
    }