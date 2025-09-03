from pydantic import BaseModel, Field


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
