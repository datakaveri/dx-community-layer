from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.challenge.competition_requests import CompetitionsSortBy

from ...middlewares.logging import logger
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ...schemas.default_schemas import AuthorizationData
from ...database.challenge.models import (
    Competition,
    BookmarkedCompetition,
    CompetitionTimeline,
    CompetitionPrizePool,
    CompetitionParticipant,
)
from ...database.challenge.enums import CompetitionStatusEnum


async def bookmark_competition_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Handles bookmarking a competition.
    Ensures the competition exists, is published, and the user hasn't already bookmarked it.
    """
    try:
        user_id = authorized_user["user_id"]

        if not user_id:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error={
                    "code": "UNAUTHORIZED",
                    "details": "User information missing in authorization context.",
                },
            )

        # Verify competition exists and is published
        competition_stmt = select(Competition).where(
            Competition.id == competition_id,
            Competition.status == CompetitionStatusEnum.PUBLISHED,
        )
        competition_result = await db_session.execute(competition_stmt)
        competition = competition_result.scalar_one_or_none()

        if not competition:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Competition not found or not published.",
                },
            )

        # Check if the user already has an active bookmark
        try:
            existing_bookmark_stmt = select(BookmarkedCompetition).where(
                BookmarkedCompetition.competition_id == competition_id,
                BookmarkedCompetition.user_id == user_id,
                BookmarkedCompetition.is_active == True,
            )
            existing_bookmark_result = await db_session.execute(existing_bookmark_stmt)
            existing_bookmark = existing_bookmark_result.scalar_one_or_none()

            if existing_bookmark:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_409_CONFLICT,
                    message="Resource already exists",
                    error={
                        "code": "CONFLICT",
                        "details": "You have already bookmarked this competition.",
                    },
                )

            # Check if there's an inactive bookmark (reactivate it)
            inactive_bookmark_stmt = select(BookmarkedCompetition).where(
                BookmarkedCompetition.competition_id == competition_id,
                BookmarkedCompetition.user_id == user_id,
                BookmarkedCompetition.is_active == False,
            )
            inactive_bookmark_result = await db_session.execute(inactive_bookmark_stmt)
            inactive_bookmark = inactive_bookmark_result.scalar_one_or_none()
        except Exception as db_error:
            # Handle database permission errors
            error_msg = str(db_error)
            if "permission denied" in error_msg.lower() or "InsufficientPrivilegeError" in error_msg:
                logger.error(
                    f"Database permission error when checking bookmark status: {db_error}"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service unavailable",
                    error={
                        "code": "SERVICE_UNAVAILABLE",
                        "details": "Bookmark service is currently unavailable due to database permissions. Please contact support.",
                    },
                )
            # Re-raise other database errors
            raise

        if inactive_bookmark:
            # Reactivate the bookmark
            inactive_bookmark.is_active = True
            await db_session.commit()
            await db_session.refresh(inactive_bookmark)

            return CustomJSONResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Competition bookmarked successfully",
                data={
                    "bookmark_id": str(inactive_bookmark.id),
                    "competition_id": str(competition_id),
                    "user_id": str(user_id),
                    "is_active": inactive_bookmark.is_active,
                    "created_at": inactive_bookmark.created_at.isoformat(),
                },
            )

        # Create new bookmark
        new_bookmark = BookmarkedCompetition(
            competition_id=competition_id,
            user_id=user_id,
            is_active=True,
        )
        db_session.add(new_bookmark)
        await db_session.commit()
        await db_session.refresh(new_bookmark)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Competition bookmarked successfully",
            data={
                "bookmark_id": str(new_bookmark.id),
                "competition_id": str(competition_id),
                "user_id": str(user_id),
                "is_active": new_bookmark.is_active,
                "created_at": new_bookmark.created_at.isoformat(),
            },
        )
    except Exception as exc:
        logger.error("Failed to bookmark competition", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(
            message="Failed to bookmark competition",
            details=str(exc),
        )


async def unbookmark_competition_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Handles unbookmarking a competition.
    Marks the bookmark as inactive (soft delete).
    """
    try:
        user_id = authorized_user["user_id"]

        if not user_id:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error={
                    "code": "UNAUTHORIZED",
                    "details": "User information missing in authorization context.",
                },
            )

        # Find the active bookmark
        try:
            bookmark_stmt = select(BookmarkedCompetition).where(
                BookmarkedCompetition.competition_id == competition_id,
                BookmarkedCompetition.user_id == user_id,
                BookmarkedCompetition.is_active == True,
            )
            bookmark_result = await db_session.execute(bookmark_stmt)
            bookmark = bookmark_result.scalar_one_or_none()

            if not bookmark:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Resource not found",
                    error={
                        "code": "NOT_FOUND",
                        "details": "Bookmark not found or already unbookmarked.",
                    },
                )
        except Exception as db_error:
            # Handle database permission errors
            error_msg = str(db_error)
            if "permission denied" in error_msg.lower() or "InsufficientPrivilegeError" in error_msg:
                logger.error(
                    f"Database permission error when checking bookmark: {db_error}"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service unavailable",
                    error={
                        "code": "SERVICE_UNAVAILABLE",
                        "details": "Bookmark service is currently unavailable due to database permissions. Please contact support.",
                    },
                )
            # Re-raise other database errors
            raise

        # Soft delete: mark as inactive
        bookmark.is_active = False
        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Competition unbookmarked successfully",
        )
    except Exception as exc:
        logger.error("Failed to unbookmark competition", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(
            message="Failed to unbookmark competition",
            details=str(exc),
        )


async def get_bookmarked_competitions_handler(
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
    sort_by: CompetitionsSortBy,
    page: int = 1,
    limit: int = 10,
) -> CustomJSONResponse:
    """
    Handles retrieving a user's bookmarked competitions.
    Returns paginated list of active bookmarks.
    """
    try:
        user_id = authorized_user["user_id"]

        if not user_id:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error={
                    "code": "UNAUTHORIZED",
                    "details": "User information missing in authorization context.",
                },
            )

        # Build participants count subquery once for re-use
        participants_count_sq = (
            select(
                CompetitionParticipant.competition_id.label("c_id"),
                func.count(CompetitionParticipant.id).label("participants_count"),
            )
            .group_by(CompetitionParticipant.competition_id)
            .subquery()
        )

        # Get total count of active bookmarks
        try:
            count_stmt = select(func.count()).select_from(BookmarkedCompetition).where(
                BookmarkedCompetition.user_id == user_id,
                BookmarkedCompetition.is_active == True,
            )
            total_bookmarks = (await db_session.execute(count_stmt)).scalar_one()

            # Calculate pagination
            total_pages = (total_bookmarks + limit - 1) // limit if total_bookmarks > 0 else 0
            offset = (page - 1) * limit

            # Get paginated bookmarks with competition details
            bookmarks_stmt = (
                select(
                    BookmarkedCompetition,
                    Competition,
                    CompetitionTimeline.submission_ends_at.label("submission_ends_at"),
                    CompetitionPrizePool.total_pool_amount.label("total_pool_amount"),
                    CompetitionPrizePool.currency.label("currency"),
                    CompetitionPrizePool.prize_type.label("prize_type"),
                    func.coalesce(
                        participants_count_sq.c.participants_count, 0
                    ).label("participants_count"),
                )
                .join(Competition, BookmarkedCompetition.competition_id == Competition.id)
                .join(
                    CompetitionTimeline,
                    CompetitionTimeline.competition_id == Competition.id,
                    isouter=True,
                )
                .join(
                    CompetitionPrizePool,
                    CompetitionPrizePool.competition_id == Competition.id,
                    isouter=True,
                )
                .join(
                    participants_count_sq,
                    participants_count_sq.c.c_id == Competition.id,
                    isouter=True,
                )
                .where(
                    BookmarkedCompetition.user_id == user_id,
                    BookmarkedCompetition.is_active == True,
                )
                .offset(offset)
                .limit(limit)
            )

            if sort_by == CompetitionsSortBy.NEWEST:
                bookmarks_stmt = bookmarks_stmt.order_by(BookmarkedCompetition.created_at.desc())
            elif sort_by == CompetitionsSortBy.OLDEST:
                bookmarks_stmt = bookmarks_stmt.order_by(BookmarkedCompetition.created_at.asc())
            elif sort_by == CompetitionsSortBy.HOTTEST:
                bookmarks_stmt = bookmarks_stmt.order_by(
                    func.coalesce(participants_count_sq.c.participants_count, 0).desc()
                )

            bookmarks_result = await db_session.execute(bookmarks_stmt)
            bookmarks_rows = bookmarks_result.all()
        except Exception as db_error:
            # Handle database permission errors
            error_msg = str(db_error)
            if "permission denied" in error_msg.lower() or "InsufficientPrivilegeError" in error_msg:
                logger.error(
                    f"Database permission error when getting bookmarks: {db_error}"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service unavailable",
                    error={
                        "code": "SERVICE_UNAVAILABLE",
                        "details": "Bookmark service is currently unavailable due to database permissions. Please contact support.",
                    },
                )
            # Re-raise other database errors
            raise

        bookmarked_competitions = []
        now = datetime.now(timezone.utc)
        for (
            bookmark,
            competition,
            submission_ends_at,
            total_pool_amount,
            currency,
            prize_type,
            participants_count,
        ) in bookmarks_rows:
            days_left = None
            if submission_ends_at:
                if submission_ends_at.tzinfo is None:
                    submission_ends_at = submission_ends_at.replace(tzinfo=timezone.utc)
                delta = submission_ends_at - now
                days_left = max(delta.days, 0)

            bookmarked_competitions.append(
                {
                    "bookmark_id": str(bookmark.id),
                    "competition_id": str(competition.id),
                    "competition_title": competition.title,
                    "competition_subtitle": competition.subtitle,
                    "competition_image_url": competition.image_url,
                    "competition_status": competition.status.value if competition.status else None,
                    "bookmarked_at": bookmark.created_at.isoformat(),
                    "prize_pool": {
                        "total_pool_amount": total_pool_amount or 0.0,
                        "currency": currency or "INR",
                        "prize_type": prize_type.value if prize_type else None,
                    },
                    "days_left": days_left,
                    "participants_count": participants_count,
                }
            )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Bookmarked competitions retrieved successfully",
            data={"bookmarked_competitions": bookmarked_competitions},
            meta={
                "total_bookmarks": total_bookmarks,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        )
    except Exception as exc:
        logger.error("Failed to get bookmarked competitions", exc_info=True)
        return CustomBackendError(
            message="Failed to get bookmarked competitions",
            details=str(exc),
        )

