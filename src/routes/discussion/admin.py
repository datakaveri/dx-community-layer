from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.discussion.admin_requests import (
    AdminRetrieveCommentReportsParams,
    AdminRetrieveDiscussionParams,
    AdminReviewDiscussionParams,
    AdminRetrieveCommentsParams,
    AdminReviewCommentParams,
)
from ...schemas.discussion.comment_requests import ReviewCommentReportParams

from ...services.discussion.admin_services import (
    admin_retrieve_discussions_handler,
    admin_review_discussion_handler,
    admin_retrieve_comments_handler,
    admin_review_comment_handler,
    admin_retrieve_comment_reports_handler,
    admin_review_comment_report_handler,
)
from ...schemas.discussion.admin_responses import (
    ADMIN_RETRIEVE_DISCUSSIONS_RESPONSE_MODEL,
    ADMIN_REVIEW_DISCUSSION_RESPONSE_MODEL,
    ADMIN_REVIEW_COMMENT_RESPONSE_MODEL,
)
from ...middlewares.logging import logger
from ...configs.db_config import get_discussion_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...middlewares.authorization import http_bearer_header
from ...schemas.default_schemas import AuthorizationData, UserRole


router = APIRouter(prefix="/admin", tags=["Discussion - Admin APIs"])


@router.get(
    path="/discussions/{choice}",
    description=(
        "Retrieves a list of discussions for the admin panel. Supports pagination, "
        "filtering (by type, status, tags). "
    ),
    responses=ADMIN_RETRIEVE_DISCUSSIONS_RESPONSE_MODEL,
)
async def admin_retrieve_discussions(
    req_params: AdminRetrieveDiscussionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Retrieves discussions for the admin panel based on the provided filters and choice.

    Args:
        req_params (AdminRetrieveDiscussionParams): The request body containing the pagination and filters.
        user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved discussions and relevant metadata.
    """
    logger.info("Admin Retrieve Discussions API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": "You are not authorized to access this resource. Please contact support if required.",
            },
        )

    return await admin_retrieve_discussions_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/review/discussion/{discussion_id}",
    description="Updates the review status of a discussion.\n`Note: Only Admins can access this route.`",
    responses=ADMIN_REVIEW_DISCUSSION_RESPONSE_MODEL,
)
async def admin_review_discussion(
    req_params: AdminReviewDiscussionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Reviews a discussion based on the provided discussion ID.

    Args:
        discussion_id (UUID): The ID of the discussion to review.
        user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the reviewed discussion and relevant metadata.
    """
    logger.info("Admin Retrieve Discussions API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": "You are not authorized to access this resource. Please contact support if required.",
            },
        )

    return await admin_review_discussion_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/comments/{choice}",
    description=(
        "Retrieve comments pending for admin approval and the history.\n"
        "`Note: Only Admins can access this route.`"
    ),
    responses=ADMIN_REVIEW_COMMENT_RESPONSE_MODEL,
)
async def admin_retrieve_comments(
    req_params: AdminRetrieveCommentsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    logger.info("Admin Retrieve Pending Comments API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": "You are not authorized to access this resource. Please contact support if required.",
            },
        )

    return await admin_retrieve_comments_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.put(
    path="/comments/{comment_id}/review",
    description=(
        "Review a comment for approval or rejection.\n"
        "`Note: Only Admins can access this route.`"
    ),
)
async def admin_review_comment(
    req_params: AdminReviewCommentParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    logger.info("Admin Review Comment API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": "You are not authorized to access this resource.",
            },
        )

    return await admin_review_comment_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )

@router.get(
    path="/comment-reports",
    description=(
        "Retrieve all reported comments for moderation.\n"
        "`Note: Only Admins can access this route.`"
    ),
)
async def admin_retrieve_comment_reports(
    req_params: AdminRetrieveCommentReportsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    logger.info("Admin Retrieve Comment Reports API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": "You are not authorized to access this resource.",
            },
        )

    return await admin_retrieve_comment_reports_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )

@router.post(
    path="/comment-reports/{report_id}/review",
    description=(
        "Review a reported comment (ignore or accept).\n"
        "`Note: Only Admins can access this route.`"
    ),
)
async def admin_review_comment_report(
    req_params: ReviewCommentReportParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    logger.info("Admin Review Comment Report API is being called")

    if authorized_user["user_role"] != UserRole.COS_ADMIN:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Forbidden access",
            error={
                "code": "FORBIDDEN",
                "details": "You are not authorized to access this resource.",
            },
        )

    return await admin_review_comment_report_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )
