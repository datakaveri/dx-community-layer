import math
import uuid
import pytz
from fastapi import status
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import selectinload
from sqlalchemy import delete, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.discussion.discussion_requests import (
    AddUpdateDiscussionReactionParams,
    CreateDiscussionParams,
    DiscussionActions,
    DiscussionActionsParams,
    RetrieveDiscussionChoices,
    RetrieveDiscussionParams,
    RetrieveDiscussionsSortByEnum,
    UpdateDiscussionParams,
)
from ...middlewares.logging import logger
from ...database.discussion.models import (
    BookmarkedDiscussion,
    DeletedDiscussion,
    Discussion,
    DiscussionAttachment,
    DiscussionReaction,
    DiscussionTag,
    DiscussionVote,
    PinnedDiscussion,
    Tag,
    User,
)
from ...configs.s3_config import s3_client
from ...configs.env_config import env_config
from ...database.discussion.enums import DiscussionsStatusEnum, DiscussionsTypeEnum
from ...schemas.default_schemas import AuthorizationData, UserRole
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ...schemas.discussion.discussion_responses import (
    GetPopularTagsSuccessfulResponseData,
    RecentBookmarkedDiscussion,
    RetrieveDiscussionByIDResponseDiscussion,
    RetrieveDiscussionsResponseDiscussion,
    UserSchema,
)
from ...database.discussion.models import DiscussionReview

def _build_permanent_s3_key(discussion_id: uuid.UUID, file_name: str) -> str:
    return f"private/{discussion_id}/content/{file_name}"


def get_s3_file_metadata(object_key: str) -> dict:
    try:
        response = s3_client.head_object(
            Bucket=env_config.DISCUSSION_S3_BUCKET, Key=object_key
        )

        metadata = {
            "file_name": object_key.split("/")[-1],
            "content_type": response.get("ContentType"),
            "content_length_bytes": response.get("ContentLength"),
            "size_in_kb": round(response.get("ContentLength") / 1024, 2),
        }

        return metadata

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"error": str(e)}


