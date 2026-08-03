from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    device_name: str | None = Field(default=None, max_length=160)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    roles: list[str]


class OtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class OtpVerifyRequest(OtpRequest):
    otp: str = Field(min_length=4, max_length=8)
    display_name: str | None = Field(default=None, max_length=160)
