from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class URLCreate(BaseModel):
    original_url: str
    custom_code: str | None = None

class URLOut(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int = 0
    model_config = {"from_attributes": True}

class StatsOut(BaseModel):
    url_id: int
    short_code: str
    original_url: str
    total_clicks: int
    clicks_by_date: dict[str, int]
