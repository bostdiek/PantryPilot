from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="User's password")
    first_name: str | None = Field(
        default=None, max_length=50, description="User's first name"
    )
    last_name: str | None = Field(
        default=None, max_length=50, description="User's last name"
    )


class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, description="User's email address")
    username: str | None = Field(
        default=None, min_length=3, max_length=50, description="Username"
    )
    password: str | None = Field(
        default=None, min_length=6, description="User's password"
    )
    first_name: str | None = Field(
        default=None, max_length=50, description="User's first name"
    )
    last_name: str | None = Field(
        default=None, max_length=50, description="User's last name"
    )


class UserPublic(UserBase):
    id: UUID = Field(..., description="Unique identifier for the user")

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserBase):
    id: UUID = Field(..., description="Unique identifier for the user")
    hashed_password: str = Field(..., description="Hashed password for the user")
    first_name: str | None = Field(
        default=None, max_length=50, description="User's first name"
    )
    last_name: str | None = Field(
        default=None, max_length=50, description="User's last name"
    )
