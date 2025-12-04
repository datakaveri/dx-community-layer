from uuid import UUID
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ...configs.db_config import get_challenge_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...middlewares.authorization import http_bearer_header
from ...schemas.challenge.competition_requests import (
    RetrieveParticipatedCompetitionsParams,
)
from ...schemas.challenge.competition_responses import (
    RETRIEVE_PARTICIPATED_COMPETITIONS_RESPONSE_MODEL,
)
from ...services.challenge.competition_services import (
    retrieve_participated_competitions_handler,
)
from ...services.challenge.challenge_services import (
    get_competition_leaderboard_handler,
)

# Import child routers
from .admin import router as admin_router
from .users import router as users_router
from .attachment import router as attachment_router
from .submission import router as submission_router


router = APIRouter(prefix="/challenge", tags=["Challenge APIs"])


router.include_router(admin_router)
router.include_router(submission_router)
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
    db_session: AsyncSession = Depends(get_challenge_db_session),
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


@router.get(
    path="/participated",
    description="Returns all competitions that the user has participated in.",
    responses=RETRIEVE_PARTICIPATED_COMPETITIONS_RESPONSE_MODEL,
)
async def retrieve_participated_competitions(
    req_params: RetrieveParticipatedCompetitionsParams = Depends(),
    authorized_user: dict = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves competitions that the user has participated in.

    Args:
        req_params (RetrieveParticipatedCompetitionsParams): The request body containing the sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved competitions and relevant metadata.
    """
    logger.info("Retrieve Participated Competitions API is being called")

    return await retrieve_participated_competitions_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )
