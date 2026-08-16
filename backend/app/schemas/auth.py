from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "editor"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True