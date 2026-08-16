from pydantic import BaseModel


class ArtworkCreate(BaseModel):
    episode_id: int
    artwork_type: str
    storage_key: str
    width: int
    height: int
    size_bytes: int


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