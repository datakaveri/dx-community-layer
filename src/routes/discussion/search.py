from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...docs import public_desc
from ...middlewares.logging import logger
from ...configs.db_config import get_discussion_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...services.discussion.search_services import (
    search_authors_handler,
    search_discussions_handler,
    search_tags_handler,
)
from ...schemas.discussion.search_responses import (
    SEARCH_AUTHORS_RESPONSE_MODEL,
    SEARCH_DISCUSSIONS_RESPONSE_MODEL,
    SEARCH_TAGS_RESPONSE_MODEL,
)
from ...schemas.default_schemas import AuthorizationData
from ...middlewares.authorization import http_bearer_header_public
from ...schemas.discussion.search_requests import SearchDiscussionsParams, SearchParams


router = APIRouter(prefix="/search")


@router.get(
    path="/discussions/{choice}",
    description=public_desc("Search discussions by title and sub_category."),
    responses=SEARCH_DISCUSSIONS_RESPONSE_MODEL,
)
async def search_discussions(
    req_params: SearchDiscussionsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Retrieves discussions based on the provided search query.

    Args:
        query (str): The search query.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved discussions.
    """
    logger.info("Search Discussions API is being called")

    return await search_discussions_handler(
        req_params=req_params, authorized_user=authorized_user, db_session=db_session
    )


@router.get(
    path="/tags",
    description=public_desc("Search tags by name."),
    responses=SEARCH_TAGS_RESPONSE_MODEL,
)
async def search_tags(
    req_params: SearchParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Retrieves tags based on the provided search query.

    Args:
        query (str): The search query.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved tags.
    """
    logger.info("Search Tags API is being called")

    return await search_tags_handler(
        req_params=req_params, authorized_user=authorized_user, db_session=db_session
    )


@router.get(
    path="/authors",
    description=public_desc("Search authors by name."),
    responses=SEARCH_AUTHORS_RESPONSE_MODEL,
)
async def search_authors(
    req_params: SearchParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_discussion_db_session),
) -> CustomJSONResponse:
    """
    Retrieves authors based on the provided search query.

    Args:
        query (str): The search query.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved authors.
    """
    logger.info("Search Authors API is being called")

    return await search_authors_handler(
        req_params=req_params, authorized_user=authorized_user, db_session=db_session
    )
