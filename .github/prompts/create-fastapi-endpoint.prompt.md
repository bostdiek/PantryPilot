---
description: "Create a new FastAPI endpoint with proper patterns, validation, and testing"
mode: "agent"
tools: ['changes', 'codebase', 'editFiles', 'extensions', 'fetch', 'findTestFiles', 'githubRepo', 'new', 'openSimpleBrowser', 'problems', 'runCommands', 'runNotebooks', 'runTasks', 'runTests', 'search', 'searchResults', 'terminalLastCommand', 'terminalSelection', 'testFailure', 'usages', 'vscodeAPI', 'context7', 'sequentialthinking', 'pylance mcp server']
---

# Create FastAPI Endpoint

Generate a complete FastAPI endpoint following PantryPilot backend patterns and best practices.

## Context

You are working in the PantryPilot backend (`apps/backend/`), which uses:

- **FastAPI**: 0.116.1+ with dependency injection
- **Python**: 3.12+ with modern async patterns
- **uv**: For package management
- **Pydantic**: For request/response validation
- **SQLAlchemy**: For database operations (async)
- **Alembic**: For database migrations

## Requirements

When creating a new FastAPI endpoint, include:

1. **Pydantic Models**: Request and response schemas with proper validation
2. **Router Implementation**: Properly structured API router with versioning
3. **Database Operations**: CRUD functions with async SQLAlchemy
4. **Error Handling**: Appropriate HTTP exceptions and status codes
5. **Type Hints**: Complete type annotations for all functions
6. **Documentation**: Docstrings and OpenAPI metadata
7. **Tests**: Unit tests with pytest and proper mocking

## Template Structure

### 1. Pydantic Schemas (`schemas/`)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class {Entity}Base(BaseModel):
    """Base schema for {entity} data."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class {Entity}Create({Entity}Base):
    """Schema for creating a new {entity}."""
    pass

class {Entity}Update(BaseModel):
    """Schema for updating an existing {entity}."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class {Entity}Response({Entity}Base):
    """Schema for {entity} API responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### 2. Database Models (`models/`)

```python
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class {Entity}(Base):
    """Database model for {entity}."""
    __tablename__ = "{entities}"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### 3. CRUD Operations (`crud/`)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from fastapi import HTTPException, status

async def create_{entity}(
    db: AsyncSession,
    {entity}_data: {Entity}Create
) -> {Entity}:
    """Create a new {entity}."""
    db_{entity} = {Entity}(**{entity}_data.model_dump())
    db.add(db_{entity})
    try:
        await db.commit()
        await db.refresh(db_{entity})
        return db_{entity}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="{Entity} with this name already exists"
        )

async def get_{entity}(db: AsyncSession, {entity}_id: int) -> Optional[{Entity}]:
    """Get a {entity} by ID."""
    result = await db.execute(select({Entity}).where({Entity}.id == {entity}_id))
    return result.scalar_one_or_none()

async def get_{entities}(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[{Entity}]:
    """Get multiple {entities} with pagination."""
    result = await db.execute(
        select({Entity}).offset(skip).limit(limit).order_by({Entity}.name)
    )
    return result.scalars().all()

async def update_{entity}(
    db: AsyncSession,
    {entity}_id: int,
    {entity}_data: {Entity}Update
) -> Optional[{Entity}]:
    """Update an existing {entity}."""
    db_{entity} = await get_{entity}(db, {entity}_id)
    if not db_{entity}:
        return None

    update_data = {entity}_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_{entity}, field, value)

    await db.commit()
    await db.refresh(db_{entity})
    return db_{entity}

async def delete_{entity}(db: AsyncSession, {entity}_id: int) -> bool:
    """Delete a {entity}."""
    db_{entity} = await get_{entity}(db, {entity}_id)
    if not db_{entity}:
        return False

    await db.delete(db_{entity})
    await db.commit()
    return True
```

### 4. API Router (`api/v1/`)

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Annotated
from dependencies import get_db
from crud import {entity}_crud
from schemas import {Entity}Create, {Entity}Update, {Entity}Response

router = APIRouter(prefix="/{entities}", tags=["{entities}"])

@router.post(
    "/",
    response_model={Entity}Response,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new {entity}",
    description="Create a new {entity} with the provided data."
)
async def create_{entity}(
    {entity}_data: {Entity}Create,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> {Entity}Response:
    """Create a new {entity}."""
    return await {entity}_crud.create_{entity}(db, {entity}_data)

@router.get(
    "/",
    response_model=List[{Entity}Response],
    summary="Get all {entities}",
    description="Retrieve a list of {entities} with optional pagination."
)
async def get_{entities}(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends()
) -> List[{Entity}Response]:
    """Get all {entities} with pagination."""
    return await {entity}_crud.get_{entities}(db, skip=skip, limit=limit)

@router.get(
    "/{{{entity}_id}}",
    response_model={Entity}Response,
    summary="Get a {entity} by ID",
    description="Retrieve a specific {entity} by its ID."
)
async def get_{entity}(
    {entity}_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> {Entity}Response:
    """Get a {entity} by ID."""
    {entity} = await {entity}_crud.get_{entity}(db, {entity}_id)
    if not {entity}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{Entity} not found"
        )
    return {entity}

@router.patch(
    "/{{{entity}_id}}",
    response_model={Entity}Response,
    summary="Update a {entity}",
    description="Update an existing {entity} with the provided data."
)
async def update_{entity}(
    {entity}_id: int,
    {entity}_data: {Entity}Update,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> {Entity}Response:
    """Update a {entity}."""
    {entity} = await {entity}_crud.update_{entity}(db, {entity}_id, {entity}_data)
    if not {entity}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{Entity} not found"
        )
    return {entity}

@router.delete(
    "/{{{entity}_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a {entity}",
    description="Delete a {entity} by ID."
)
async def delete_{entity}(
    {entity}_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a {entity}."""
    deleted = await {entity}_crud.delete_{entity}(db, {entity}_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{Entity} not found"
        )
