from pydantic import BaseModel


class EpisodeCreate(BaseModel):
    episode_id: str
    season_id: int
    episode_number: int
    title: str
    duration_seconds: int | None = None
    language: str
    content_group: str
    status: str = "draft"


class EpisodeResponse(BaseModel):
    id: int
    episode_id: str
    season_id: int
    episode_number: int
    title: str
    duration_seconds: int | None
    language: str
    content_group: str
    status: str

    class Config:
        from_attributes = True