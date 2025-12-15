import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Path, Depends, Body

from ...docs import public_desc
from ...middlewares.logging import logger
from ...configs.db_config import get_discussion_db_session
from ...schemas.default_schemas import AuthorizationData
from ...schemas.custom_responses import CustomJSONResponse
from ...schemas.discussion.comment_requests import (
    CreateCommentParams,
    CreateCommentReplyParams,
    RetrieveCommentRepliesParams,
    RetrieveDiscussionCommentsParams,
    AddUpdateCommentReactionParams,
)
from ...middlewares.authorization import http_bearer_header, http_bearer_header_public
from ...services.discussion.comment_services import (
    create_comment_reply_handler,
    retrieve_comment_replies_handler,
    retrieve_discussion_comments_handler,
    create_discussion_comment_handler,
    add_comment_vote_handler,
    delete_comment_vote_handler,
    add_update_comment_reaction_handler,
    delete_comment_reaction_handler,
    delete_comment_handler,
)
from ...schemas.discussion.comment_responses import (
    ADD_UPDATE_COMMENT_REACTION_RESPONSE_MODEL,
    DELETE_COMMENT_REACTION_RESPONSE_MODEL,
    DELETE_COMMENT_RESPONSE_MODEL,
    RETRIEVE_COMMENTS_RESPONSE_MODEL,
)


router = APIRouter(tags=["Discussion - Comment APIs"])


@router.get(
    path="/discussion/{discussion_id}/comments",
    description=public_desc("Fetches all comments for a discussion by its ID."),
    responses=RETRIEVE_COMMENTS_RESPONSE_MODEL,
)
async def retrieve_discussion_comments(
    req_params: RetrieveDiscussionCommentsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Retrieves all comments for a discussion by its ID.

    Args:
        discussion_id (uuid.UUID): The ID of the discussion to retrieve comments for.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved comments and relevant metadata.
    """
    logger.info("Retrieve Discussion Comments API is being called")

    return await retrieve_discussion_comments_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/comments/{comment_id}/replies",
    description=public_desc("Fetches all replies for a comment by its ID."),
)
async def retrieve_comment_replies(
    req_params: RetrieveCommentRepliesParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Retrieves all replies for a comment by its ID.

    Args:
        comment_id (uuid.UUID): The ID of the comment to retrieve replies for.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved replies and relevant metadata.
    """
    logger.info("Retrieve Comment Replies API is being called")

    return await retrieve_comment_replies_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/discussion/{discussion_id}/comment",
    description="Adds a comment to a discussion by its ID.",
)
async def create_discussion_comment(
    req_params: CreateCommentParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Adds a comment to a discussion by its ID.

    Args:
        req_params (CreateCommentParams): The request body containing the comment details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created comment details and relevant metadata.
    """
    logger.info("Create Discussion Comment API is being called")

    return await create_discussion_comment_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/comment/{comment_id}/reply",
    description="Adds a reply to a comment by its ID.",
)
async def create_comment_reply(
    req_params: CreateCommentReplyParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Adds a reply to a comment by its ID.

    Args:
        req_params (CreateCommentReplyParams): The request body containing the reply details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created reply details and relevant metadata.
    """
    logger.info("Create Comment Reply API is being called")

    return await create_comment_reply_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/comment/{comment_id}/vote",
    description="Adds an upvote to a comment by its ID.",
)
async def add_comment_vote(
    comment_id: uuid.UUID = Path(..., description="ID of the comment to upvote"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    logger.info("Add Comment Vote API is being called")
    return await add_comment_vote_handler(
        comment_id=comment_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.delete(
    path="/comment/{comment_id}/vote",
    description="Removes the current user's upvote from the comment.",
)
async def delete_comment_vote(
    comment_id: uuid.UUID = Path(..., description="ID of the comment to remove upvote"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    logger.info("Delete Comment Vote API is being called")
    return await delete_comment_vote_handler(
        comment_id=comment_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/comments/{comment_id}/reaction",
    description="Adds or updates a reaction to a comment. If the user has already reacted, this updates the reaction.",
    responses=ADD_UPDATE_COMMENT_REACTION_RESPONSE_MODEL,
)
async def add_update_comment_reaction(
    req_params: AddUpdateCommentReactionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    return await add_update_comment_reaction_handler(
        comment_id=req_params.comment_id,
        emoji_code=req_params.emoji_code,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.delete(
    path="/comments/{comment_id}/reaction",
    description="Removes the current user’s reaction from the comment.",
    responses=DELETE_COMMENT_REACTION_RESPONSE_MODEL,
)
async def delete_comment_reaction(
    comment_id: uuid.UUID = Path(..., description="ID of the comment"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    return await delete_comment_reaction_handler(
        comment_id=comment_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.delete(
    path="/comments/{comment_id}",
    description="Deletes a comment by its ID if the current user has permission.",
    responses=DELETE_COMMENT_RESPONSE_MODEL,
)
async def delete_comment(
    comment_id: uuid.UUID = Path(..., description="ID of the comment to delete"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    logger.info("Delete Comment API is being called")
    return await delete_comment_handler(
        comment_id=comment_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )
