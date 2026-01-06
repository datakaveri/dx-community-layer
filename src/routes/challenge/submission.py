from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession


from ...middlewares.logging import logger
from ...schemas.default_schemas import AuthorizationData
from ...configs.db_config import get_challenge_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...middlewares.authorization import http_bearer_header
from ...schemas.challenge.submission_requests import (
    CreateUserSubmissionsParams,
    RetrieveUserSubmissionsParams,
    UpdateUserSubmissionsParams,
)
from ...schemas.challenge.submission_responses import (
    CREATE_USER_SUBMISSION_RESPONSE_MODEL,
    RETRIEVE_USER_SUBMISSIONS_RESPONSE_MODEL,
    UPDATE_SUBMISSION_RESPONSE_MODEL,
)
from ...services.challenge.submission_services import (
    create_user_submission_handler,
    retrieve_user_submissions_handler,
    update_user_submission_handler,
)


router = APIRouter(tags=["Challenge - Submission APIs"])


@router.get(
    path="/submissions/{choice}",
    description="Retrieves submissions for an authenticated user across challenges based on their choice.",
    responses=RETRIEVE_USER_SUBMISSIONS_RESPONSE_MODEL,
)
async def retrieve_user_submissions(
    req_params: RetrieveUserSubmissionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves submissions for an authenticated user across challenges based on their choice.

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


@router.post(
    path="/{competition_id}/submission",
    description="Creates a new submission for a specific competition for an authenticated user.",
    responses=CREATE_USER_SUBMISSION_RESPONSE_MODEL,
)
async def create_user_submission(
    req_params: CreateUserSubmissionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Creates a new submission for a specific challenge for an authenticated user.

    Args:
        req_params (CreateUserSubmissionsParams): The request body containing the challenge ID and submission details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created submission details and relevant metadata.
    """
    logger.info("Create User Submission API is being called")

    return await create_user_submission_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.put(
    path="/submission/{submission_id}",
    description="Updates a submission for a specific challenge for an authenticated user.",
    responses=UPDATE_SUBMISSION_RESPONSE_MODEL,
)
async def update_user_submission(
    req_params: UpdateUserSubmissionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Updates a submission for a specific challenge for an authenticated user.

    Args:
        req_params (CreateUserSubmissionsParams): The request body containing the challenge ID and submission details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the updated submission details and relevant metadata.
    """
    logger.info("Update User Submission API is being called")

    return await update_user_submission_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )
