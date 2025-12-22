from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Body, Depends, Path, Query

from ...schemas.challenge.admin_responses import ADMIN_CREATE_COMPETITION_RESPONSE_MODEL
from ...schemas.challenge.admin_requests import (
    AdminCreateCompetitionParams,
    AdminEvaluateSubmissionParams,
    AdminRetrieveCompetitionSubmissionsParams,
    AdminRetrieveCompetitionsParams,
    AdminUpdateCompetitionParams,
)
from ...middlewares.logging import logger
from ...configs.db_config import get_challenge_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...middlewares.authorization import http_bearer_header
from ...schemas.default_schemas import AuthorizationData, UserRole
from ...schemas.challenge.competition_requests import (
    UpdateCompetitionParams,
)
from ...schemas.challenge.submission_requests import (
    PublishSubmissionParams,
    AdminEditSubmissionParams,
)
from ...schemas.challenge.submission_responses import (
    LIST_SUBMISSIONS_RESPONSE_MODEL,
    DisqualifySubmissionResponse,
)
from ...services.challenge.competition_services import (
    admin_announce_competition_result_handler,
    update_competition_handler,
    delete_competition_handler,
)
from ...services.challenge.submission_services import (
    publish_submission_service,
    admin_edit_submission_evaluation_service,
    disqualify_submission_service,
)
from ...services.challenge.admin_services import (
    admin_create_competition_handler,
    admin_evaluate_submission_handler,
    admin_retrieve_challenge_dataset_handler,
    admin_retrieve_challenge_by_id_handler,
    admin_retrieve_competition_submissions_handler,
    admin_retrieve_competitions_handler,
    admin_update_competition_handler,
)


router = APIRouter(prefix="/admin", tags=["Challenge - Admin APIs"])