async def retrieve_discussion_by_id_handler(
    discussion_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves a discussion by its ID.

    Args:
        discussion_id (uuid.UUID): The ID of the discussion to retrieve.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved discussion and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        stmt = select(Discussion).where(Discussion.id == discussion_id)

        stmt = stmt.options(
            selectinload(Discussion.user),
            selectinload(Discussion.discussion_tags).selectinload(
                Discussion.discussion_tags.property.mapper.class_.tag
            ),
            selectinload(Discussion.discussion_attachments),
            selectinload(Discussion.bookmarked_discussions),
            selectinload(Discussion.pinned_discussions),
            selectinload(Discussion.discussion_votes),
            selectinload(Discussion.discussion_reviews).selectinload(
                Discussion.discussion_reviews.property.mapper.class_.reviewer
            ),
            selectinload(Discussion.discussion_reactions).selectinload(
                Discussion.discussion_reactions.property.mapper.class_.user
            ),
        )

        res = await db_session.execute(stmt)
        discussion = res.scalars().first()

        if not discussion:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion not found",
                error={
                    "code": "NOT_FOUND",
                    "message": "The discussion does not exist. Please contact developers if the issue persists.",
                },
            )

        if (
            authorized_user["user_role"] != UserRole.COS_ADMIN
            and authorized_user["user_id"] != discussion.user_id
        ) and discussion.status != DiscussionsStatusEnum.APPROVED:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to view this discussion. Please contact developers if the issue persists.",
                },
            )

        # Serialize
        serialized_discussion = RetrieveDiscussionByIDResponseDiscussion.model_validate(
            discussion
        ).model_dump()

        latest_review_time = (
            max(r.created_at for r in discussion.discussion_reviews)
            if discussion.discussion_reviews
            else None
        )

        if discussion.status == DiscussionsStatusEnum.PENDING:
            # User resubmitted, ignore old admin review timestamp
            serialized_discussion["published_time"] = discussion.updated_at
        else:
            serialized_discussion["published_time"] = (
                latest_review_time or discussion.updated_at or discussion.created_at
            )

        # compute reactions
        reactions_summary = {}
        user_reaction = {}

        for r in getattr(discussion, "discussion_reactions", []):
            reactions_summary[r.emoji_code] = reactions_summary.get(r.emoji_code, 0) + 1
            if r.user_id == authorized_user["user_id"]:
                user_reaction = {"emoji_code": r.emoji_code}

        serialized_discussion["reactions"] = {
            "emojis": reactions_summary,
            "user_reaction": user_reaction,
        }

        # compute votes
        serialized_discussion["votes"] = len(
            getattr(discussion, "discussion_votes", [])
        )

        # compute flags
        is_bookmarked = any(
            b.user_id == authorized_user["user_id"]
            for b in getattr(discussion, "bookmarked_discussions", [])
        )
        is_pinned = any(
            p.user_id == authorized_user["user_id"]
            for p in getattr(discussion, "pinned_discussions", [])
        )
        is_voted = any(
            v.user_id == authorized_user["user_id"]
            for v in getattr(discussion, "discussion_votes", [])
        )

        serialized_discussion["is_bookmarked"] = is_bookmarked
        serialized_discussion["is_pinned"] = is_pinned
        serialized_discussion["is_voted"] = is_voted

        logger.info(f"{authorized_user['email']} - Discussion retrieved successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion retrieved successfully",
            data=serialized_discussion,
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Discussion retrieval failed",
            details="An error occurred while retrieving the discussion. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def retrieve_discussions_handler(
    req_params: RetrieveDiscussionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves discussions based on the provided choice and filters.

    Args:
        req_params (RetrieveDiscussionParams): Request params including filters, choice, pagination, etc.
        authorized_user (AuthorizationData): The authenticated user's data.
        db_session (AsyncSession): Async SQLAlchemy session.

    Returns:
        CustomJSONResponse: Discussions and pinned discussions with metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        user_id = authorized_user["user_id"]
        pinned_discussions: list[Discussion] = []

        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(Discussion)

        # -----------------------
        # Apply choice filters
        # -----------------------
        if req_params.choice == RetrieveDiscussionChoices.OWNED:
            stmt = stmt.where(Discussion.user_id == user_id)
        elif req_params.choice == RetrieveDiscussionChoices.BOOKMARKED:
            stmt = stmt.where(
                Discussion.bookmarked_discussions.any(
                    BookmarkedDiscussion.user_id == user_id,
                )
            )

        # -----------------------
        # Approved filter for non-owned
        # -----------------------
        if req_params.choice == RetrieveDiscussionChoices.ALL:
            stmt = stmt.where(Discussion.status == DiscussionsStatusEnum.APPROVED)

        # -----------------------
        # Apply dynamic filters
        # -----------------------
        if req_params.filters:
            for field, values in req_params.filters.model_dump().items():
                # Skip tags and sub_category_id as they are handled separately
                if field in ["tags", "sub_category_id"]:
                    continue
                if values not in [None, []] and hasattr(Discussion, field):
                    column = getattr(Discussion, field)
                    if isinstance(values, list):
                        stmt = stmt.where(column.in_(values))
                    elif isinstance(values, bool):
                        stmt = stmt.where(column.is_(values))

        # -----------------------
        # Tag filter
        # -----------------------
        if req_params.filters and req_params.filters.tags:
            stmt = stmt.where(
                Discussion.discussion_tags.any(
                    DiscussionTag.tag.has(Tag.name.in_(req_params.filters.tags))
                )
            )

        # -----------------------
        # Sub-category ID filter
        # -----------------------
        if req_params.filters and req_params.filters.sub_category_id is not None:
            stmt = stmt.where(
                Discussion.sub_category_id == req_params.filters.sub_category_id
            )

        # -----------------------
        # Pinned discussions
        # -----------------------
        if req_params.pinned:
            pinned_stmt = (
                select(Discussion)
                .join(
                    PinnedDiscussion,
                    PinnedDiscussion.discussion_id == Discussion.id,
                )
                .where(
                    PinnedDiscussion.user_id == user_id,
                    Discussion.status == DiscussionsStatusEnum.APPROVED,
                )
                .order_by(PinnedDiscussion.pinned_at.desc())
                .options(
                    selectinload(Discussion.user),
                    selectinload(Discussion.discussion_votes),
                    selectinload(Discussion.bookmarked_discussions),
                    selectinload(Discussion.pinned_discussions),
                )
            )

            # Apply dynamic filters to pinned discussions (same as main query)
            if req_params.filters:
                for field, values in req_params.filters.model_dump().items():
                    # Skip tags and sub_category_id as they are handled separately
                    if field in ["tags", "sub_category_id"]:
                        continue
                    if values not in [None, []] and hasattr(Discussion, field):
                        column = getattr(Discussion, field)
                        if isinstance(values, list):
                            pinned_stmt = pinned_stmt.where(column.in_(values))
                        elif isinstance(values, bool):
                            pinned_stmt = pinned_stmt.where(column.is_(values))
            
            if req_params.filters and req_params.filters.tags:
                pinned_stmt = pinned_stmt.where(
                    Discussion.discussion_tags.any(
                        DiscussionTag.tag.has(Tag.name.in_(req_params.filters.tags))
                    )
                )

            if req_params.filters and req_params.filters.sub_category_id is not None:
                pinned_stmt = pinned_stmt.where(
                    Discussion.sub_category_id == req_params.filters.sub_category_id
                )

            result = await db_session.execute(pinned_stmt)
            pinned_discussions = result.scalars().unique().all()

            pinned_ids = [d.id for d in pinned_discussions]
            if pinned_ids:
                stmt = stmt.where(Discussion.id.not_in(pinned_ids))

        # -----------------------
        # Subquery: count votes per discussion
        # -----------------------
        votes_subq = (
            select(
                DiscussionVote.discussion_id,
                func.count(DiscussionVote.id).label("vote_count"),
            )
            .group_by(DiscussionVote.discussion_id)
            .subquery()
        )

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
        
        latest_review_subq = (
            select(
                DiscussionReview.discussion_id,
                func.max(DiscussionReview.created_at).label("approved_time"),
            )
            .group_by(DiscussionReview.discussion_id)
            .subquery()
        )

        stmt = stmt.outerjoin(
            latest_review_subq,
            Discussion.id == latest_review_subq.c.discussion_id,
        )
        sort_time_expr = case(
            (
                Discussion.status == DiscussionsStatusEnum.PENDING,
                Discussion.updated_at,
            ),
            else_=func.coalesce(
                latest_review_subq.c.approved_time,
                Discussion.updated_at,
                Discussion.created_at,
            ),
        )

        if req_params.sort_by == RetrieveDiscussionsSortByEnum.NEWEST:
            stmt = stmt.order_by(sort_time_expr.desc())

        elif req_params.sort_by == RetrieveDiscussionsSortByEnum.OLDEST:
            stmt = stmt.order_by(sort_time_expr.asc())

        elif req_params.sort_by == RetrieveDiscussionsSortByEnum.HOTTEST:
            stmt = stmt.outerjoin(
                votes_subq, Discussion.id == votes_subq.c.discussion_id
            ).order_by(
                func.coalesce(votes_subq.c.vote_count, 0).desc(),
                Discussion.updated_at.desc(),
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
            selectinload(Discussion.discussion_votes),
            selectinload(Discussion.pinned_discussions),
            selectinload(Discussion.bookmarked_discussions),
            selectinload(Discussion.discussion_reviews).selectinload(
                Discussion.discussion_reviews.property.mapper.class_.reviewer
            ),
        )
        result = await db_session.execute(stmt)
        discussions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_discussions = []
        for d in discussions:
            # compute flags
            is_bookmarked = any(
                b.user_id == user_id for b in getattr(d, "bookmarked_discussions", [])
            )
            is_pinned = any(
                p.user_id == user_id for p in getattr(d, "pinned_discussions", [])
            )
            is_voted = any(
                v.user_id == user_id for v in getattr(d, "discussion_votes", [])
            )

            # compute vote count via relationship
            votes = len(getattr(d, "discussion_votes", []))

            base = RetrieveDiscussionsResponseDiscussion.model_validate(d).model_dump(
                exclude={"votes"}
            )
            latest_review_time = (
                max(r.created_at for r in d.discussion_reviews)
                if d.discussion_reviews
                else None
            )
            if d.status == DiscussionsStatusEnum.PENDING:
                # User has (re)submitted - ignore old admin review time
                base["published_time"] = d.updated_at
            else:
                base["published_time"] = latest_review_time or d.updated_at or d.created_at
            base["votes"] = votes
            base["is_bookmarked"] = is_bookmarked
            base["is_pinned"] = is_pinned
            base["is_voted"] = is_voted
            serialized_discussions.append(base)

        serialized_pinned = []
        for d in pinned_discussions:
            votes = len(getattr(d, "discussion_votes", []))

            base = RetrieveDiscussionsResponseDiscussion.model_validate(d).model_dump(
                exclude={"votes"}
            )
            base["votes"] = votes
            base["is_bookmarked"] = True
            base["is_pinned"] = True
            serialized_pinned.append(base)

        logger.info(f"{authorized_user['email']} - Discussions retrieved successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussions retrieved successfully",
            data={
                "discussions": serialized_discussions,
                "pinned_discussions": serialized_pinned,
            },
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
            message="Discussion retrieval failed",
            details="An error occurred while retrieving discussions. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def create_discussion_handler(
    req_params: CreateDiscussionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Creates a new discussion for the authenticated user.

    Args:
        req_params (CreateDiscussionParams): The request body containing the discussion details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created discussion details and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Duplicate check (async)
        # -----------------------
        q = select(Discussion).where(
            Discussion.user_id == authorized_user["user_id"],
            Discussion.title == req_params.title,
            Discussion.type == req_params.type,
            Discussion.category == req_params.category,
            Discussion.sub_category == req_params.sub_category,
            Discussion.sub_category_id == req_params.sub_category_id,
        )
        res = await db_session.execute(q)
        existing_discussion = res.scalars().first()

        if existing_discussion:
            logger.info(f"{authorized_user['email']} - Discussion already exists")
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_409_CONFLICT,
                message="Discussion already exists",
                error={
                    "code": "CONFLICT",
                    "details": (
                        "A discussion with the same title, type, category, and sub-category already exists. "
                        "Please use a different title, type, category, or sub-category."
                    ),
                },
            )

        # -----------------------
        # Create Discussion
        # -----------------------
        new_discussion = Discussion(
            user_id=authorized_user["user_id"],
            title=req_params.title,
            type=req_params.type,
            category=req_params.category,
            sub_category=req_params.sub_category,
            sub_category_id=req_params.sub_category_id,
            content=req_params.content,
        )

        db_session.add(new_discussion)
        await db_session.flush()

        # -----------------------
        # Handle Tags (bulk)
        # -----------------------
        tag_names: List[str] = list(dict.fromkeys(req_params.tags or []))
        tag_map: Dict[str, Tag] = {}

        if tag_names:
            # fetch existing tags
            q = select(Tag).where(Tag.name.in_(tag_names))
            res = await db_session.execute(q)
            existing_tags: List[Tag] = res.scalars().all()
            for t in existing_tags:
                tag_map[t.name] = t

            # create missing tags
            missing_names = [n for n in tag_names if n not in tag_map]
            new_tag_objs: List[Tag] = []
            for name in missing_names:
                t = Tag(name=name)
                new_tag_objs.append(t)
                db_session.add(t)

            if new_tag_objs:
                await db_session.flush()
                for t in new_tag_objs:
                    tag_map[t.name] = t

            # create DiscussionTag rows in bulk
            discussion_tag_objs: List[DiscussionTag] = []
            for name in tag_names:
                tag_obj = tag_map.get(name)
                if tag_obj:
                    discussion_tag_objs.append(
                        DiscussionTag(
                            discussion_id=new_discussion.id, tag_id=tag_obj.id
                        )
                    )

            if discussion_tag_objs:
                db_session.add_all(discussion_tag_objs)

        # -----------------------
        # Handle Attachments (copy in S3 -> store permanent key)
        # -----------------------
        if req_params.attachments:
            attachment_objs: List[DiscussionAttachment] = []
            for source_s3_key in req_params.attachments:
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
                permanent_s3_key = (
                    f"private/{new_discussion.id}/attachments/{metadata['file_name']}"
                )

                try:
                    s3_client.copy_object(
                        Bucket=env_config.DISCUSSION_S3_BUCKET,
                        CopySource=f"{env_config.DISCUSSION_S3_BUCKET}/{source_s3_key}",
                        Key=permanent_s3_key,
                    )
                except Exception as s3_exc:
                    logger.exception(
                        f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                    )
                    await db_session.rollback()
                    return CustomBackendError(
                        message="Discussion creation failed",
                        details="An error occurred while creating the discussion. Please contact developers if the issue persists.",
                    )

                attachment_objs.append(
                    DiscussionAttachment(
                        discussion_id=new_discussion.id,
                        attachment_metadata=metadata,
                        s3_key=permanent_s3_key,  # store permanent key
                    )
                )

            if attachment_objs:
                db_session.add_all(attachment_objs)

        # -----------------------
        # Finalize transaction
        # -----------------------
        await db_session.commit()

        logger.info(
            f"{authorized_user['email']} - Discussion created successfully (id={new_discussion.id})"
        )
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Discussion created successfully",
            data={"discussion_id": new_discussion.id},
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Discussion creation failed",
            details="An error occurred while creating the discussion. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def update_discussion_handler(
    req_params: UpdateDiscussionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Update a discussion's title, content, and tags. Replaces tags if provided.
    Only the owner or an org admin can update.
    """
    logger.info(f"{authorized_user['email']} - Update Discussion Execution started")
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        # Get discussion
        discussion = await db_session.execute(
            select(Discussion).where(Discussion.id == req_params.discussion_id)
        )
        discussion = discussion.scalars().first()

        if not discussion:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion not found",
                error={
                    "code": "NOT_FOUND",
                    "message": "The discussion does not exist. Please contact developers if the issue persists.",
                },
            )

        # Authorization: Owner
        if discussion.user_id != authorized_user["user_id"]:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to update this discussion. Please contact developers if the issue persists.",
                },
            )

        # Title
        if req_params.title:
            discussion.title = req_params.title

        # Category
        if req_params.category:
            discussion.category = req_params.category

        # Sub-category
        if req_params.sub_category:
            discussion.sub_category = req_params.sub_category

        # Sub-category ID
        if req_params.sub_category_id:
            discussion.sub_category_id = req_params.sub_category_id

        # Content
        if req_params.content:
            discussion.content = req_params.content

        # Tags
        if req_params.tags:
            if req_params.tags.add:
                for new_tag in req_params.tags.add:
                    # Check if the tag already exists
                    tag = await db_session.execute(
                        select(Tag).where(Tag.name == new_tag)
                    )
                    tag = tag.scalars().first()

                    if not tag:
                        tag = Tag(name=new_tag)
                        db_session.add(tag)
                        await db_session.flush()

                    discussion_tag = DiscussionTag(
                        tag_id=tag.id,
                        discussion_id=discussion.id,
                    )
                    db_session.add(discussion_tag)

            if req_params.tags.remove:
                # Remove tags by name directly
                await db_session.execute(
                    delete(DiscussionTag)
                    .where(DiscussionTag.discussion_id == discussion.id)
                    .where(
                        DiscussionTag.tag_id.in_(
                            select(Tag.id).where(Tag.name.in_(req_params.tags.remove))
                        )
                    )
                )

        # Added attachments
        if req_params.added_attachments:
            attachment_objs: List[DiscussionAttachment] = []

            for attachment_key in req_params.added_attachments:
                metadata = get_s3_file_metadata(attachment_key)

                if "error" in metadata:
                    logger.error(
                        f"{authorized_user['email']} - Error fetching metadata for {attachment_key}: {metadata['error']}"
                    )
                    await db_session.rollback()
                    return CustomBackendError(
                        message="Discussion update failed",
                        details="An error occurred while updating the discussion. Please contact developers if the issue persists.",
                    )

                # build permanent key and copy object to permanent location
                permanent_s3_key = _build_permanent_s3_key(
                    discussion_id=discussion.id, file_name=metadata["file_name"]
                )

                try:
                    s3_client.copy_object(
                        Bucket=env_config.DISCUSSION_S3_BUCKET,
                        CopySource=f"{env_config.DISCUSSION_S3_BUCKET}/{attachment_key}",
                        Key=permanent_s3_key,
                    )
                except Exception as s3_exc:
                    logger.exception(
                        f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                    )
                    await db_session.rollback()
                    return CustomBackendError(
                        message="Discussion update failed",
                        details="An error occurred while updating the discussion. Please contact developers if the issue persists.",
                    )

                attachment_objs.append(
                    DiscussionAttachment(
                        discussion_id=discussion.id,
                        attachment_metadata=metadata,
                        s3_key=permanent_s3_key,  # store permanent key
                    )
                )

            if attachment_objs:
                db_session.add_all(attachment_objs)

        if discussion.status == DiscussionsStatusEnum.CHANGES_REQUIRED:
            discussion.status = DiscussionsStatusEnum.PENDING

        discussion.updated_at = current_timestamp

        await db_session.commit()

        logger.info(f"{authorized_user['email']} - Discussion updated successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion updated successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Discussion update failed",
            details="An error occurred while updating the discussion. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(
            f"{authorized_user['email']} - Update Discussion Execution completed"
        )


async def discussion_actions_handler(
    req_params: DiscussionActionsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Async handler for discussion actions: bookmark, unbookmark, pin, unpin.

    Behavior (strict, no toggle):
      - bookmark: create BookmarkedDiscussion (409 if already exists)
      - unbookmark: delete BookmarkedDiscussion (404 if not exists)
      - pin: create PinnedDiscussion (409 if already exists)
      - unpin: delete PinnedDiscussion (404 if not exists)
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # Validate discussion exists
        q = select(Discussion).where(Discussion.id == req_params.discussion_id)
        res = await db_session.execute(q)
        discussion = res.scalars().one_or_none()

        if discussion is None:
            logger.info(
                f"{authorized_user['email']} - Discussion not found: {req_params.discussion_id}"
            )
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The discussion you are trying to perform an action does not exist. Please try again later or contact support if the issue persists.",
                },
            )

        user_id = authorized_user["user_id"]

        # --- BOOKMARK ---
        if req_params.action is DiscussionActions.BOOKMARK:
            q = select(BookmarkedDiscussion).where(
                BookmarkedDiscussion.discussion_id == req_params.discussion_id,
                BookmarkedDiscussion.user_id == user_id,
            )
            res = await db_session.execute(q)
            existing = res.scalars().one_or_none()
            if existing:
                # conflict
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_409_CONFLICT,
                    message="Discussion already bookmarked",
                    error={
                        "code": "CONFLICT",
                        "details": "The discussion has already been bookmarked. Please try again later or contact support if the issue persists.",
                    },
                )

            new_bm = BookmarkedDiscussion(
                discussion_id=req_params.discussion_id,
                user_id=user_id,
                is_active=True,
            )
            db_session.add(new_bm)
            await db_session.commit()
            logger.info(
                f"{authorized_user['email']} - Bookmarked discussion {req_params.discussion_id}"
            )
            return CustomJSONResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Discussion bookmarked successfully",
            )

        # --- UNBOOKMARK ---
        if req_params.action is DiscussionActions.UNBOOKMARK:
            q = select(BookmarkedDiscussion).where(
                BookmarkedDiscussion.discussion_id == req_params.discussion_id,
                BookmarkedDiscussion.user_id == user_id,
            )
            res = await db_session.execute(q)
            existing = res.scalars().one_or_none()
            if not existing:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Bookmark not found",
                    error={
                        "code": "NOT_FOUND",
                        "details": "The discussion is not bookmarked. Please try again later or contact support if the issue persists.",
                    },
                )

            # delete the bookmark row
            await db_session.execute(
                delete(BookmarkedDiscussion).where(
                    BookmarkedDiscussion.id == existing.id
                )
            )
            await db_session.commit()
            logger.info(
                f"{authorized_user['email']} - Unbookmarked discussion {req_params.discussion_id}"
            )
            return CustomJSONResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Discussion unbookmarked successfully",
            )

        # --- PIN ---
        if req_params.action is DiscussionActions.PIN:
            q = select(PinnedDiscussion).where(
                PinnedDiscussion.discussion_id == req_params.discussion_id,
                PinnedDiscussion.user_id == user_id,
            )
            res = await db_session.execute(q)
            existing = res.scalars().one_or_none()
            if existing:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_409_CONFLICT,
                    message="Discussion already pinned",
                    error={
                        "code": "CONFLICT",
                        "details": "The discussion has already been pinned. Please try again later or contact support if the issue persists.",
                    },
                )

            new_pin = PinnedDiscussion(
                discussion_id=req_params.discussion_id,
                user_id=user_id,
            )
            db_session.add(new_pin)
            await db_session.commit()
            logger.info(
                f"{authorized_user['email']} - Pinned discussion {req_params.discussion_id}"
            )
            return CustomJSONResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Discussion pinned successfully",
            )

        # --- UNPIN ---
        if req_params.action is DiscussionActions.UNPIN:
            q = select(PinnedDiscussion).where(
                PinnedDiscussion.discussion_id == req_params.discussion_id,
                PinnedDiscussion.user_id == user_id,
            )
            res = await db_session.execute(q)
            existing = res.scalars().one_or_none()
            if not existing:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Pin not found",
                    error={
                        "code": "NOT_FOUND",
                        "details": "The discussion is not pinned. Please try again later or contact support if the issue persists.",
                    },
                )

            await db_session.execute(
                delete(PinnedDiscussion).where(PinnedDiscussion.id == existing.id)
            )
            await db_session.commit()
            logger.info(
                f"{authorized_user['email']} - Unpinned discussion {req_params.discussion_id}"
            )
            return CustomJSONResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Discussion unpinned successfully",
            )

    except Exception as e:
        await db_session.rollback()
        logger.exception(
            f"{authorized_user['email']} - Error during discussion action: {str(e)}"
        )
        return CustomBackendError(
            message="Discussion action failed",
            details="An error occurred while performing the discussion action. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def add_update_discussion_reaction_handler(
    req_params: AddUpdateDiscussionReactionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Handles adding or updating a reaction to a discussion.
    Supports either emoji reaction or vote reaction.
    """

    logger.info(f"{authorized_user['email']} - Execution started")
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        discussion = (
            (
                await db_session.execute(
                    select(Discussion).filter(Discussion.id == req_params.discussion_id)
                )
            )
            .scalars()
            .one_or_none()
        )

        if not discussion:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The discussion does not exist. Please contact developers if the issue persists.",
                },
            )

        existing_reaction = (
            (
                await db_session.execute(
                    select(DiscussionReaction).filter(
                        DiscussionReaction.discussion_id == req_params.discussion_id,
                        DiscussionReaction.user_id == authorized_user["user_id"],
                    )
                )
            )
            .scalars()
            .one_or_none()
        )

        if existing_reaction:
            existing_reaction.emoji_code = req_params.emoji_code
            existing_reaction.emoji_timestamp = current_timestamp

        else:
            new_reaction = DiscussionReaction(
                discussion_id=req_params.discussion_id,
                user_id=authorized_user["user_id"],
                emoji_code=req_params.emoji_code,
                emoji_timestamp=current_timestamp,
            )
            db_session.add(new_reaction)

        await db_session.commit()

        logger.info(
            f"{authorized_user['email']} - Discussion reaction added/updated successfully"
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion reaction added/updated successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Discussion reaction failed",
            details="An error occurred while adding/updating the discussion reaction. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def delete_discussion_reaction_handler(
    discussion_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Deletes a discussion reaction if the authorized user is the creator.
    Records it in DeletedDiscussionReaction table.

    Args:
        discussion_id (uuid.UUID): ID of the discussion reaction to delete
        authorized_user (AuthorizationData): Authenticated user details
        db_session (AsyncSession): Async SQLAlchemy session

    Returns:
        CustomJSONResponse: Success or error response
    """
    logger.info(
        f"{authorized_user['email']} - Delete Discussion Reaction Execution started"
    )

    try:
        # Fetch discussion reaction
        result = await db_session.execute(
            select(DiscussionReaction).filter(
                DiscussionReaction.discussion_id == discussion_id,
                DiscussionReaction.user_id == authorized_user["user_id"],
            )
        )
        discussion_reaction = result.scalars().one_or_none()

        if not discussion_reaction:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion reaction not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The discussion reaction does not exist. Please contact developers if the issue persists.",
                },
            )

        # Delete discussion reaction
        await db_session.execute(
            delete(DiscussionReaction).filter(
                DiscussionReaction.discussion_id == discussion_id,
                DiscussionReaction.user_id == authorized_user["user_id"],
            )
        )

        await db_session.commit()

        logger.info(
            f"{authorized_user['email']} - Discussion reaction deleted successfully"
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion reaction deleted successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Discussion reaction deletion failed",
            details="An error occurred while deleting the discussion reaction. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def add_discussion_vote_handler(
    discussion_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Adds a vote to a discussion.

    Args:
        discussion_id (uuid.UUID): ID of the discussion to vote on
        authorized_user (AuthorizationData): Authenticated user details
        db_session (AsyncSession): Async SQLAlchemy session

    Returns:
        CustomJSONResponse: Success or error response
    """
    logger.info(f"{authorized_user['email']} - Add Discussion Vote Execution started")

    try:
        discussion = (
            (
                await db_session.execute(
                    select(Discussion).filter(Discussion.id == discussion_id)
                )
            )
            .scalars()
            .one_or_none()
        )

        if not discussion:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The discussion does not exist. Please contact developers if the issue persists.",
                },
            )

        # Check if the user has already voted
        existing_vote = (
            (
                await db_session.execute(
                    select(DiscussionVote).filter(
                        DiscussionVote.discussion_id == discussion_id,
                        DiscussionVote.user_id == authorized_user["user_id"],
                    )
                )
            )
            .scalars()
            .one_or_none()
        )

        if existing_vote:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_409_CONFLICT,
                message="Discussion already voted",
                error={
                    "code": "CONFLICT",
                    "details": "You have already voted for this discussion. Please try again later or contact support if the issue persists.",
                },
            )

        discussion_vote = DiscussionVote(
            discussion_id=discussion_id, user_id=authorized_user["user_id"]
        )

        db_session.add(discussion_vote)
        await db_session.commit()

        logger.info(f"{authorized_user['email']} - Discussion vote added successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Discussion vote added successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Discussion vote failed",
            details="An error occurred while adding the discussion vote. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def delete_discussion_vote_handler(
    discussion_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Deletes a discussion vote if the authorized user is the creator.
    Records it in DeletedDiscussionVote table.

    Args:
        discussion_id (uuid.UUID): ID of the discussion vote to delete
        authorized_user (AuthorizationData): Authenticated user details
        db_session (AsyncSession): Async SQLAlchemy session

    Returns:
        CustomJSONResponse: Success or error response
    """
    logger.info(
        f"{authorized_user['email']} - Delete Discussion Vote Execution started"
    )

    try:
        discussion_vote = (
            (
                await db_session.execute(
                    select(DiscussionVote).filter(
                        DiscussionVote.discussion_id == discussion_id,
                        DiscussionVote.user_id == authorized_user["user_id"],
                    )
                )
            )
            .scalars()
            .one_or_none()
        )

        if not discussion_vote:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion vote not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The discussion vote does not exist. Please contact developers if the issue persists.",
                },
            )

        # Delete discussion vote
        await db_session.execute(
            delete(DiscussionVote).filter(
                DiscussionVote.discussion_id == discussion_id,
                DiscussionVote.user_id == authorized_user["user_id"],
            )
        )

        await db_session.commit()

        logger.info(
            f"{authorized_user['email']} - Discussion vote deleted successfully"
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion vote deleted successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to delete discussion vote",
            details="An error occurred while deleting the discussion vote. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def delete_discussion_handler(
    discussion_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Deletes a discussion if the authorized user is the creator.
    Records it in DeletedDiscussion along with cleanup of related records.

    Args:
        discussion_id (uuid.UUID): ID of the discussion to delete
        authorized_user (AuthorizationData): Authenticated user details
        db_session (AsyncSession): Async SQLAlchemy session

    Returns:
        CustomJSONResponse: Success or error response
    """
    logger.info(f"{authorized_user['email']} - Delete Discussion Execution started")

    try:
        # Fetch discussion with related data
        result = await db_session.execute(
            select(Discussion).filter(Discussion.id == discussion_id)
        )
        discussion = result.scalar_one_or_none()

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

        # Ownership check
        if discussion.user_id != authorized_user["user_id"]:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "details": "You do not have permission to delete this discussion. Please contact developers if the issue persists.",
                },
            )

        # Record the deletion
        deleted_record = DeletedDiscussion(
            discussion_id=discussion.id,
            user_id=authorized_user["user_id"],
        )
        db_session.add(deleted_record)

        delete_stmt = delete(Discussion).where(Discussion.id == discussion_id)
        await db_session.execute(delete_stmt)
        await db_session.commit()

        logger.info(f"{authorized_user['email']} - Discussion deleted successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion deleted successfully.",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(
            f"{authorized_user['email']} - Error deleting discussion: {str(e)}"
        )

        return CustomBackendError(
            message="Discussion deletion failed",
            details="An error occurred while deleting the discussion. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(
            f"{authorized_user['email']} - Delete Discussion Execution completed"
        )


async def get_popular_tags_handler(
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves the top 5 most frequently used tags across all approved discussions.

    Args:
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the top 5 popular tags and their counts.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        stmt = (
            select(
                Tag.id, Tag.name, func.count(DiscussionTag.discussion_id).label("count")
            )
            .join(DiscussionTag, DiscussionTag.tag_id == Tag.id)
            .join(Discussion, Discussion.id == DiscussionTag.discussion_id)
            .where(Discussion.status == DiscussionsStatusEnum.APPROVED)
            .group_by(Tag.id)
            .order_by(func.count(DiscussionTag.discussion_id).desc())
            .limit(5)
        )

        result = await db_session.execute(stmt)
        popular_tags = result.all()

        logger.info(f"{authorized_user['email']} - Popular tags retrieved successfully")

        serialized_tags = [
            GetPopularTagsSuccessfulResponseData.model_validate(tag).model_dump()
            for tag in popular_tags
        ]

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Popular tags retrieved successfully",
            data=serialized_tags,
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to retrieve popular tags",
            details="An error occurred while retrieving popular tags. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def get_recent_authors_handler(
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves the top 3 most recent authors for each discussion type.

    Args:
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the top 3 recent authors for each discussion type.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # First, get the most recent discussion for each user per type
        recent_discussions_subq = (
            select(
                Discussion.user_id,
                Discussion.type,
                func.max(Discussion.created_at).label("max_created_at"),
            )
            .where(Discussion.status == DiscussionsStatusEnum.APPROVED)
            .group_by(Discussion.user_id, Discussion.type)
            .subquery()
        )

        # Then rank users within each type and get top 3
        ranked_users_subq = select(
            recent_discussions_subq.c.user_id,
            recent_discussions_subq.c.type,
            func.row_number()
            .over(
                partition_by=recent_discussions_subq.c.type,
                order_by=recent_discussions_subq.c.max_created_at.desc(),
            )
            .label("rank"),
        ).subquery()

        stmt = (
            select(User, ranked_users_subq.c.type)
            .join(ranked_users_subq, ranked_users_subq.c.user_id == User.id)
            .where(ranked_users_subq.c.rank <= 3)
            .order_by(ranked_users_subq.c.type, ranked_users_subq.c.rank)
        )

        result = await db_session.execute(stmt)
        rows = result.all()

        # Group users by discussion type
        users_by_type = {}
        for user, discussion_type in rows:
            type_str = (
                discussion_type.value
                if hasattr(discussion_type, "value")
                else discussion_type
                )
            if type_str not in users_by_type:
                users_by_type[type_str] = []

            user_data = UserSchema.model_validate(user).model_dump()
            users_by_type[type_str].append(user_data)

        # Ensure all discussion types are present
        for discussion_type in DiscussionsTypeEnum:
            if discussion_type.value not in users_by_type:
                users_by_type[discussion_type.value] = []

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Recent discussion authors retrieved successfully by type",
            data=users_by_type,
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to retrieve recent discussion authors",
            details=(
                "An error occurred while retrieving recent discussion authors. Please contact developers if the issue persists."
            ),
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def recent_bookmarked_discussions_handler(
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Fetch the last 5 bookmarked discussions for the user, ordered by latest bookmark. Returns only id and title for each discussion.

    Args:
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the last 5 bookmarked discussions for the user.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        stmt = (
            select(Discussion)
            .join(
                BookmarkedDiscussion,
                BookmarkedDiscussion.discussion_id == Discussion.id,
            )
            .where(
                BookmarkedDiscussion.user_id == authorized_user["user_id"],
                BookmarkedDiscussion.is_active.is_(True),
            )
            .order_by(BookmarkedDiscussion.created_at.desc())
            .limit(5)
        )

        result = await db_session.execute(stmt)
        bookmarked_discussions = result.scalars().all()

        serialized_bookmarked_discussions = [
            RecentBookmarkedDiscussion.model_validate(discussion).model_dump()
            for discussion in bookmarked_discussions
        ]

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Recent bookmarks fetched successfully",
            data=serialized_bookmarked_discussions,
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to retrieve recent bookmarked discussions",
            details="An error occurred while retrieving recent bookmarked discussions. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
