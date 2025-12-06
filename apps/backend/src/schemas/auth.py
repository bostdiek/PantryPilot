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


class RegisterResponse(BaseModel):
    """Response model for registration (no token, just confirmation)."""

    message: str = Field(
        ..., description="Confirmation message about email verification"
    )
    email: str = Field(..., description="Email address to verify")


class VerifyEmailRequest(BaseModel):
    """Request model for email verification."""

    token: str = Field(..., description="Email verification token from the link")


class VerifyEmailResponse(BaseModel):
    """Response model for successful email verification."""

    message: str = Field(..., description="Success message")
    access_token: str = Field(..., description="Access token for authentication")
    token_type: str = Field(default="bearer", description="Type of the token")


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""

    email: EmailStr = Field(..., description="Email address for password reset")


class ForgotPasswordResponse(BaseModel):
    """Response model for forgot password."""

    message: str = Field(
        ..., description="Confirmation that reset email was sent if account exists"
    )


class ResetPasswordRequest(BaseModel):
    """Request model for password reset."""

    token: str = Field(..., description="Password reset token from the email link")
    new_password: str = Field(
        ...,
        min_length=12,
        description="New password with minimum length of 12 characters",
    )


class ResetPasswordResponse(BaseModel):
    """Response model for successful password reset."""

    message: str = Field(..., description="Success message")
