from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...docs import public_desc
from ...middlewares.logging import logger
from ...schemas.default_schemas import AuthorizationData
from ...configs.db_config import get_challenge_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...middlewares.authorization import http_bearer_header, http_bearer_header_public
from ...schemas.challenge.competition_requests import (
    RetrieveCompetitionLeaderboardParams,
    RetrieveCompetitonsParams,
    RetrieveParticipatedCompetitionsParams,
)
from ...schemas.challenge.competition_responses import (
    RETRIEVE_COMPETITION_LEADERBOARD_RESPONSE_MODEL,
    RETRIEVE_PARTICIPATED_COMPETITIONS_RESPONSE_MODEL,
)
from ...services.challenge.competition_services import (
    retrieve_competition_leaderboard_handler,
    retrieve_competitions_handler,
    retrieve_participated_competitions_handler,
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
    path="/{choice}",
    description=public_desc(
        (
            "Retrieves all competitions accross the TGDex platform based on the choice provided.",
            "Supports pagination, sorting and filtering (by query).",
        )
    ),
)
async def retrieve_competitions(
    req_params: RetrieveCompetitonsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves all competitions accross the TGDex platform.

    Args:
        req_params (RetrieveCompetitonsParams): The request body containing the sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved competitions and relevant metadata.
    """

    logger.info("Retrieve Competitions API is being called")

    return await retrieve_competitions_handler(
        req_params=req_params, authorized_user=authorized_user, db_session=db_session
    )


@router.get(
    path="/{competition_id}/leaderboard",
    description=public_desc(
        (
            "Retrieves the leaderboard for a specific competition. Supports pagination, "
            "sorting and filtering (by query)."
        )
    ),
    responses=RETRIEVE_COMPETITION_LEADERBOARD_RESPONSE_MODEL,
)
async def retrieve_competition_leaderboard(
    req_params: RetrieveCompetitionLeaderboardParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves the leaderboard for a specific competition.

    Args:
        req_params (RetrieveCompetitionLeaderboard): The request body containing the sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved leaderboard and relevant metadata.
    """

    logger.info("Retrieve Competition Leaderboard API is being called")

    return await retrieve_competition_leaderboard_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/participated",
    description="Returns all competitions that the user has participated in.",
    responses=RETRIEVE_PARTICIPATED_COMPETITIONS_RESPONSE_MODEL,
)
async def retrieve_participated_competitions(
    req_params: RetrieveParticipatedCompetitionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
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
