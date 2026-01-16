from typing import List
import pytz
import math
from fastapi import status
from datetime import datetime, timedelta, time
from sqlalchemy.orm import selectinload
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...configs.env_config import env_config
from ...configs.s3_config import s3_client
from ...services.discussion.discussion_services import get_s3_file_metadata
from ...middlewares.logging import logger
from .search_services import format_tsquery
from ...schemas.default_schemas import AuthorizationData
from ...database.discussion.models import (
    CommentAttachment,
    Discussion,
    DiscussionReview,
    DiscussionTag,
    Tag,
    Comment,
    User,
)
from ...schemas.discussion.admin_requests import (
    AdminRetrieveDiscussionParams,
    AdminRetrieveDiscussionsChoices,
    AdminRetrieveDiscussionsSortByEnum,
    AdminReviewDiscussionParams,
    AdminRetrieveCommentsParams,
    AdminReviewCommentParams,
    RetrieveCommentsChoices,
    RetrieveCommentsSortByEnum,
)
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ...schemas.discussion.admin_responses import (
    AdminRetrieveCommentsSchema,
    AdminRetrieveDiscussionsResponseDiscussion,
)

from ...database.discussion.enums import CommentsStatusEnum


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
        # Subquery to get the latest review for each discussion
        latest_review_subquery = select(
            DiscussionReview.discussion_id,
            DiscussionReview.reviewer_id,
            DiscussionReview.created_at,
            func.row_number()
            .over(
                partition_by=DiscussionReview.discussion_id,
                order_by=DiscussionReview.created_at.desc(),
            )
            .label("rn"),
        ).subquery()

        stmt = (
            select(Discussion, latest_review_subquery.c.created_at)
            .distinct()
            .join(
                latest_review_subquery,
                latest_review_subquery.c.discussion_id == Discussion.id,
                isouter=True,
            )
            .where(
                (latest_review_subquery.c.rn == 1)
                | (latest_review_subquery.c.rn.is_(None))
            )
        )

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("simple", formatted_query)

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
                ).date()
                end_date = datetime.strptime(
                    req_params.filters.time_range.end_date,
                    AdminRetrieveDiscussionParams.DATE_FORMAT,
                ).date()

                start_dt = datetime.combine(start_date, time.min).replace(
                    tzinfo=pytz.UTC
                )

                end_dt = datetime.combine(end_date, time.min).replace(
                    tzinfo=pytz.UTC
                ) + timedelta(days=1)
                stmt = stmt.where(
                    Discussion.updated_at >= start_dt, Discussion.updated_at < end_dt
                )

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
        if req_params.choice == AdminRetrieveDiscussionsChoices.REVIEW_HISTORY:
            stmt = stmt.where(
                latest_review_subquery.c.reviewer_id == authorized_user["user_id"]
            )

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(Discussion.id.distinct()))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Sorting
        # -----------------------
        if req_params.sort_by and req_params.sort_order:
            if req_params.sort_by == AdminRetrieveDiscussionsSortByEnum.reviewed_at:
                stmt = stmt.order_by(
                    latest_review_subquery.c.created_at.asc()
                    if req_params.sort_order == "asc"
                    else latest_review_subquery.c.created_at.desc()
                )
            elif req_params.sort_by == AdminRetrieveDiscussionsSortByEnum.created_at:
                stmt = stmt.order_by(
                    Discussion.created_at.asc()
                    if req_params.sort_order == "asc"
                    else Discussion.created_at.desc()
                )
            elif req_params.sort_by == AdminRetrieveDiscussionsSortByEnum.updated_at:
                stmt = stmt.order_by(
                    Discussion.updated_at.asc()
                    if req_params.sort_order == "asc"
                    else Discussion.updated_at.desc()
                )

        # -----------------------
        # Pagination
        # -----------------------
        offset = (req_params.page - 1) * req_params.limit
        stmt = stmt.offset(offset).limit(req_params.limit)

        # -----------------------
        # Execute and fetch
        # -----------------------
        stmt = stmt.options(
            selectinload(Discussion.user),
            selectinload(Discussion.discussion_tags).selectinload(
                Discussion.discussion_tags.property.mapper.class_.tag
            ),
            selectinload(Discussion.discussion_reviews),
        )
        result = await db_session.execute(stmt)
        discussions = result.scalars().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_discussions = []

        for discussion in discussions:
            serialized_discussion = (
                AdminRetrieveDiscussionsResponseDiscussion.model_validate(
                    discussion
                ).model_dump(exclude={"reviewed_at"})
            )

            serialized_discussion["reviewed_at"] = (
                max(review.created_at for review in discussion.discussion_reviews)
                if discussion.discussion_reviews
                else None
            )

            serialized_discussions.append(serialized_discussion)

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
        # discussion.updated_at = current_timestamp
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


