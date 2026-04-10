from typing import Literal

from pydantic import BaseModel


class GithubAuthSession(BaseModel):
    access_token: str
    token_type: str = "bearer"
    scope: str = ""
    login: str
    user_id: int
    source: Literal["device", "env", "web"] = "device"


class GithubDeviceCode(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int = 5
    verification_uri_complete: str | None = None


class GithubViewer(BaseModel):
    login: str
    user_id: int


class GithubWebSessionStatus(BaseModel):
    authenticated: bool
    configured: bool
    login: str = ""
    user_id: int = 0