```

### 5. Tests (`tests/`)

```python
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from main import app

class Test{Entity}API:
    """Test {entity} API endpoints."""

    @pytest.mark.asyncio
    async def test_create_{entity}(self, async_client: AsyncClient):
        """Test creating a new {entity}."""
        {entity}_data = {
            "name": "Test {Entity}",
            "description": "Test description"
        }

        response = await async_client.post("/api/v1/{entities}/", json={entity}_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == {entity}_data["name"]
        assert data["description"] == {entity}_data["description"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_{entities}(self, async_client: AsyncClient):
        """Test getting all {entities}."""
        response = await async_client.get("/api/v1/{entities}/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_{entity}_not_found(self, async_client: AsyncClient):
        """Test getting a non-existent {entity}."""
        response = await async_client.get("/api/v1/{entities}/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_{entity}(self, async_client: AsyncClient, sample_{entity}):
        """Test updating a {entity}."""
        update_data = {"name": "Updated {Entity}"}

        response = await async_client.patch(
            f"/api/v1/{entities}/{sample_{entity}.id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]

    @pytest.mark.asyncio
    async def test_delete_{entity}(self, async_client: AsyncClient, sample_{entity}):
        """Test deleting a {entity}."""
        response = await async_client.delete(f"/api/v1/{entities}/{sample_{entity}.id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = await async_client.get(f"/api/v1/{entities}/{sample_{entity}.id}")
        assert get_response.status_code == 404
```

## Usage Instructions

1. **Specify the entity name** when using this prompt (e.g., "Item", "User", "Recipe")
2. **Replace placeholders** like `{Entity}`, `{entity}`, `{entities}` with your actual entity names
3. **Use Context7** to fetch the latest FastAPI documentation for any specific patterns
4. **Run migrations** after creating database models: `uv run alembic revision --autogenerate -m "Add {entity} table"`
5. **Add to main router** in `api/v1/api.py`: `api_router.include_router({entity}_router)`
6. **Run tests** to verify implementation: `uv run pytest tests/test_{entity}.py -v`

## Integration Steps

1. Create the database model and run migration
2. Implement Pydantic schemas with validation
3. Write CRUD operations with proper error handling
4. Create API router with comprehensive endpoints
5. Add router to main API router
6. Write comprehensive tests
7. Update API documentation

Use Context7 to reference `/tiangolo/fastapi` for the latest FastAPI patterns and best practices when implementing your endpoint.
