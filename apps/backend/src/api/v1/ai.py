"""AI-powered recipe extraction and suggestion endpoints."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic_ai import AgentRunError

from core.security import create_draft_token
from crud.ai_drafts import create_draft, get_draft_by_id
from dependencies.auth import get_current_user
from dependencies.db import DbSession
from models.users import User
from schemas.ai import (
    AIDraftFetchResponse,
    AIDraftResponse,
    AIRecipeFromUrlRequest,
)
from schemas.api import ApiResponse
from services.ai import (
    HTMLExtractionService,
    convert_to_recipe_create,
    create_recipe_agent,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Initialize services
html_service = HTMLExtractionService()


@router.post("/extract-recipe-from-url", response_model=ApiResponse[AIDraftResponse])
async def extract_recipe_from_url(
    request: AIRecipeFromUrlRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[AIDraftResponse]:
    """Extract recipe from URL using AI and create a signed deep link.
    
    This endpoint:
    1. Validates and fetches HTML from the provided URL
    2. Sanitizes the HTML content to remove ads/scripts/trackers
    3. Uses AI to extract structured recipe data
    4. Creates a temporary AIDraft with the extracted data
    5. Returns a signed deep link for the frontend to load the draft
    
    Requires authentication via JWT Bearer token.
    
    Args:
        request: Contains source URL and optional prompt override
        db: Database session
        current_user: Authenticated user from JWT
        
    Returns:
        ApiResponse containing draft_id, signed_url, and expiration info
        
    Raises:
        HTTPException: 422 for invalid URL, 500 for AI/processing failures
    """
    try:
        # Step 1: Fetch and sanitize HTML
        logger.info(f"Fetching recipe from URL: {request.source_url}")
        sanitized_html = await html_service.fetch_and_sanitize(str(request.source_url))
        
        if not sanitized_html.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No usable content found at the provided URL"
            )
        
        # Step 2: Create AI agent and extract recipe
        logger.info("Extracting recipe using AI agent")
        agent = create_recipe_agent()
        
        # Use custom prompt if provided, otherwise use default
        prompt = (
            request.prompt_override 
            or "Extract the recipe information from this HTML content:"
        )
        full_prompt = f"{prompt}\n\nHTML Content:\n{sanitized_html}"
        
        try:
            # Run AI extraction
            result = await agent.run(full_prompt)
            extraction_result = result.data
            
            logger.info(
                f"AI extraction completed with confidence: "
                f"{extraction_result.confidence_score}"
            )
            
        except AgentRunError as e:
            logger.error(f"AI agent failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Failed to extract recipe using AI. "
                    "The content may not contain a valid recipe."
                )
            ) from e
        except Exception as e:
            logger.error(f"Unexpected AI error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI processing failed"
            ) from e
        
        # Step 3: Convert to standard recipe schema
        try:
            generated_recipe = convert_to_recipe_create(
                extraction_result, str(request.source_url)
            )
        except Exception as e:
            logger.error(f"Schema conversion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process extracted recipe data"
            ) from e
        
        # Step 4: Create draft with extracted data
        draft_payload = {
            "generated_recipe": generated_recipe.model_dump(),
            "extraction_metadata": {
                "confidence_score": generated_recipe.confidence_score,
                "source_url": str(request.source_url),
                "extracted_at": datetime.now(UTC).isoformat(),
            }
        }
        
        draft = await create_draft(
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=draft_payload,
            source_url=str(request.source_url),
            prompt_used=request.prompt_override,
            ttl_hours=1,
        )
        
        # Step 5: Create signed token and deep link
        ttl = timedelta(hours=1)
        token = create_draft_token(draft.id, current_user.id, ttl)
        
        # Create deep link URL for frontend
        signed_url = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"
        
        response_data = AIDraftResponse(
            draft_id=draft.id,
            signed_url=signed_url,
            expires_at=draft.expires_at,
            ttl_seconds=3600,  # 1 hour
        )
        
        logger.info(
            f"Successfully created AI draft {draft.id} for user {current_user.id}"
        )
        
        return ApiResponse(
            success=True,
            data=response_data,
            message="Recipe extracted successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in recipe extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during recipe extraction"
        ) from e


@router.get("/drafts/{draft_id}", response_model=ApiResponse[AIDraftFetchResponse])
async def get_ai_draft(
    draft_id: UUID,
    token: str,
    db: DbSession,
) -> ApiResponse[AIDraftFetchResponse]:
    """Fetch an AI draft using a signed token.
    
    This endpoint validates the signed token and returns the draft payload
    if the token is valid and not expired.
    
    Args:
        draft_id: UUID of the draft to fetch
        token: Signed JWT token for authorization
        db: Database session
        
    Returns:
        ApiResponse containing the draft payload and metadata
        
    Raises:
        HTTPException: 401 for invalid/expired token, 404 for draft not found
    """
    try:
        # Decode and validate the token
        from core.security import decode_draft_token
        token_payload = decode_draft_token(token)
        
        # Verify the draft_id matches the token
        if str(draft_id) != token_payload.get("draft_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not match draft ID"
            )
        
        # Get user_id from token for ownership check
        user_id = UUID(token_payload["user_id"])
        
        # Fetch the draft
        draft = await get_draft_by_id(db, draft_id, user_id)
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )
        
        # Check if draft has expired
        if datetime.now(UTC) >= draft.expires_at:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft has expired"
            )
        
        response_data = AIDraftFetchResponse(
            payload=draft.payload,
            type="recipe_suggestion",  # Currently only supporting recipes
            created_at=draft.created_at,
            expires_at=draft.expires_at,
        )
        
        return ApiResponse(
            success=True,
            data=response_data,
            message="Draft retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching draft {draft_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve draft"
        ) from e