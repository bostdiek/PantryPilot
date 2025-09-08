from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserPreferencesBase(BaseModel):
    """Base schema for user preferences."""

    family_size: int = Field(
        default=2, ge=1, le=20, description="Number of people in the household"
    )
    default_servings: int = Field(
        default=4, ge=1, le=50, description="Default servings for new recipes"
    )
    allergies: list[str] = Field(
        default_factory=list, description="List of user allergies"
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list, description="List of dietary restrictions"
    )
    theme: str = Field(
        default="light",
        pattern=r"^(light|dark|system)$",
        description="App theme preference",
    )
    units: str = Field(
        default="imperial",
        pattern=r"^(metric|imperial)$",
        description="Unit system preference",
    )
    meal_planning_days: int = Field(
        default=7, ge=1, le=30, description="Number of days to plan ahead"
    )
    preferred_cuisines: list[str] = Field(
        default_factory=list, description="List of preferred cuisines"
    )

    model_config = ConfigDict(from_attributes=True)


class UserPreferencesCreate(UserPreferencesBase):
    """Schema for creating user preferences."""

    pass


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences - all fields optional."""

    family_size: int | None = Field(
        default=None, ge=1, le=20, description="Number of people in the household"
    )
    default_servings: int | None = Field(
        default=None, ge=1, le=50, description="Default servings for new recipes"
    )
    allergies: list[str] | None = Field(
        default=None, description="List of user allergies"
    )
    dietary_restrictions: list[str] | None = Field(
        default=None, description="List of dietary restrictions"
    )
    theme: str | None = Field(
        default=None,
        pattern=r"^(light|dark|system)$",
        description="App theme preference",
    )
    units: str | None = Field(
        default=None,
        pattern=r"^(metric|imperial)$",
        description="Unit system preference",
    )
    meal_planning_days: int | None = Field(
        default=None, ge=1, le=30, description="Number of days to plan ahead"
    )
    preferred_cuisines: list[str] | None = Field(
        default=None, description="List of preferred cuisines"
    )


class UserPreferencesResponse(UserPreferencesBase):
    """Schema for user preferences response."""

    id: UUID = Field(..., description="Unique identifier for the preferences")
    user_id: UUID = Field(..., description="ID of the user these preferences belong to")

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    """Combined user profile and preferences response."""

    id: UUID = Field(..., description="Unique identifier for the user")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    preferences: UserPreferencesResponse | None = Field(
        default=None, description="User preferences"
    )

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile information."""

    first_name: str | None = Field(
        default=None, max_length=50, description="First name"
    )
    last_name: str | None = Field(default=None, max_length=50, description="Last name")
    username: str | None = Field(
        default=None, min_length=3, max_length=50, description="Username"
    )
