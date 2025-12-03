import math
from typing import List
import uuid
from fastapi import status
from sqlalchemy import func, select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ...schemas.discussion.comment_requests import (
    CreateCommentParams,
    CreateCommentReplyParams,
    RetrieveCommentRepliesParams,
    RetrieveDiscussionCommentsParams,
)
from ...configs.s3_config import s3_client
from ...configs.env_config import env_config
from ...schemas.discussion.comment_responses import CommentSchema
from ...schemas.default_schemas import AuthorizationData, UserRole
from ...database.discussion.models import (
    Comment,
    CommentAttachment,
    CommentReaction,
    CommentVote,
    DeletedComment,
    Discussion,
)
from .discussion_services import get_s3_file_metadata
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError


async def retrieve_discussion_comments_handler(
    req_params: RetrieveDiscussionCommentsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieve all comments for a discussion.

    Args:
        discussion_id (uuid.UUID): The ID of the discussion to retrieve comments for.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved comments and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(Comment).filter(
            Comment.discussion_id == req_params.discussion_id,
            Comment.parent_id.is_(None),
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
        sort = getattr(req_params, "sort", "newest")
        if sort == "newest":
            stmt = stmt.order_by(Comment.created_at.desc())
        elif sort == "oldest":
            stmt = stmt.order_by(Comment.created_at.asc())
        elif sort == "hottest":
            # Order by most upvoted, then newest
            stmt = (
                stmt.join(Comment.comment_votes, isouter=True)
                .group_by(Comment.id)
                .order_by(func.count(CommentVote.id).desc(), Comment.created_at.desc())
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
            selectinload(Comment.user),
            selectinload(Comment.sub_comments),
            selectinload(Comment.comment_votes),
            selectinload(Comment.comment_reactions),
            selectinload(Comment.comment_attachments),
        )
        result = await db_session.execute(stmt)
        comments = result.scalars().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_comments = []
        for comment in comments:
            # compute flags
            is_voted = any(
                v.user_id == authorized_user["user_id"]
                for v in getattr(comment, "comment_votes", [])
            )

            # compute vote count via relationship
            votes = len(getattr(comment, "comment_votes", []))

            # compute reactions
            reactions_summary = {}
            user_reaction = {}

            for r in getattr(comment, "comment_reactions", []):
                reactions_summary[r.emoji_code] = (
                    reactions_summary.get(r.emoji_code, 0) + 1
                )
                if r.user_id == authorized_user["user_id"]:
                    user_reaction = {"emoji_code": r.emoji_code}

            base = CommentSchema.model_validate(comment).model_dump(exclude={"votes"})
            base["votes"] = votes
            base["is_voted"] = is_voted
            base["reactions"] = {
                "emojis": reactions_summary,
                "user_reaction": user_reaction,
            }
            # compute sub-comments counts
            if comment.sub_comments:
                base["sub_comments_count"] = len(comment.sub_comments)
            serialized_comments.append(base)

        logger.info(f"{authorized_user['email']} - Discussions retrieved successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion comments retrieved successfully",
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
            message="Discussion comments retrieval failed",
            details="An error occurred while retrieving the discussion comments. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def retrieve_comment_replies_handler(
    req_params: RetrieveCommentRepliesParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieve all replies for a comment.

    Args:
        comment_id (uuid.UUID): The ID of the comment to retrieve replies for.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved replies and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(Comment).filter(Comment.parent_id == req_params.comment_id)

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
        sort = getattr(req_params, "sort", "newest")
        if sort == "newest":
            stmt = stmt.order_by(Comment.created_at.desc())
        elif sort == "oldest":
            stmt = stmt.order_by(Comment.created_at.asc())
        elif sort == "hottest":
            stmt = (
                stmt.join(Comment.comment_votes, isouter=True)
                .group_by(Comment.id)
                .order_by(func.count(CommentVote.id).desc(), Comment.created_at.desc())
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
            selectinload(Comment.user),
            selectinload(Comment.comment_votes),
            selectinload(Comment.comment_reactions),
            selectinload(Comment.comment_attachments),
        )
        result = await db_session.execute(stmt)
        comments = result.scalars().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_comments = []
        for comment in comments:
            # compute flags
            is_voted = any(
                v.user_id == authorized_user["user_id"]
                for v in getattr(comment, "comment_votes", [])
            )

            # compute vote count via relationship
            votes = len(getattr(comment, "comment_votes", []))

            # compute reactions
            reactions_summary = {}
            user_reaction = {}

            for r in getattr(comment, "comment_reactions", []):
                reactions_summary[r.emoji_code] = (
                    reactions_summary.get(r.emoji_code, 0) + 1
                )
                if r.user_id == authorized_user["user_id"]:
                    user_reaction = {"emoji_code": r.emoji_code}

            base = CommentSchema.model_validate(comment).model_dump(exclude={"votes"})
            base["votes"] = votes
            base["is_voted"] = is_voted
            base["reactions"] = {
                "emojis": reactions_summary,
                "user_reaction": user_reaction,
            }
            serialized_comments.append(base)

        logger.info(f"{authorized_user['email']} - Discussions retrieved successfully")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussion comments retrieved successfully",
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
            message="Comment replies retrieval failed",
            details="An error occurred while retrieving the comment replies. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def create_discussion_comment_handler(
    req_params: CreateCommentParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Create a new comment for a discussion.

    Args:
        req_params (CreateCommentParams): The request body containing the comment details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created comment details and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        stmt = select(Discussion).filter(Discussion.id == req_params.discussion_id)
        result = await db_session.execute(stmt)
        discussion = result.scalars().one()

        if not discussion:
            logger.error(
                f"{authorized_user['email']} - Discussion not found (id={req_params.discussion_id})"
            )
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Discussion not found",
                error={
                    "code": "NOT_FOUND",
                    "message": "The discussion you are trying to comment on does not exist. Please contact support if the issue persists.",
                },
            )

        new_comment = Comment(
            discussion_id=req_params.discussion_id,
            user_id=authorized_user["user_id"],
            comment=req_params.comment,
        )

        db_session.add(new_comment)
        await db_session.flush()

        # -----------------------
        # Handle Attachments (copy in S3 -> store permanent key)
        # -----------------------
        if req_params.attachments:
            attachment_objs: List[CommentAttachment] = []
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
                permanent_s3_key = f"private/{new_comment.discussion_id}/comments/{new_comment.id}/{metadata['file_name']}"

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
                        comment_id=new_comment.id,
                        attachment_metadata=metadata,
                        s3_key=permanent_s3_key,
                    )
                )

            if attachment_objs:
                db_session.add_all(attachment_objs)

        # -----------------------
        # Finalize transaction
        # -----------------------
        await db_session.commit()

        logger.info(
            f"{authorized_user['email']} - Discussion comment created successfully (id={new_comment.id})"
        )
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Discussion comment created successfully",
            data={"comment_id": new_comment.id},
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Discussion comment creation failed",
            details="An error occurred while creating the discussion comment. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def create_comment_reply_handler(
    req_params: CreateCommentReplyParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Create a new reply for a comment.

    Args:
        req_params (CreateCommentReplyParams): The request body containing the reply details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created reply details and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        stmt = select(Comment).where(Comment.id == req_params.comment_id)
        parent_comment = (await db_session.execute(stmt)).scalar_one()

        if not parent_comment:
            logger.error(
                f"{authorized_user['email']} - Parent comment not found (id={req_params.comment_id})"
            )
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Parent comment not found",
                error={
                    "code": "NOT_FOUND",
                    "message": f"The parent comment (id={req_params.comment_id}) you are trying to reply to does not exist. Please contact support if the issue persists.",
                },
            )

        new_reply = Comment(
            discussion_id=parent_comment.discussion_id,
            user_id=authorized_user["user_id"],
            parent_id=parent_comment.id,
            comment=req_params.reply,
        )

        db_session.add(new_reply)
        await db_session.flush()

        # -----------------------
        # Handle Attachments (copy in S3 -> store permanent key)
        # -----------------------
        if req_params.attachments:
            for source_s3_key in req_params.attachments:
                metadata = get_s3_file_metadata(source_s3_key)

                if "error" in metadata:
                    logger.error(
                        f"{authorized_user['email']} - Error fetching metadata for {source_s3_key}: {metadata['error']}"
                    )
                    await db_session.rollback()
                    return CustomBackendError(
                        message="Comment reply creation failed",
                        details="An error occurred while creating the comment reply. Please contact developers if the issue persists.",
                    )

                # build permanent key and copy object to permanent location
                permanent_s3_key = f"private/{new_reply.discussion_id}/comments/{new_reply.id}/{metadata['file_name']}"

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
                        message="Comment reply creation failed",
                        details="An error occurred while creating the comment reply. Please contact developers if the issue persists.",
                    )

                db_session.add(
                    CommentAttachment(
                        comment_id=new_reply.id,
                        attachment_metadata=metadata,
                        s3_key=permanent_s3_key,
                    )
                )

        # -----------------------
        # Finalize transaction
        # -----------------------
        await db_session.commit()

        logger.info(
            f"{authorized_user['email']} - Comment reply created successfully (id={new_reply.id})"
        )
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Comment reply created successfully",
            data={"reply_id": new_reply.id},
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Comment reply creation failed",
            details="An error occurred while creating the comment reply. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def add_comment_vote_handler(
    comment_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    logger.info(f"{authorized_user['email']} - Add Comment Vote Execution started")
    try:
        comment = (
            (await db_session.execute(select(Comment).filter(Comment.id == comment_id)))
            .scalars()
            .one_or_none()
        )
        if not comment:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Comment not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The comment does not exist. Please contact developers if the issue persists.",
                },
            )

        user_id = authorized_user["user_id"]
        try:
            user_id = uuid.UUID(str(user_id))
        except Exception:
            pass

        existing_vote = (
            (
                await db_session.execute(
                    select(CommentVote).filter(
                        CommentVote.comment_id == comment_id,
                        CommentVote.user_id == user_id,
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
                message="Comment already upvoted",
                error={
                    "code": "CONFLICT",
                    "details": "You have already upvoted this comment. Please try again later or contact support if the issue persists.",
                },
            )

        vote = CommentVote(comment_id=comment_id, user_id=user_id)
        db_session.add(vote)
        await db_session.commit()

        logger.info(f"{authorized_user['email']} - Comment vote added successfully")
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Comment vote added successfully",
        )
    except Exception as e:
        await db_session.rollback()
        err_msg = str(e)
        logger.exception(
            f"{authorized_user['email']} - Error while adding comment vote: {err_msg}"
        )
        details = (
            "Comment votes table might be missing. Please run database migrations."
            if "relation" in err_msg and "comment_votes" in err_msg
            else f"An error occurred while adding the comment vote: {err_msg}"
        )
        return CustomBackendError(
            message="Comment vote failed",
            details=details,
        )
    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def delete_comment_vote_handler(
    comment_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    logger.info(f"{authorized_user['email']} - Delete Comment Vote Execution started")
    try:
        user_id = authorized_user["user_id"]
        try:
            user_id = uuid.UUID(str(user_id))
        except Exception:
            pass

        vote = (
            (
                await db_session.execute(
                    select(CommentVote).filter(
                        CommentVote.comment_id == comment_id,
                        CommentVote.user_id == user_id,
                    )
                )
            )
            .scalars()
            .one_or_none()
        )
        if not vote:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Comment vote not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The comment vote does not exist. Please contact developers if the issue persists.",
                },
            )

        await db_session.execute(
            delete(CommentVote).filter(
                CommentVote.comment_id == comment_id,
                CommentVote.user_id == user_id,
            )
        )
        await db_session.commit()
        logger.info(f"{authorized_user['email']} - Comment vote deleted successfully")
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Comment vote deleted successfully",
        )
    except Exception as e:
        await db_session.rollback()
        err_msg = str(e)
        logger.exception(
            f"{authorized_user['email']} - Error while deleting comment vote: {err_msg}"
        )
        details = (
            "Comment votes table might be missing. Please run database migrations."
            if "relation" in err_msg and "comment_votes" in err_msg
            else f"An error occurred while deleting the comment vote: {err_msg}"
        )
        return CustomBackendError(
            message="Failed to delete comment vote",
            details=details,
        )
    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def add_update_comment_reaction_handler(
    comment_id: uuid.UUID,
    emoji_code: str | None,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Add or update the current user's emoji reaction on a comment.
    If a reaction exists, update its emoji and timestamp; else create one.
    """
    from datetime import datetime
    import pytz
    from sqlalchemy import select

    logger.info(f"{authorized_user['email']} - Add/Update Comment Reaction started")

    try:
        # Validate comment exists
        result = await db_session.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalars().one_or_none()
        if not comment:
            return CustomJSONResponse(
                success=False,
                status_code=404,
                message="Comment not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The comment does not exist. Please contact developers if the issue persists.",
                },
            )

        current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

        # Find existing user reaction
        reaction_q = await db_session.execute(
            select(CommentReaction).where(
                CommentReaction.comment_id == comment_id,
                CommentReaction.user_id == authorized_user["user_id"],
            )
        )
        existing_reaction = reaction_q.scalars().one_or_none()

        if existing_reaction:
            existing_reaction.emoji_code = emoji_code
            existing_reaction.emoji_timestamp = current_timestamp
        else:
            new_reaction = CommentReaction(
                comment_id=comment_id,
                user_id=authorized_user["user_id"],
                emoji_code=emoji_code,
                emoji_timestamp=current_timestamp,
            )
            db_session.add(new_reaction)

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=200,
            message="Reaction added/updated successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.exception(f"Failed to add/update comment reaction: {e}")
        return CustomBackendError(message="Comment reaction failed")


async def delete_comment_reaction_handler(
    comment_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Delete the current user's reaction on a comment if it exists.
    """
    from sqlalchemy import delete, select

    logger.info(f"{authorized_user['email']} - Delete Comment Reaction started")

    try:
        # Ensure a reaction exists for this user on this comment
        res = await db_session.execute(
            select(CommentReaction).where(
                CommentReaction.comment_id == comment_id,
                CommentReaction.user_id == authorized_user["user_id"],
            )
        )
        reaction = res.scalars().one_or_none()
        if not reaction:
            return CustomJSONResponse(
                success=False,
                status_code=404,
                message="Reaction not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The comment reaction does not exist. Please contact developers if the issue persists.",
                },
            )

        await db_session.execute(
            delete(CommentReaction).where(
                CommentReaction.comment_id == comment_id,
                CommentReaction.user_id == authorized_user["user_id"],
            )
        )
        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=200,
            message="Reaction deleted successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.exception(f"Failed to delete comment reaction: {e}")
        return CustomBackendError(message="Failed to delete comment reaction")


