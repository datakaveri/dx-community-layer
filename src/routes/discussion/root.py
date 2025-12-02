import uuid
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path, Query

from ...docs import public_desc
from ...middlewares.logging import logger
from ...configs.db_config import get_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...schemas.discussion_requests import (
    AddUpdateDiscussionReactionParams,
    CreateDiscussionParams,
    DiscussionActionsParams,
    RetrieveDiscussionParams,
    UpdateDiscussionParams,
)
from ...schemas.default_schemas import AuthorizationData
from ...middlewares.authorization import http_bearer_header, http_bearer_header_public
from ...services.discussion_services import (
    add_discussion_vote_handler,
    add_update_discussion_reaction_handler,
    create_discussion_handler,
    get_recent_authors_handler,
    recent_bookmarked_discussions_handler,
    update_discussion_handler,
    delete_discussion_handler,
    delete_discussion_reaction_handler,
    delete_discussion_vote_handler,
    discussion_actions_handler,
    retrieve_discussion_by_id_handler,
    retrieve_discussions_handler,
    get_popular_tags_handler,
)
from ...schemas.discussion_responses import (
    ADD_DISCUSSION_VOTE_RESPONSE_MODEL,
    ADD_UPDATE_DISCUSSION_REACTION_RESPONSE_MODEL,
    CREATE_DISCUSSION_RESPONSE_MODEL,
    DELETE_DISCUSSION_REACTION_RESPONSE_MODEL,
    DELETE_DISCUSSION_RESPONSE_MODEL,
    DELETE_DISCUSSION_VOTE_RESPONSE_MODEL,
    DISCUSSION_ACTIONS_RESPONSE_MODEL,
    GET_POPULAR_TAGS_RESPONSE_MODEL,
    RECENT_AUTHORS_RESPONSE_MODEL,
    RETRIEVE_DISCUSSION_BY_ID_RESPONSE_MODEL,
    RETRIEVE_DISCUSSION_RESPONSE_MODEL,
    UPDATE_DISCUSSION_RESPONSE_MODEL,
)

from .admin import router as admin_router
from .search import router as search_router
from .comments import router as comments_router
from .attachment import router as attachment_router


router = APIRouter(prefix="/discussion", tags=["Discussion APIs"])

router.include_router(admin_router)
router.include_router(search_router)
router.include_router(comments_router)
router.include_router(attachment_router)


