from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession


from ...middlewares.logging import logger
from ...schemas.default_schemas import AuthorizationData
from ...configs.db_config import get_challenge_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...middlewares.authorization import http_bearer_header
from ...schemas.challenge.submission_requests import RetrieveUserSubmissionsParams
from ...schemas.challenge.submission_responses import (
    RETRIEVE_USER_SUBMISSIONS_RESPONSE_MODEL,
)
from ...services.challenge.submission_services import (
    retrieve_user_submissions_handler,
)


router = APIRouter()


@router.get(
    path="/submissions/{choice}",
    description="Endpoint for authenticated users to get their submissions across competitions.",
    responses=RETRIEVE_USER_SUBMISSIONS_RESPONSE_MODEL,
)
async def retrieve_user_submissions(
    req_params: RetrieveUserSubmissionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves submissions for a user across competitions based on their choice.

    Args:
        req_params (RetrieveUserSubmissionsParams): The request body containing the choice and sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved submission interests and relevant metadata.
    """
    logger.info("Retrieve User Submissions API is being called")

    return await retrieve_user_submissions_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )
