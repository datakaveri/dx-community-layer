import math
from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..middlewares.logging import logger
from ..schemas.default_schemas import AuthorizationData
from ..schemas.discussion_responses import TagSchema, UserSchema
from ..database.models import Discussion, DiscussionTag, Tag, User
from ..schemas.discussion_requests import RetrieveDiscussionChoices
from ..schemas.search_requests import SearchDiscussionsParams, SearchParams
from ..schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ..schemas.search_responses import SearchDiscussionSuccessfulResponseDiscussion


def format_tsquery(query: str) -> str:
    """
    Converts a user query into a valid tsquery string.
    - Escapes special characters
    - Applies `:*` to each term for prefix matching
    - Joins terms with `&` for AND search

    Args:
        query (str): The user query.

    Returns:
        str: The formatted tsquery string.
    """
    terms = [term.strip() for term in query.split() if term.strip()]
    return " <-> ".join(terms) + ":*"


async def search_discussions_handler(
    req_params: SearchDiscussionsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves discussions based on the provided search query for title and sub_category.

    Args:
        req_params (SearchDiscussionsParams): The request body containing the search query.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, ID and role.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved discussions.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        formatted_query = format_tsquery(req_params.query)
        ts_query = func.to_tsquery("english", formatted_query)

        # -----------------------
        # Base Query
        # -----------------------
        stmt = select(Discussion).options(
            selectinload(Discussion.user),
            selectinload(Discussion.discussion_tags).selectinload(DiscussionTag.tag),
            selectinload(Discussion.discussion_votes),
            selectinload(Discussion.discussion_attachments),
            selectinload(Discussion.bookmarked_discussions),
            selectinload(Discussion.pinned_discussions),
        )

        # -----------------------
        # Choice Filter
        # -----------------------
        if req_params.choice == RetrieveDiscussionChoices.ALL:
            pass
        if req_params.choice == RetrieveDiscussionChoices.OWNED:
            stmt = stmt.filter(Discussion.user_id == authorized_user["user_id"])
        elif req_params.choice == RetrieveDiscussionChoices.BOOKMARKED:
            stmt = stmt.filter(
                Discussion.bookmarked_discussions.any(
                    user_id=authorized_user["user_id"]
                )
            )

        # -----------------------
        # Search Query
        # -----------------------
        stmt = stmt.filter(
            (Discussion.title_vector.op("@@")(ts_query))
            | (Discussion.sub_category_vector.op("@@")(ts_query))
        )

        # -----------------------
        # Apply filters
        # -----------------------
        if req_params.filters.sub_category_id:
            stmt = stmt.filter(Discussion.sub_category_id == req_params.filters.sub_category_id)

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(Discussion.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

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
        serialized_discussions = []
        for d in discussions:
            # compute flags
            is_bookmarked = any(
                b.user_id == authorized_user["user_id"]
                for b in getattr(d, "bookmarked_discussions", [])
            )
            is_pinned = any(
                p.user_id == authorized_user["user_id"]
                for p in getattr(d, "pinned_discussions", [])
            )

            # compute vote count via relationship
            votes = len(getattr(d, "discussion_votes", []))

            base = SearchDiscussionSuccessfulResponseDiscussion.model_validate(
                d
            ).model_dump(exclude={"votes"})
            base["votes"] = votes
            base["is_bookmarked"] = is_bookmarked
            base["is_pinned"] = is_pinned

            serialized_discussions.append(base)

        logger.info(
            f"{authorized_user['email']} - Search completed successfully for query: {req_params.query}"
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Search completed successfully",
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
            message="Failed to search discussions",
            details="An error occurred while searching discussions for the provided query. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def search_tags_handler(
    req_params: SearchParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves tags based on the provided search query.

    Args:
        req_params (SearchTagsParams): The request body containing the search query.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, ID and role.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved tags.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        formatted_query = format_tsquery(req_params.query)
        ts_query = func.to_tsquery("english", formatted_query)

        # -----------------------
        # Base Query
        # -----------------------
        stmt = select(Tag).filter(Tag.name_vector.op("@@")(ts_query))

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(Discussion.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Pagination
        # -----------------------
        offset = (req_params.page - 1) * req_params.limit
        stmt = stmt.offset(offset).limit(req_params.limit)

        # -----------------------
        # Execute and fetch
        # -----------------------
        result = await db_session.execute(stmt)
        tags = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        searialized_tags = [TagSchema.model_validate(t).model_dump() for t in tags]

        logger.info(
            f"{authorized_user['email']} - Search completed successfully for query: {req_params.query}"
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Search completed successfully",
            data=searialized_tags,
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
            message="Failed to search tags",
            details="An error occurred while searching tags for the provided query. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def search_authors_handler(
    req_params: SearchParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves authors based on the provided search query.

    Args:
        req_params (SearchAuthorsParams): The request body containing the search query.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved authors.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        formatted_query = format_tsquery(req_params.query)
        ts_query = func.to_tsquery("english", formatted_query)

        # -----------------------
        # Base Query
        # -----------------------
        stmt = select(User).filter(User.name_vector.op("@@")(ts_query))

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(User.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Pagination
        # -----------------------
        offset = (req_params.page - 1) * req_params.limit
        stmt = stmt.offset(offset).limit(req_params.limit)

        # -----------------------
        # Execute and fetch
        # -----------------------
        result = await db_session.execute(stmt)
        authors = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_authors = [
            UserSchema.model_validate(a).model_dump() for a in authors
        ]

        logger.info(
            f"{authorized_user['email']} - Search completed successfully for query: {req_params.query}"
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Search completed successfully",
            data=serialized_authors,
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
            message="Failed to search authors",
            details="An error occurred while searching authors for the provided query. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