async def delete_comment_handler(
    comment_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Delete a comment if the requester is the author or a COS admin.
    Records the deletion in DeletedComment for auditing.
    """
    logger.info(f"{authorized_user['email']} - Delete Comment Execution started")

    try:
        result = await db_session.execute(
            select(Comment)
            .filter(Comment.id == comment_id)
            .options(selectinload(Comment.comment_attachments))
        )
        comment = result.scalars().one_or_none()

        if not comment:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Comment not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "The comment does not exist. Please contact developers if the issue persists.",
                },
            )

        if (
            comment.user_id != authorized_user["user_id"]
            and authorized_user["user_role"] != UserRole.COS_ADMIN
        ):
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "details": "You do not have permission to delete this comment. Please contact developers if the issue persists.",
                },
            )

        # Record deletion
        deleted_comment = DeletedComment(
            comment_id=comment.id, user_id=authorized_user["user_id"]
        )
        db_session.add(deleted_comment)

        # Attempt to clean up any uploaded attachments associated with the comment
        attachment_keys = [
            attachment.s3_key
            for attachment in getattr(comment, "comment_attachments", [])
        ]
        for key in attachment_keys:
            try:
                s3_client.delete_object(
                    Bucket=env_config.DISCUSSION_AWS_S3_BUCKET, Key=key
                )
            except Exception as s3_exc:
                logger.warning(
                    f"{authorized_user['email']} - Failed to delete attachment {key}: {s3_exc}"
                )

        await db_session.execute(delete(Comment).where(Comment.id == comment_id))
        await db_session.commit()

        logger.info(f"{authorized_user['email']} - Comment deleted successfully")
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Comment deleted successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.exception(f"{authorized_user['email']} - Error deleting comment: {e}")
        return CustomBackendError(
            message="Comment deletion failed",
            details="An error occurred while deleting the comment. Please contact developers if the issue persists.",
        )
    finally:
        logger.info(f"{authorized_user['email']} - Delete Comment Execution completed")
