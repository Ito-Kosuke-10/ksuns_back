from pydantic import BaseModel


class GoogleUrlResponse(BaseModel):
    auth_url: str


class UserInfo(BaseModel):
    id: int
    email: str
    display_name: str


class AuthTokensResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
