from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str = Field(..., description="Access token for authentication")
    token_type: str = Field(..., description="Type of the token, e.g., 'bearer'")


class TokenData(BaseModel):
    sub: str | None = Field(
        default=None,
        description="Subject (user identifier) of the token",
    )
    scopes: list[str] = Field(
        default_factory=list,
        description="Scopes/permissions associated with the token",
    )


class LoginResponse(Token):
    """Response model for login, extending Token with user info."""

    user_id: str = Field(..., description="Unique identifier for the user")
    email: str = Field(..., description="Email of the authenticated user")


class UserRegister(BaseModel):
    """Schema for user registration."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_\-]{3,32}$",
        description="Username (3-32 chars, alphanumeric, underscore, hyphen)",
    )
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(
        ...,
        min_length=12,
        description="Password with minimum length of 12 characters",
    )
    first_name: str | None = Field(
        default=None, max_length=50, description="Optional first name"
    )
    last_name: str | None = Field(
        default=None, max_length=50, description="Optional last name"
    )