async def admin_retrieve_comments_handler(
    req_params: AdminRetrieveCommentsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves comments based on the provided request parameters.

    Args:
        req_params (AdminRetrievePendingCommentsParams): The request body containing the request parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved pending comments.
    """
    logger.info(f"{authorized_user['email']} - Fetch pending comments started")

    try:
        # -----------------------
        # Base selectable
        # -----------------------
        stmt = (
            select(Comment)
            .join(Discussion, Comment.discussion_id == Discussion.id)
            .join(User, Comment.user_id == User.id)
        )

        # -----------------------
        # Choice Filter
        # -----------------------
        if req_params.choice == RetrieveCommentsChoices.PENDING:
            stmt = stmt.where(Comment.status == CommentsStatusEnum.PENDING)
        else:
            stmt = stmt.where(
                Comment.status != CommentsStatusEnum.PENDING,
                Comment.approved_by == authorized_user["user_id"],
            )

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("simple", formatted_query)

            stmt = stmt.where(
                (Discussion.title_vector.op("@@")(ts_query))
                | (User.name_vector.op("@@")(ts_query))
            )

        # -----------------------
        # Filters
        # -----------------------
        if req_params.filters:
            if req_params.filters.discussion_type:
                stmt = stmt.where(
                    Discussion.type.in_(req_params.filters.discussion_type)
                )

            if req_params.filters.status:
                stmt = stmt.where(Comment.status.in_(req_params.filters.status))

            if req_params.filters.time_range:
                if (
                    req_params.filters.time_range.start_date
                    and req_params.filters.time_range.end_date
                ):
                    start_date = datetime.strptime(
                        req_params.filters.time_range.start_date,
                        AdminRetrieveDiscussionParams.DATE_FORMAT,
                    ).date()
                    end_date = datetime.strptime(
                        req_params.filters.time_range.end_date,
                        AdminRetrieveDiscussionParams.DATE_FORMAT,
                    ).date()

                    start_dt = datetime.combine(start_date, time.min).replace(
                        tzinfo=pytz.UTC
                    )

                    end_dt = datetime.combine(end_date, time.min).replace(
                        tzinfo=pytz.UTC
                    ) + timedelta(days=1)

                    if req_params.choice == RetrieveCommentsChoices.PENDING:
                        stmt = stmt.where(
                            Comment.created_at >= start_dt, Comment.created_at < end_dt
                        )
                    else:
                        stmt = stmt.where(
                            Comment.created_at >= start_dt,
                            Comment.approved_at < end_dt,
                            Comment.approved_at != None,
                        )

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(Comment.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Sorting
        # -----------------------
        if req_params.sort_by == RetrieveCommentsSortByEnum.DISCUSSION_TITLE:
            sort_column = Discussion.title
        elif req_params.sort_by == RetrieveCommentsSortByEnum.APPROVED_AT:
            sort_column = Comment.approved_at
        else:
            sort_column = Comment.created_at

        if req_params.sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc().nullslast(), Comment.id.asc())
        else:
            stmt = stmt.order_by(sort_column.desc().nullslast(), Comment.id.desc())

        # -----------------------
        # Pagination
        # -----------------------
        offset = (req_params.page - 1) * req_params.limit
        stmt = stmt.offset(offset).limit(req_params.limit)

        # -----------------------
        # Execute and fetch
        # -----------------------
        stmt = stmt.options(
            selectinload(Comment.user),
            selectinload(Comment.comment_attachments),
            selectinload(Comment.discussion),
            selectinload(Comment.approved_by_user),
        )
        result = await db_session.execute(stmt)
        comments = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_comments = [
            AdminRetrieveCommentsSchema.model_validate(comment).model_dump()
            for comment in comments
        ]

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Pending comments retrieved successfully",
            data=serialized_comments,
            meta={
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": req_params.page,
                "limit": req_params.limit,
            },
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to retrieve pending comments",
            details="An error occurred while retrieving pending comments. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def admin_review_comment_handler(
    req_params: AdminReviewCommentParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Review a comment for approval or rejection.

    Args:
        req_params (AdminReviewCommentParams): The request body containing the request parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the reviewed comment and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Review comment started")
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        result = await db_session.execute(
            select(Comment).where(Comment.id == req_params.comment_id)
        )
        comment_obj = result.scalars().one_or_none()

        if not comment_obj:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Comment not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The comment does not exist. Please contact developers if the issue persists.",
                },
            )

        # Update status
        comment_obj.status = req_params.status
        comment_obj.comment = req_params.comment

        if req_params.attachments.remove:
            for attachment_id in req_params.attachments.remove:
                attachment_result = await db_session.execute(
                    select(CommentAttachment).where(
                        CommentAttachment.id == attachment_id,
                        CommentAttachment.comment_id == comment_obj.id,
                    )
                )
                attachment_obj = attachment_result.scalars().one_or_none()
                if attachment_obj:
                    db_session.delete(attachment_obj)

        if req_params.attachments.add:
            attachment_objs: List[CommentAttachment] = []
            for source_s3_key in req_params.attachments.add:
                metadata = get_s3_file_metadata(source_s3_key)

                if "error" in metadata:
                    logger.error(
                        f"{authorized_user['email']} - Error fetching metadata for {source_s3_key}: {metadata['error']}"
                    )
                    await db_session.rollback()
                    return CustomBackendError(
                        message="Discussion creation failed",
                        details="An error occurred while creating the discussion. Please contact developers if the issue persists.",
                    )

                # build permanent key and copy object to permanent location
                permanent_s3_key = f"private/{comment_obj.discussion_id}/comments/{comment_obj.id}/{metadata['file_name']}"

                try:
                    s3_client.copy_object(
                        Bucket=env_config.DISCUSSION_AWS_S3_BUCKET,
                        CopySource=f"{env_config.DISCUSSION_AWS_S3_BUCKET}/{source_s3_key}",
                        Key=permanent_s3_key,
                    )
                except Exception as s3_exc:
                    logger.exception(
                        f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                    )
                    await db_session.rollback()
                    return CustomBackendError(
                        message="Discussion comment creation failed",
                        details="An error occurred while creating the discussion comment. Please contact developers if the issue persists.",
                    )

                attachment_objs.append(
                    CommentAttachment(
                        comment_id=comment_obj.id,
                        attachment_metadata=metadata,
                        s3_key=permanent_s3_key,
                    )
                )

            if attachment_objs:
                db_session.add_all(attachment_objs)

        comment_obj.approved_by = authorized_user["user_id"]
        comment_obj.approved_at = current_timestamp

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Comment reviewed successfully",
        )

    except Exception as e:
        await db_session.rollback()

        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to review comment",
            details="An error occurred while reviewing the comment. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
