from pydantic import BaseModel


class SeasonCreate(BaseModel):
    show_id: int
    season_number: int


class SeasonResponse(BaseModel):
    id: int
    show_id: int
    season_number: int

    class Config:
        from_attributes = True