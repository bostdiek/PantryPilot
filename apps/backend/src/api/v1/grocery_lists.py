"""API endpoints for grocery list functionality."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from crud.grocery_lists import grocery_list_crud
from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.users import User
from schemas.api import ApiResponse
from schemas.grocery_lists import GroceryListRequest, GroceryListResponse


router = APIRouter(prefix="/grocery-lists", tags=["grocery-lists"])


@router.post(
    "",
    summary="Generate grocery list",
    response_model=ApiResponse[GroceryListResponse],
    description=(
        "Generate a grocery list for the authenticated user based on their meal plan "
        "within the specified date range. Aggregates ingredients from all recipes "
        "planned for the given period, excluding optional ingredients and meals "
        "marked as 'eating out'."
    ),
    responses={
        200: {"description": "Grocery list generated successfully"},
        400: {"description": "Invalid date range provided"},
        401: {"description": "Authentication required"},
    },
)
async def generate_grocery_list(
    request: GroceryListRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[GroceryListResponse]:
    """Generate a grocery list for the authenticated user.
    
    Args:
        request: Date range for grocery list generation
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ApiResponse containing the grocery list with aggregated ingredients
        
    Raises:
        HTTPException: If the date range is invalid (end_date before start_date)
    """
    # Validate date range
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be on or after start date"
        )
    
    try:
        # Generate the grocery list using CRUD layer
        grocery_list = await grocery_list_crud.generate_grocery_list(
            db=db,
            user_id=current_user.id,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        
        return ApiResponse(
            data=grocery_list,
            message="Grocery list generated successfully"
        )
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error generating grocery list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the grocery list"
        ) from e