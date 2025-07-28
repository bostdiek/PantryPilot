---
description: "FastAPI backend development guidelines for PantryPilot"
applyTo: "apps/backend/**/*.py"
---

# FastAPI Backend Development

Instructions for building high-quality Python backend applications with FastAPI, modern async patterns, and best practices following the official FastAPI documentation at [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com).

## Project Context

• Python 3.12+ with modern type hints and async/await patterns
• FastAPI 0.116.1+ with dependency injection and automatic validation
• uv for fast Python package management and virtual environments
• SQLAlchemy with async support for database operations
• Alembic 1.16.4+ for database schema migrations
• Pydantic for data validation and serialization
• PostgreSQL 15-alpine as the primary database

## Development Standards

### Python Code Quality

• Follow PEP 8 style guide with Ruff 0.12.5+ for linting and formatting
• Use mypy 1.14.2+ for static type checking with strict mode
• Include comprehensive type hints using `typing` module
• Write clear docstrings following PEP 257 conventions
• Break down complex functions into smaller, more manageable functions
• Handle edge cases with proper exception handling

### FastAPI Architecture

• Structure endpoints with proper dependency injection patterns
• Use `Annotated` types for dependencies: `Annotated[AsyncSession, Depends(get_db)]`
• Implement CRUD operations with async SQLAlchemy patterns
• Create Pydantic schemas for request/response validation
• Use proper HTTP status codes and exception handling
• Include OpenAPI metadata with tags, summaries, and descriptions

### Package Management with uv

• Use `uv add <package>` to add dependencies, never pip directly
• Use `uv sync` to install dependencies from pyproject.toml
• Use `uv run <command>` to execute commands in virtual environment
• Update dependencies with `uv lock --upgrade` for version updates
• Maintain pyproject.toml with precise version specifications

### Database Operations

• Use async SQLAlchemy patterns with AsyncSession for all database operations
• Apply dependency injection for database sessions using `get_db()` function
• Implement proper connection pooling and session management
• Use Alembic for schema migrations with descriptive commit messages
• Handle database exceptions with appropriate HTTP status codes
• Structure models with proper relationships and indexes

### API Design Patterns

• Follow RESTful conventions for endpoint naming and HTTP methods
• Implement proper pagination for list endpoints with `skip` and `limit`
• Use consistent error response formats across all endpoints
• Apply request/response validation with Pydantic models
• Include proper CORS configuration for frontend integration
• Implement health check endpoints for monitoring

### Testing and Quality Assurance

• Write unit tests with pytest 8.4.1+ and async test patterns
• Use pytest fixtures for database sessions and test data
• Mock external dependencies and API calls appropriately
• Include edge case testing for validation and error handling
• Implement integration tests for critical application workflows
• Maintain high test coverage for business logic

### Security Best Practices

• Implement proper input validation and sanitization
• Use dependency injection for authentication and authorization
• Apply rate limiting and request size restrictions
• Validate all user inputs with Pydantic schemas
• Handle sensitive data with proper encryption and hashing
• Log security events and monitor for suspicious activity

### Context7 Integration

• Use Context7 MCP server to fetch latest FastAPI documentation: `/tiangolo/fastapi`
• Reference Python best practices from official docs: `/python/cpython`
• Leverage SQLAlchemy patterns and examples: `/sqlalchemy/sqlalchemy`
• Follow Pydantic validation patterns: `/pydantic/pydantic`

## Error Handling and Testing

• Use FastAPI HTTPException for API errors with proper status codes
• Implement comprehensive error logging and monitoring
• Write pytest tests with async support and database fixtures
• Include test coverage reports with `uv run pytest --cov=src`
• Test edge cases like empty inputs, invalid data types, and large datasets

## Example Implementation

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

router = APIRouter(prefix="/items", tags=["items"])

async def create_item(
    item: ItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ItemResponse:
    """Create a new item with proper validation and error handling."""
    try:
        db_item = Item(**item.model_dump())
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)
        return ItemResponse.model_validate(db_item)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item with this name already exists"
        )
```

## Context7 Integration

When working with FastAPI, use Context7 to reference the latest documentation:
• Use `/tiangolo/fastapi` for official FastAPI patterns and best practices
• Reference `/pydantic/pydantic` for advanced validation patterns
• Consult `/sqlalchemy/sqlalchemy` for database operation guidance
