# app/routes/admin.py

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.challenge.admin_requests import (
    AdminRetrieveCompetitionSubmissionsParams,
    AdminRetrieveCompetitionsParams,
)
from ...middlewares.logging import logger
from ...configs.db_config import get_challenge_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...middlewares.authorization import http_bearer_header
from ...schemas.default_schemas import AuthorizationData, UserRole
from ...database.challenge.enums import CompetitionStatusEnum
from ...schemas.challenge.competition_requests import (
    CreateCompetitionParams,
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
    create_competition_handler,
    update_competition_handler,
    delete_competition_handler,
    announce_result_service,
)
from ...services.challenge.submission_services import (
    get_admin_competition_submissions_handler,
    publish_submission_service,
    admin_edit_submission_evaluation_service,
    disqualify_submission_service,
)
from ...services.challenge.admin_services import (
    admin_retrieve_challenge_dataset_handler,
    admin_retrieve_challenge_by_id_handler,
    admin_retrieve_competition_submissions_handler,
    admin_retrieve_competitions_handler,
)

router = APIRouter(prefix="/admin")


@router.get(
    path="/challenges/{choice}",
    description=(
        "Retrieves competitions for admin with pagination, filters, and sorting. "
        "Only COS_ADMIN can access."
    ),
)
async def admin_retrieve_competitions(
    req_params: AdminRetrieveCompetitionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves a list of competitions for the admin panel.

    Args:
        req_params (AdminRetrieveCompetitionsParams): The request body containing the pagination and filters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved competitions and relevant metadata.
    """
    logger.info("Admin Retrieve Competitions API is being called")

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


# -------------------------------------------------------------------
# ADMIN – CREATE COMPETITION
# -------------------------------------------------------------------
@router.post(
    path="/challenges",
    description="Creates a new competition. Only COS_ADMIN can access.",
)
async def admin_create_challenge(
    req_params: CreateCompetitionParams = Depends(),
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

    return await create_competition_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – GET COMPETITION DATASET
# -------------------------------------------------------------------
@router.get(
    path="/challenges/datasets/{competition_id}",
    description=(
        "Retrieves dataset (databanks and AI models) for a competition. "
        "Only COS_ADMIN can access."
    ),
)
async def admin_retrieve_challenge_dataset(
    competition_id: UUID = Path(
        ..., description="ID of the competition to retrieve dataset for"
    ),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves dataset information for a specific competition.

    Args:
        competition_id: Competition ID.
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
# ADMIN – LIST SUBMISSIONS FOR A COMPETITION
# -------------------------------------------------------------------
@router.get(
    path="/challenges/{competition_id}/submissions",
    description="Retrieves all submissions for a competition. Only COS_ADMIN can access.",
    responses=LIST_SUBMISSIONS_RESPONSE_MODEL,
)
async def admin_retrieve_competition_submissions(
    req_params: AdminRetrieveCompetitionSubmissionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves all submissions for a competition.

    Args:
        req_params (AdminRetrieveCompetitionSubmissionsParams): The request body containing the competition ID and pagination parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved submissions and relevant metadata.
    """
    logger.info("Admin Retrieve Competition Submissions API is being called")

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
# ADMIN – GET COMPETITION BY ID
# -------------------------------------------------------------------
@router.get(
    path="/challenges/{competition_id}",
    description="Retrieves a single competition by ID with all details. Only COS_ADMIN can access.",
)
async def admin_retrieve_challenge_by_id(
    competition_id: UUID = Path(..., description="ID of the competition to retrieve"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Retrieves a single competition with full admin-level details.

    Args:
        competition_id: Competition ID.
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse with competition details or 404 if not found.
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


# -------------------------------------------------------------------
# ADMIN – UPDATE COMPETITION
# -------------------------------------------------------------------
@router.put(
    path="/challenges/{competition_id}",
    description=(
        "Updates an existing competition draft. Only COS_ADMIN can access. "
        "Only draft or scheduled competitions can be updated."
    ),
)
async def admin_update_challenge(
    competition_id: UUID = Path(..., description="ID of the competition to update"),
    req_params: UpdateCompetitionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Updates an existing competition (draft/scheduled) from the admin panel.

    Args:
        competition_id: Competition ID.
        req_params: Update payload for competition.
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

    return await update_competition_handler(
        competition_id=competition_id,
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – DELETE COMPETITION
# -------------------------------------------------------------------
@router.delete(
    path="/challenges/{competition_id}",
    description="Deletes an existing competition draft or scheduled challenge. Only COS_ADMIN can access.",
)
async def admin_delete_challenge(
    competition_id: UUID = Path(..., description="ID of the competition to delete"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Deletes a draft or scheduled competition.

    Args:
        competition_id: Competition ID.
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


# -------------------------------------------------------------------
# ADMIN – DISQUALIFY SUBMISSION
# -------------------------------------------------------------------
@router.put(
    path="/{competition_id}/{submission_id}/disqualify",
    response_model=DisqualifySubmissionResponse,
    description="Disqualify a submission inside a competition. Only COS_ADMIN can access.",
)
async def admin_disqualify_submission(
    competition_id: str = Path(..., description="Competition ID"),
    submission_id: str = Path(..., description="Submission ID"),
    comments: str = Body(..., description="Comments for disqualification"),
    attachment: Optional[str] = Body(
        default=None, description="Attachment for disqualification"
    ),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Disqualifies a specific submission for a given competition.

    Args:
        competition_id: Competition ID.
        submission_id: Submission ID.
        comments: Reason/comments for disqualification.
        attachment: Optional attachment (evidence).
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse indicating disqualification result.
    """
    logger.info(
        f"Admin Disqualify Submission API called for competition={competition_id}, submission={submission_id}"
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

    result = await disqualify_submission_service(
        competition_id=competition_id,
        submission_id=submission_id,
        comments=comments,
        db=db_session,
    )

    if not result:
        return CustomJSONResponse(
            success=False,
            status_code=404,
            message="Submission not found for given competition_id",
            error={"code": "NOT_FOUND"},
        )

    return CustomJSONResponse(
        success=True,
        status_code=200,
        message="Submission successfully disqualified",
    )


# -------------------------------------------------------------------
# ADMIN – ANNOUNCE RESULT
# -------------------------------------------------------------------
@router.post(
    path="/challenges/announce-result",
    description="Announce competition result. Only COS_ADMIN can access.",
)
async def announce_competition_result(
    competition_id: UUID = Query(..., description="Competition ID"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Announces the result for a competition.

    Args:
        competition_id: Competition ID.
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse indicating success or failure.
    """
    logger.info("Announce Competition Result API Called")

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

    return await announce_result_service(
        competition_id=competition_id,
        db=db_session,
    )


# -------------------------------------------------------------------
# ADMIN – PUBLISH SUBMISSION
# -------------------------------------------------------------------
@router.post(
    path="/submission/{submission_id}/publish",
    description="Publishes a submission inside a competition. Only COS_ADMIN can access.",
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
