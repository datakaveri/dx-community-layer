from datetime import datetime, timedelta
import math
from pydantic import Tag
from fastapi import status
import pytz
from sqlalchemy.orm import selectinload
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..middlewares.logging import logger
from ..services.search_services import format_tsquery
from ..schemas.default_schemas import AuthorizationData
from ..database.models import Discussion, DiscussionReview, DiscussionTag
from ..schemas.admin_requests import (
    AdminRetrieveDiscussionParams,
    AdminReviewDiscussionParams,
    TimeRangeEnum,
)
from ..schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ..schemas.admin_responses import AdminRetrieveDiscussionsResponseDiscussion


async def admin_retrieve_discussions_handler(
    req_params: AdminRetrieveDiscussionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves discussions for the admin panel based on the provided filters.

    Args:
        req_params (AdminRetrieveDiscussionParams): The request body containing the pagination and filters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved discussions and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(Discussion).options(
            selectinload(Discussion.user),
            selectinload(Discussion.discussion_tags).selectinload(
                Discussion.discussion_tags.property.mapper.class_.tag
            ),
        )

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("english", formatted_query)

            stmt = stmt.where(
                (Discussion.title_vector.op("@@")(ts_query))
                | (Discussion.sub_category_vector.op("@@")(ts_query))
            )

        # -----------------------
        # Apply dynamic filters
        # -----------------------
        for field, values in req_params.filters.model_dump().items():
            if values not in [None, []] and hasattr(Discussion, field):
                column = getattr(Discussion, field)
                if isinstance(values, list):
                    stmt = stmt.where(column.in_(values))
                elif isinstance(values, bool):
                    stmt = stmt.where(column.is_(values))

        # -----------------------
        # Time range filter (created_at)
        # -----------------------
        if req_params.filters.time_range:
            if (
                req_params.filters.time_range.start_date
                and req_params.filters.time_range.end_date
            ):
                start_date = datetime.strptime(
                    req_params.filters.time_range.start_date,
                    AdminRetrieveDiscussionParams.DATE_FORMAT,
                ).astimezone(pytz.UTC)
                end_date = datetime.strptime(
                    req_params.filters.time_range.end_date,
                    AdminRetrieveDiscussionParams.DATE_FORMAT,
                ).astimezone(pytz.UTC)
                stmt = stmt.where(Discussion.created_at.between(start_date, end_date))

        # -----------------------
        # Tag filter
        # -----------------------
        if req_params.filters.tags:
            stmt = stmt.where(
                Discussion.discussion_tags.any(
                    DiscussionTag.tag.has(Tag.name.in_(req_params.filters.tags))
                )
            )

        # -----------------------
        # Review history filter
        # -----------------------
        if getattr(req_params, "choice", None) == "review_history":
            reviewer_filter = exists().where(
                (DiscussionReview.discussion_id == Discussion.id)
                & (DiscussionReview.reviewer_id == authorized_user["id"])
            )
            stmt = stmt.where(reviewer_filter)

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(Discussion.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Sorting
        # -----------------------
        if req_params.sort_by and req_params.sort_order:
            if hasattr(Discussion, req_params.sort_by.value):
                sort_column = getattr(Discussion, req_params.sort_by.value)
                stmt = stmt.order_by(
                    sort_column.asc()
                    if req_params.sort_order == "asc"
                    else sort_column.desc()
                )

        # -----------------------
        # Pagination
        # -----------------------
        offset = (req_params.page - 1) * req_params.limit
        stmt = stmt.offset(offset).limit(req_params.limit)

        # -----------------------
        # Execute and fetch
        # -----------------------
        result = await db_session.execute(stmt)
        discussions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_discussions = [
            AdminRetrieveDiscussionsResponseDiscussion.model_validate(
                discussion
            ).model_dump()
            for discussion in discussions
        ]

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussions retrieved successfully",
            data=serialized_discussions,
            meta={
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": req_params.page,
                "limit": req_params.limit,
                "query": req_params.query,
            },
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to retrieve discussions",
            details="An error occurred while retrieving the discussion. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def admin_review_discussion_handler(
    req_params: AdminReviewDiscussionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Admin reviews a discussion based on the provided discussion ID.

    Args:
        req_params (AdminReviewDiscussionParams): The request body containing the discussion ID.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response indicating the result of the review operation.
    """
    logger.info(f"{authorized_user['email']} - Execution started")
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        discussion = await db_session.execute(
            select(Discussion).where(Discussion.id == req_params.discussion_id)
        )
        discussion = discussion.scalars().one_or_none()

        if not discussion:
            logger.error(f"{authorized_user['email']} - Discussion not found")
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The discussion does not exist. Please contact developers if the issue persists.",
                },
            )

        discussion.status = req_params.review_status.value

        new_review = DiscussionReview(
            discussion_id=req_params.discussion_id,
            reviewer_id=authorized_user["user_id"],
            comment=req_params.comment,
            updated_status=req_params.review_status.value,
        )

        db_session.add(new_review)
        discussion.updated_at = current_timestamp
        await db_session.commit()

        logger.info(f"{authorized_user['email']} - Discussion reviewed successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion reviewed successfully",
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to review discussion",
            details="An error occurred while reviewing the discussion. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