@router.get(
    path="/{discussion_id}",
    description=public_desc(
        (
            "Fetches full details of a discussion by its UUID. Includes content, attachments, "
            "tags, author info, category, reactions count, reactions, etc. Admins and owners can view discussions "
            "of all statuses; regular users can only see APPROVED discussions."
        )
    ),
    responses=RETRIEVE_DISCUSSION_BY_ID_RESPONSE_MODEL,
)
async def retrieve_discussion_by_id(
    discussion_id: uuid.UUID = Path(
        ..., description="ID of the discussion to retrieve"
    ),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Retrieves a discussion by its ID.

    Args:
        discussion_id (uuid.UUID): The ID of the discussion to retrieve.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved discussion and relevant metadata.
    """
    logger.info("Retrieve Discussion by ID API is being called")

    return await retrieve_discussion_by_id_handler(
        discussion_id=discussion_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/choice/{choice}",
    description=public_desc(
        (
            "Retrieves a list of discussions for the specified choice. Supports pagination, "
            "filtering (by type, status, tags), and sorting (by hottest, newest, or oldest). "
            "Use category=all to fetch discussions across all categories. Only discussions with status "
            "<b>APPROVED</b> are returned to regular users."
        )
    ),
    responses=RETRIEVE_DISCUSSION_RESPONSE_MODEL,
)
async def retrieve_discussions(
    req_params: RetrieveDiscussionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Retrieves discussions based on the provided choice and filters.

    Args:
        req_params (RetrieveDiscussionParams): The request body containing the choice and filters.
        user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved discussions and relevant metadata.
    """
    logger.info("Retrieve Discussions API is being called")

    return await retrieve_discussions_handler(
        req_params=req_params, authorized_user=authorized_user, db_session=db_session
    )


@router.post(
    path="",
    description=(
        "Creates a new discussion. The discussion initially enters the PENDING_REVIEW state "
        "and awaits admin moderation. Attachments can be added via presigned URLs. "
        "Returns the created discussion’s UUID and status."
    ),
    responses=CREATE_DISCUSSION_RESPONSE_MODEL,
)
async def create_discussion(
    req_params: CreateDiscussionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Creates a new discussion for the authenticated user.

    This endpoint allows the user to create a new discussion. The data for
    the discussion is provided in the request body, and the user's details is extracted from
    the authentication token to associate the discussion with the correct user.

    Args:
        req_params (CreateDiscussionParams): The request body containing the discussion details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created discussion details and relevant metadata.
    """
    logger.info("Create Discussion API is being called")

    return await create_discussion_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.put(
    path="/{discussion_id}",
    description=(
        "Updates a discussion's title, content, category, sub-category, tags and adds attachments. "
        "Only the owner or an admin can update. "
    ),
    responses=UPDATE_DISCUSSION_RESPONSE_MODEL,
)
async def update_discussion(
    req_params: UpdateDiscussionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Updates a discussion with the provided details(title, content, tags).

    Args:
        req_params (UpdateDiscussionParams): The request body containing the discussion details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the updated discussion details and relevant metadata.
    """
    logger.info("Update Discussion API is being called")

    return await update_discussion_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/{discussion_id}/actions/{action}",
    description="This endpoint performs actions on a discussion such as `bookmark`, `unbookmark`, `pin` & `unpin`.",
    responses=DISCUSSION_ACTIONS_RESPONSE_MODEL,
)
async def discussion_actions(
    req_params: DiscussionActionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Performs actions on a discussion such as bookmark, unbookmark, pin & unpin.

    Args:
        req_params (CreateDiscussionParams): The request body containing the discussion details.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created discussion details and relevant metadata.
    """
    logger.info("Discussion Actions API is being called")

    return await discussion_actions_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/{discussion_id}/reaction",
    description="Adds or updates a reaction to a discussion. If the user has already reacted, this updates the reaction.",
    responses=ADD_UPDATE_DISCUSSION_REACTION_RESPONSE_MODEL,
)
async def add_update_discussion_reaction(
    req_params: AddUpdateDiscussionReactionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Adds or updates a reaction to a discussion.

    Args:
        req_params (AddUpdateDiscussionReactionParams): The request body containing the reaction details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created discussion details and relevant metadata.
    """
    logger.info("Add/Update Discussion Reaction API is being called")

    return await add_update_discussion_reaction_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.delete(
    path="/{discussion_id}/reaction",
    description=(
        "Removes the current user’s reaction from the discussion. If the user has no reaction, "
        "this returns a no-op or a 404."
    ),
    responses=DELETE_DISCUSSION_REACTION_RESPONSE_MODEL,
)
async def delete_discussion_reaction(
    discussion_id: uuid.UUID = Path(..., description="ID of the discussion to delete"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Deletes a discussion and stores its details in DeletedDiscussion table.

    Args:
        discussion_id (uuid.UUID): The ID of the discussion to delete.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the deleted discussion details and relevant metadata.
    """
    logger.info("Delete Discussion Reaction API called")

    return await delete_discussion_reaction_handler(
        discussion_id=discussion_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/{discussion_id}/vote",
    description=(
        "Adds a vote to a discussion. If the user has already voted, this return a 409 conflict."
    ),
    responses=ADD_DISCUSSION_VOTE_RESPONSE_MODEL,
)
async def add_discussion_vote(
    discussion_id: uuid.UUID = Path(..., description="ID of the discussion to vote on"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Adds or updates a vote to a discussion.

    Args:
        req_params (AddUpdateDiscussionVoteParams): The request body containing the vote details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created discussion details and relevant metadata.
    """
    logger.info("Add/Update Discussion Vote API is being called")

    return await add_discussion_vote_handler(
        discussion_id=discussion_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.delete(
    path="/{discussion_id}/vote",
    description=(
        "Removes the current user’s vote from the discussion. If the user has no vote, "
        "this returns a no-op or a 404."
    ),
    responses=DELETE_DISCUSSION_VOTE_RESPONSE_MODEL,
)
async def delete_discussion_vote(
    discussion_id: uuid.UUID = Path(..., description="ID of the discussion to delete"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Deletes a discussion and stores its details in DeletedDiscussion table.

    Args:
        discussion_id (uuid.UUID): The ID of the discussion to delete.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the deleted discussion details and relevant metadata.
    """
    logger.info("Delete Discussion Vote API called")

    return await delete_discussion_vote_handler(
        discussion_id=discussion_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.delete(
    path="/{discussion_id}",
    description=(
        "Removes the current user’s reaction from the discussion. If the user has no reaction, "
        "this returns a no-op or a 404."
    ),
    responses=DELETE_DISCUSSION_RESPONSE_MODEL,
)
async def delete_discussion(
    discussion_id: uuid.UUID = Path(..., description="ID of the discussion to delete"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Deletes a discussion and stores its details in DeletedDiscussion table.

    Args:
        discussion_id (uuid.UUID): The ID of the discussion to delete.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the deleted discussion details and relevant metadata.
    """
    logger.info("Delete Discussion API called")

    return await delete_discussion_handler(
        discussion_id=discussion_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/tags/popular",
    description=public_desc(
        (
            "Returns the top 5 most frequently used tags across all approved discussions. "
            "Ranking is based on the total number of approved discussions that include each tag."
        )
    ),
    responses=GET_POPULAR_TAGS_RESPONSE_MODEL,
)
async def get_popular_tags(
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Retrieves the top 5 most frequently used tags across all approved discussions.

    Args:
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the top 5 popular tags and their counts.
    """
    logger.info("Get Popular Tags API is being called")

    return await get_popular_tags_handler(
        authorized_user=authorized_user, db_session=db_session
    )


@router.get(
    path="/recent/authors",
    description=public_desc(
        (
            "Returns up to three recent discussion authors (unique, by most recent discussion created). "
            "Only author data is returned."
        )
    ),
    responses=RECENT_AUTHORS_RESPONSE_MODEL,
)
async def get_recent_authors(
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: Session = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Retrieves up to three recent unique discussion authors.
    """
    logger.info("Get Recent Authors API is being called")
    return await get_recent_authors_handler(
        authorized_user=authorized_user, db_session=db_session
    )


@router.get(
    path="/recent/bookmarked",
    description="Fetch the last 5 discussions bookmarked by the authenticated user. Returns only id and title.",
)
async def recent_bookmarked_discussions(
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_db_session),
) -> CustomJSONResponse:
    return await recent_bookmarked_discussions_handler(
        authorized_user=authorized_user, db_session=db_session
    )
