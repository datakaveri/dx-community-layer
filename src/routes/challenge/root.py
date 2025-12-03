from fastapi import APIRouter, Depends, Path
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ...configs.db_config import get_db_session
from ...middlewares.logging import logger
from ...schemas.custom_responses import CustomJSONResponse

from ...services.challenge.challenge_services import (
    get_competition_leaderboard_handler,
)
from .admin import router as admin_router
from .attachment import router as attachment_router
from .users import router as users_router

# Main Challenge router namespace
router = APIRouter(prefix="/challenge", tags=["Challenge APIs"])

# Attach child routers
router.include_router(admin_router)
router.include_router(attachment_router)
router.include_router(users_router)


@router.get(
    path="/{competition_id}/leaderboard",
    description=(
        "Returns submissions for a competition with user data, "
        "sorted by score (leaderboard style)."
    ),
)
async def get_competition_leaderboard(
    competition_id: UUID = Path(..., description="ID of the competition"),
    db_session: AsyncSession = Depends(get_db_session),
) -> CustomJSONResponse:

    """
    Public endpoint that retrieves the leaderboard for a competition.

    Args:
        competition_id: ID of the competition.
        db_session: DB session instance.

    Returns:
        CustomJSONResponse: Leaderboard list with ranks.
    """

    logger.info("Public Competition Leaderboard API is being called")

    return await get_competition_leaderboard_handler(
        competition_id=competition_id,
        db_session=db_session,
    )
