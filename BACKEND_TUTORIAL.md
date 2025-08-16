# Backend Tutorial: From SQL to FastAPI/Pydantic/Alembic

Welcome to the PantryPilot backend! This tutorial is designed specifically for someone with a strong background in SQL databases, data warehousing, and tools like Snowflake, DBT, and Airflow. We'll map your existing knowledge to Python web development concepts.

## Table of Contents

1. [Conceptual Mapping: From Data Engineering to Web Development](#conceptual-mapping)
2. [Understanding Pydantic: Your Data Validation Layer](#understanding-pydantic)
3. [Understanding the Difference: Models vs Schemas](#understanding-the-difference-models-vs-schemas)
4. [FastAPI Endpoints: Your API Interface](#fastapi-endpoints)
5. [SQLAlchemy: Your ORM Bridge](#sqlalchemy-orm)
6. [Alembic: Your Migration Tool](#alembic-migrations)
7. [Practical Implementation Guide](#practical-implementation)
8. [Testing and Validation](#testing-validation)

## Conceptual Mapping: From Data Engineering to Web Development

### Your Background → Web Development Equivalents

| Your Knowledge | Web Development Equivalent | Purpose |
|----------------|---------------------------|---------|
| SQL Tables/Views | Pydantic Models | Define data structure and validation |
| DBT Models | FastAPI Endpoints | Transform and expose data via HTTP |
| Snowflake Schemas | SQLAlchemy Models | Database table definitions in Python |
| Airflow DAGs | API Request/Response Flow | Orchestrate data processing |
| Data Validation | Pydantic Field Validation | Ensure data quality at API boundary |
| ETL Pipelines | CRUD Operations | Create, Read, Update, Delete data |

### The Request Flow

Just like an Airflow DAG, a web request flows through stages:

```
HTTP Request → FastAPI Endpoint → Pydantic Validation → Business Logic → SQLAlchemy ORM → Database
     ↓
HTTP Response ← Pydantic Serialization ← Business Logic ← SQLAlchemy Results ← Database
```

## Understanding Pydantic: Your Data Validation Layer

Think of Pydantic as **DBT for API data** - it defines the schema, validates inputs, and transforms data types.

### From SQL to Pydantic

**SQL Table Definition:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    full_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Equivalent Pydantic Model:**
```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    """Schema for creating a new user (request body)"""
    username: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)

class UserResponse(BaseModel):
    """Schema for returning user data (response body)"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True  # Allows creation from SQLAlchemy models
```

### Key Pydantic Concepts

1. **Input Validation** (like DBT tests):
   ```python
   class Item(BaseModel):
       name: str = Field(..., min_length=1, max_length=100)
       price: float = Field(..., gt=0)  # Must be greater than 0
       tags: List[str] = Field(default_factory=list)
   ```

2. **Data Transformation** (like DBT macros):
   ```python
   from pydantic import validator

   class User(BaseModel):
       email: str

       @validator('email')
       def email_must_be_lowercase(cls, v):
           return v.lower()
   ```

3. **Nested Models** (like joined tables):
   ```python
   class Address(BaseModel):
       street: str
       city: str
       country: str = "USA"

   class User(BaseModel):
       name: str
       address: Address  # Nested model
   ```

## Understanding the Difference: Models vs Schemas

Before we dive into FastAPI endpoints, it's crucial to understand the distinction between `src/models` and `src/schemas` - this is a common source of confusion but fundamental to clean architecture.

### `src/models` - Database Layer (SQLAlchemy Models)

**Purpose**: Define the actual database table structure and relationships

**What they do**:
- Define database tables, columns, constraints, and relationships
- Handle database operations (queries, inserts, updates, deletes)
- Map Python objects to database rows
- Define foreign keys, indexes, and database-level constraints

**Example**:
```python
# src/models/user.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # Stored in DB
    created_at = Column(DateTime, default=datetime.utcnow)

    # Database relationships
    items = relationship("Item", back_populates="owner")
```

### `src/schemas` - API Layer (Pydantic Models)

**Purpose**: Define data validation, serialization, and API contracts

**What they do**:
- Validate incoming request data
- Serialize outgoing response data
- Define what fields are required/optional for different operations
- Handle data transformation and validation rules
- Generate API documentation

**Example**:
```python
# src/schemas/user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str  # Plain text from API request
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    # Note: NO password field - never return passwords in API responses

    class Config:
        from_attributes = True  # Can create from SQLAlchemy model
```

### Key Differences in Practice

#### 1. **Data Flow Direction**
- **Models**: Database ↔ Python objects
- **Schemas**: API requests/responses ↔ Python objects

#### 2. **Security Considerations**
```python
# Models store everything (including sensitive data)
class User(Base):
    password_hash = Column(String(255))  # Hashed password stored in DB

# Schemas control what's exposed via API
class UserResponse(BaseModel):
    username: str
    email: str
    # NO password field - security!

class UserCreate(BaseModel):
    password: str  # Plain text input for creation only
```

#### 3. **Different Schemas for Different Operations**
```python
# Creating a user (what we need from client)
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

# Updating a user (all fields optional)
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    # No password - handle separately for security

# Returning user data (what we send back)
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
```

### How They Work Together

Here's a typical flow in your FastAPI endpoint:

```python
@app.post("/users/", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # 1. FastAPI validates incoming JSON against UserCreate schema
    # 2. Convert schema to model data
    user_dict = user_data.dict()
    user_dict['password_hash'] = hash_password(user_dict.pop('password'))

    # 3. Create SQLAlchemy model instance
    db_user = User(**user_dict)

    # 4. Save to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 5. Return response (automatically converts User model to UserResponse schema)
    return db_user
```

### Summary Comparison

| Aspect | Models (SQLAlchemy) | Schemas (Pydantic) |
|--------|-------------------|-------------------|
| **Purpose** | Database structure | API validation/serialization |
| **Location** | `src/models/` | `src/schemas/` |
| **Deals with** | Tables, columns, relationships | Requests, responses, validation |
| **Security** | Stores everything | Controls what's exposed |
| **Validation** | Database constraints | Input/output validation |
| **Multiple per entity** | Usually one | Multiple (Create, Update, Response) |

**Real-World Analogy**: Think of it like a restaurant:
- **Models** = Kitchen equipment and storage (how food is actually stored and prepared)
- **Schemas** = Menu and ordering system (what customers see and can order)

This separation allows you to:
1. **Secure your API** - control exactly what data is exposed
2. **Flexible validation** - different rules for different operations
3. **Clean architecture** - separate concerns between data storage and API interface
4. **Evolution** - change API contracts without changing database structure

## FastAPI Endpoints: Your API Interface

FastAPI endpoints are like **Snowflake stored procedures** or **DBT models** - they define how to process and return data.

### Basic CRUD Operations

Think of these as your standard data operations:

```python
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

app = FastAPI()

@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Like INSERT INTO users..."""
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Like SELECT * FROM users WHERE id = ?"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users/", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Like SELECT * FROM users LIMIT ? OFFSET ?"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserCreate, db: Session = Depends(get_db)):
    """Like UPDATE users SET ... WHERE id = ?"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Like DELETE FROM users WHERE id = ?"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}
```

### Advanced Patterns

**Complex Queries** (like your analytical SQL):
```python
@app.get("/users/analytics", response_model=List[UserAnalytics])
async def user_analytics(db: Session = Depends(get_db)):
    """
    Like: SELECT username, COUNT(items.id) as item_count, AVG(items.price) as avg_price
          FROM users
          LEFT JOIN items ON users.id = items.user_id
          GROUP BY users.id, username
    """
    result = (
        db.query(User.username, func.count(Item.id), func.avg(Item.price))
        .outerjoin(Item)
        .group_by(User.id, User.username)
        .all()
    )
    return [{"username": r[0], "item_count": r[1], "avg_price": r[2]} for r in result]
```

## SQLAlchemy ORM: Your Database Bridge

SQLAlchemy is like **defining your data warehouse schema in Python**. It translates between Python objects and SQL tables.

### From SQL DDL to SQLAlchemy Models

**SQL Table:**
```sql
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**SQLAlchemy Model:**
```python
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships (like JOINs)
    user = relationship("User", back_populates="items")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), nullable=False)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    items = relationship("Item", back_populates="user")
```

### Querying with SQLAlchemy

Think of this as **translating your SQL knowledge to Python**:

```python
# SELECT * FROM users WHERE username = 'john'
user = db.query(User).filter(User.username == 'john').first()

# SELECT * FROM items WHERE price > 100 ORDER BY price DESC
expensive_items = db.query(Item).filter(Item.price > 100).order_by(Item.price.desc()).all()

# SELECT users.*, COUNT(items.id) as item_count
# FROM users LEFT JOIN items ON users.id = items.user_id
# GROUP BY users.id
user_counts = (
    db.query(User, func.count(Item.id).label('item_count'))
    .outerjoin(Item)
    .group_by(User.id)
    .all()
)
```

## Alembic Migrations: Your Schema Evolution Tool

Alembic is like **DBT's incremental models** - it manages schema changes over time.

### Migration Workflow

This is similar to how you might manage schema changes in a data warehouse:

1. **Create a migration** (like planning a schema change):
   ```bash
   cd apps/backend/src
   uv run alembic revision -m "add user table"
   ```

2. **Edit the migration file** (like writing the DDL):
   ```python
   # alembic/versions/001_add_user_table.py
   from alembic import op
   import sqlalchemy as sa

   def upgrade():
       """Like your 'up' migration in DBT"""
       op.create_table(
           'users',
           sa.Column('id', sa.Integer(), primary_key=True),
           sa.Column('username', sa.String(50), nullable=False),
           sa.Column('email', sa.String(100), nullable=False),
           sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
       )
       op.create_index('ix_users_username', 'users', ['username'], unique=True)

   def downgrade():
       """Like your rollback plan"""
       op.drop_index('ix_users_username', table_name='users')
       op.drop_table('users')
   ```

3. **Apply the migration** (like deploying to prod):
   ```bash
   uv run alembic upgrade head
   ```

### Migration Best Practices

- **Always test migrations** (like testing DBT models):
  ```bash
  # Test on dev first
  uv run alembic upgrade head

  # Test rollback
  uv run alembic downgrade -1
  uv run alembic upgrade head
  ```

- **Use descriptive migration names**:
  ```bash
  uv run alembic revision -m "add_user_email_index_for_performance"
  ```

## Practical Implementation Guide

### Setting Up Your Models

Based on our existing schema in `db/init/schema.sql`, let's create the models:

**File: `apps/backend/src/models/user.py`**
```python
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("Item", back_populates="owner")
```

**File: `apps/backend/src/models/item.py`**
```python
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100))
    quantity = Column(Integer, default=1)
    unit = Column(String(50))
    expiry_date = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="items")
```

### Setting Up Your Schemas

**File: `apps/backend/src/schemas/user.py`**
```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(UserBase):
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserWithItems(UserResponse):
    items: List['ItemResponse'] = []
```

**File: `apps/backend/src/schemas/item.py`**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    quantity: int = Field(default=1, ge=0)
    unit: Optional[str] = Field(None, max_length=50)
    expiry_date: Optional[datetime] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    quantity: Optional[int] = Field(None, ge=0)

class ItemResponse(ItemBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Setting Up Your API Endpoints

**File: `apps/backend/src/api/v1/endpoints/users.py`**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ....dependencies.database import get_db
from ....schemas.user import UserCreate, UserResponse, UserUpdate, UserWithItems
from ....crud.user import user_crud

router = APIRouter()

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    db_user = user_crud.get_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    return user_crud.create(db=db, obj_in=user)

@router.get("/{user_id}", response_model=UserWithItems)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID with their items"""
    db_user = user_crud.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List users with pagination"""
    users = user_crud.get_multi(db, skip=skip, limit=limit)
    return users

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    """Update user"""
    db_user = user_crud.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_crud.update(db, db_obj=db_user, obj_in=user_in)

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete user"""
    db_user = user_crud.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user_crud.remove(db, id=user_id)
    return {"message": "User deleted successfully"}
```

## Testing and Validation

### Unit Tests (like DBT tests)

**File: `apps/backend/tests/test_schemas.py`**
```python
import pytest
from pydantic import ValidationError
from src.schemas.user import UserCreate

def test_user_create_valid():
    """Test valid user creation"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User"
    }
    user = UserCreate(**user_data)
    assert user.username == "testuser"
    assert user.email == "test@example.com"

def test_user_create_invalid_email():
    """Test user creation with invalid email"""
    user_data = {
        "username": "testuser",
        "email": "invalid-email",
        "password": "securepassword123"
    }
    with pytest.raises(ValidationError):
        UserCreate(**user_data)

def test_user_create_short_password():
    """Test user creation with short password"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "short"
    }
    with pytest.raises(ValidationError):
        UserCreate(**user_data)
```

### Integration Tests (like end-to-end pipeline tests)

**File: `apps/backend/tests/test_api.py`**
```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_create_user():
    """Test the complete user creation flow"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User"
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data

def test_get_user():
    """Test retrieving a user"""
    # First create a user
    user_data = {
        "username": "getuser",
        "email": "get@example.com",
        "password": "securepassword123"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]

    # Then retrieve it
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == "getuser"
    assert data["email"] == "get@example.com"
```

## Next Steps

1. **Start with Models**: Create your SQLAlchemy models in `apps/backend/src/models/`
2. **Define Schemas**: Create your Pydantic schemas in `apps/backend/src/schemas/`
3. **Generate Migrations**: Use Alembic to create database migrations
4. **Build CRUD Operations**: Create your database operations in `apps/backend/src/crud/`
5. **Create Endpoints**: Build your FastAPI endpoints in `apps/backend/src/api/v1/endpoints/`
6. **Write Tests**: Create comprehensive tests for your models, schemas, and endpoints

## Common Patterns You'll Use

### Repository Pattern (like your data access layers)
```python
# apps/backend/src/crud/base.py
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
```

Remember: You're not just writing code, you're building a **data-driven application**. Your SQL and data engineering skills are incredibly valuable here - you understand data flow, validation, and performance optimization. This is just a different way of expressing those same concepts!

Happy coding! 🚀