@router.get(
    path="/challenge/{competition_id}",
    description="Retrieves a single challenge by ID with all details. Only COS_ADMIN can access.",
)
async def admin_retrieve_challenge_by_id(
    competition_id: UUID = Path(..., description="ID of the challenge to retrieve"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves a single challenge with full admin-level details.

    Args:
        challenge_id: Challenge ID.
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse with challenge details or 404 if not found.
    """
    logger.info("Admin Retrieve Challenge by ID API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await admin_retrieve_challenge_by_id_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/challenges/{choice}",
    description=(
        "Retrieves challenges for admin with pagination, filters, and sorting. "
        "Only COS_ADMIN can access."
    ),
)
async def admin_retrieve_competitions(
    req_params: AdminRetrieveCompetitionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves a list of challenges for the admin panel.

    Args:
        req_params (AdminRetrieveChallengesParams): The request body containing the pagination and filters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved challenges and relevant metadata.
    """
    logger.info("Admin Retrieve Challenges API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await admin_retrieve_competitions_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/challenge",
    description="Creates a new competition (challenge) from the admin panel. Only COS_ADMIN can access.",
    responses=ADMIN_CREATE_COMPETITION_RESPONSE_MODEL,
)
async def admin_create_competition(
    req_params: AdminCreateCompetitionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Creates a new competition (challenge) from the admin panel.

    Args:
        req_params: Competition creation payload (title, description, timeline, etc.).
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse with created competition details.
    """
    logger.info("Admin Create Challenge API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await admin_create_competition_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.put(
    path="/challenge/{competition_id}",
    description="Updates an existing challenge (competition) from the admin panel. Only COS_ADMIN can access.",
)
async def admin_update_competition(
    req_params: AdminUpdateCompetitionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Updates an existing challenge (competition) from the admin panel.

    Args:
        req_params: Competition update payload (title, description, timeline, etc.).
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse with updated competition details.
    """
    logger.info("Admin Update Challenge API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await admin_update_competition_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – GET CHALLENGE DATASET
# -------------------------------------------------------------------
@router.get(
    path="/challenges/datasets/{competition_id}",
    description=(
        "Retrieves dataset (databanks and AI models) for a challenge. "
        "Only COS_ADMIN can access."
    ),
)
async def admin_retrieve_challenge_dataset(
    competition_id: UUID = Path(
        ..., description="ID of the challenge to retrieve dataset for"
    ),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves dataset information for a specific challenge.

    Args:
        challenge_id: Challenge ID.
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse with dataset details or 404 if not found.
    """
    logger.info("Admin Retrieve Challenge Dataset API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await admin_retrieve_challenge_dataset_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – LIST SUBMISSIONS FOR A CHALLENGE
# -------------------------------------------------------------------
@router.get(
    path="/challenges/{competition_id}/submissions",
    description="Retrieves all submissions for a challenge. Only COS_ADMIN can access.",
    responses=LIST_SUBMISSIONS_RESPONSE_MODEL,
)
async def admin_retrieve_competition_submissions(
    req_params: AdminRetrieveCompetitionSubmissionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves all submissions for a challenge.

    Args:
        req_params (AdminRetrieveChallengeSubmissionsParams): The request body containing the challenge ID and pagination parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved submissions and relevant metadata.
    """
    logger.info("Admin Retrieve Challenge Submissions API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await admin_retrieve_competition_submissions_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – DELETE CHALLENGE
# -------------------------------------------------------------------
@router.delete(
    path="/challenges/{competition_id}",
    description="Deletes an existing challenge draft or scheduled challenge. Only COS_ADMIN can access.",
)
async def admin_delete_challenge(
    competition_id: UUID = Path(..., description="ID of the challenge to delete"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Deletes a draft or scheduled challenge.

    Args:
        challenge_id: Challenge ID.
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse indicating deletion result.
    """
    logger.info("Admin Delete Challenge API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await delete_competition_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.put(
    path="/submission/{submission_id}/evaluate",
    description="Evaluates a submission inside a competition. Only COS_ADMIN can access.",
)
async def admin_evaluate_submission(
    req_params: AdminEvaluateSubmissionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Evaluates a specific submission for a given competition.

    Args:
        req_params (DisqualifySubmissionParams): The request body containing the submission ID and disqualification details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the disqualification details and relevant metadata.
    """
    logger.info("Admin Disqualify Submission API is being called")

    return await admin_evaluate_submission_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – ANNOUNCE RESULT
# -------------------------------------------------------------------
@router.post(
    path="/challenges/announce-result",
    description="Announce challenge result. Only COS_ADMIN can access.",
)
async def admin_announce_competition_result(
    competition_id: UUID = Query(..., description="Challenge ID"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Announces the result for a challenge.

    Args:
        challenge_id: Challenge ID.
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse indicating success or failure.
    """
    logger.info("Announce Challenge Result API Called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": "You are not authorized to access this resource.",
            },
        )

    return await admin_announce_competition_result_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – PUBLISH SUBMISSION
# -------------------------------------------------------------------
@router.post(
    path="/submission/{submission_id}/publish",
    description="Publishes a submission inside a challenge. Only COS_ADMIN can access.",
)
async def admin_publish_submission(
    req_params: PublishSubmissionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Publishes a submission (marks as visible/accepted).

    Args:
        req_params: Publish payload (submission_id and related info).
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse indicating publish result.
    """
    logger.info(
        f"Admin Publish Submission API called for submission={req_params.submission_id}"
    )

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await publish_submission_service(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – EDIT SUBMISSION EVALUATION
# -------------------------------------------------------------------
@router.put(
    path="/submission/{submission_id}/publish",
    description=(
        "Updates score, comments, and disqualification status for a submission. "
        "Only COS_ADMIN can access."
    ),
)
async def admin_edit_submission_evaluation(
    req_params: AdminEditSubmissionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Edits evaluation details of a submission (score, comments, disqualification).

    Args:
        req_params: Evaluation update payload.
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse indicating update result.
    """
    logger.info(
        f"Admin Edit Submission Evaluation API called for submission={req_params.submission_id}"
    )

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=403,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": (
                    "You are not authorized to access this resource. "
                    "Please contact support if required."
                ),
            },
        )

    return await admin_edit_submission_evaluation_service(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )
