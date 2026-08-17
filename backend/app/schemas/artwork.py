from pydantic import BaseModel

# FIXED: ArtworkCreate used to let the client hand us width/height/size_bytes
# directly as JSON and we'd just trust it - that's how the endpoint could
# accept artwork "at any size". There's no client-supplied-dimensions path
# anymore: POST /artworks/upload takes the real file and every field below
# is measured from it server-side. See app/services/artwork_validation.py.


class ArtworkResponse(BaseModel):
    id: int
    episode_id: int
    artwork_type: str
    storage_key: str
    width: int
    height: int
    size_bytes: int

    class Config:
        from_attributes = True