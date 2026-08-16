from pydantic import BaseModel


class ShowCreate(BaseModel):
    title: str
    slug: str
    section: str | None = None
    synopsis: str | None = None
    categories: str = ""


class ShowResponse(BaseModel):
    id: int
    title: str
    slug: str
    section: str | None
    synopsis: str | None
    categories: str

    class Config:
        from_attributes = True