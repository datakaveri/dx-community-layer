import math
import pytz
from uuid import UUID
from fastapi import status
from typing import Any, List
from datetime import datetime
from sqlalchemy import and_, exists, func, select
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.challenge.competition_responses import (
    ParticipatedCompetitionsSchema,
    RetrieveBookmarkedCompetitionsSchema,
    RetrieveChanllengeByIDSchema,
    RetrieveCompetitionsLeaderboardsSubmissions,
    RetrieveCompetitionsSchema,
)
from ...schemas.challenge.submission_requests import SortOrder
from ..discussion.search_services import format_tsquery
from ...services.challenge.submission_services import get_s3_file_metadata
from ...configs.s3_config import s3_client
from ...configs.env_config import env_config
from ...middlewares.logging import logger
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ...schemas.challenge.competition_requests import (
    CompetitionsSortByEnum,
    CreateCompetitionParams,
    RetrieveBookmarkedCompetitionsParams,
    RetrieveCompetitionChoices,
    RetrieveCompetitionLeaderboardParams,
    RetrieveCompetitionLeaderboardSortByEnum,
    RetrieveCompetitonsParams,
    RetrieveParticipatedCompetitionsParams,
    RetrieveParticipatedCompetitionsSortByEnum,
    UpdateCompetitionParams,
)
from ...schemas.default_schemas import AuthorizationData
from ...database.challenge.models import (
    BookmarkedCompetition,
    Competition,
    CompetitionParticipant,
    CompetitionSubmission,
    CompetitionTimeline,
    CompetitionPrizePool,
    CompetitionEvaluation,
    CompetitionDataset,
    User,
)
from ...database.challenge.enums import CompetitionStatusEnum, PrizeTypeEnum
from ...database.challenge.enums import CompetitionStatusEnum
from ...schemas.custom_responses import CustomJSONResponse
from ...database.challenge.models import Competition
from ...database.challenge.models import CompetitionTimeline


async def retrieve_challenge_by_id_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves a specific challenge by ID.

    Args:
        competition_id (UUID): The ID of the challenge to retrieve.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved challenge and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(Competition).where(Competition.id == competition_id)

        # -----------------------
        # Execute and fetch
        # -----------------------
        stmt = stmt.options(
            selectinload(Competition.creator),
            selectinload(Competition.prize_pools),
            selectinload(Competition.timelines),
            selectinload(Competition.evaluations),
            selectinload(Competition.datasets),
            selectinload(Competition.participants),
            selectinload(Competition.submissions),
            selectinload(Competition.bookmarked_competitions),
        )
        result = await db_session.execute(stmt)
        chanllenge = result.scalars().one_or_none()

        if not chanllenge:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Challenge not found for the provided challenge id. Please check the challenge id and try again.",
                },
            )

        # -----------------------
        # Serialize
        # -----------------------
        serialized_challenge = RetrieveChanllengeByIDSchema.model_validate(
            chanllenge
        ).model_dump(
            exclude={
                "participant_count",
                "submission_count",
                "is_joined",
                "is_drafted",
                "is_bookmarked",
            }
        )

        serialized_challenge["participant_count"] = len(chanllenge.participants)
        serialized_challenge["submission_count"] = len(chanllenge.submissions)

        serialized_challenge["is_joined"] = any(
            [
                participant.user_id == authorized_user["user_id"]
                for participant in chanllenge.participants
            ]
        )

        serialized_challenge["is_drafted"] = any(
            [
                submission.user_id == authorized_user["user_id"]
                for submission in chanllenge.submissions
            ]
        )

        serialized_challenge["is_bookmarked"] = any(
            [
                bookmark.user_id == authorized_user["user_id"] and bookmark.is_active
                for bookmark in chanllenge.bookmarked_competitions
            ]
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Admin challenge retrieved successfully",
            data=serialized_challenge,
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Challenge retrieval failed",
            details="An error occurred while retrieving the challenge. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def retrieve_competitions_handler(
    req_params: RetrieveCompetitonsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves all challenges accross the TGDex platform.

    Args:
        req_params (RetrieveCompetitonsParams): The request body containing the sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved challenges and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Subquery
        # -----------------------
        participants_count_subq = (
            select(
                CompetitionParticipant.competition_id,
                func.count(CompetitionParticipant.id).label("participants_count"),
            )
            .group_by(CompetitionParticipant.competition_id)
            .subquery()
        )

        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(Competition)

        # -----------------------
        # Apply choice filters
        # -----------------------
        if req_params.choice == RetrieveCompetitionChoices.JOINED:
            if not authorized_user["user_id"]:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message="Unauthorized access",
                    error={
                        "code": "UNAUTHORIZED",
                        "details": "Invalid token. Please provide a valid Bearer token.",
                    },
                )

            stmt = stmt.join(
                CompetitionParticipant,
                CompetitionParticipant.competition_id == Competition.id,
                isouter=True,
            ).where(
                CompetitionParticipant.user_id == authorized_user["user_id"],
            )
            stmt = stmt.where(Competition.status != CompetitionStatusEnum.COMPLETED)
        elif req_params.choice == RetrieveCompetitionChoices.COMPLETED:
            stmt = stmt.where(Competition.status == CompetitionStatusEnum.COMPLETED)

        elif req_params.choice == RetrieveCompetitionChoices.EVALUATION:
            stmt = stmt.where(Competition.status == CompetitionStatusEnum.EVALUATION)

        elif req_params.choice == RetrieveCompetitionChoices.ALL:
            stmt = stmt.where(
                Competition.status.in_(
                    [
                        CompetitionStatusEnum.PUBLISHED,
                        CompetitionStatusEnum.EVALUATION,
                        CompetitionStatusEnum.COMPLETED,
                    ]
                )
            )
            
        else:
            # PUBLISHED = only live + joinable challenges
            now = datetime.now(pytz.timezone("Asia/Kolkata")).date()

            stmt = stmt.join(
                CompetitionTimeline,
                CompetitionTimeline.competition_id == Competition.id,
                isouter=True,
            ).where(
                Competition.status == CompetitionStatusEnum.PUBLISHED,
                CompetitionTimeline.submission_starts_at.isnot(None),
                CompetitionTimeline.submission_ends_at.isnot(None),
                CompetitionTimeline.submission_starts_at <= now,
                CompetitionTimeline.submission_ends_at >= now,
            )

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("simple", formatted_query)

            stmt = stmt.where(Competition.title_vector.op("@@")(ts_query))

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(Competition.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Sorting
        # -----------------------
        if req_params.sort_by == CompetitionsSortByEnum.NEWEST:
            stmt = stmt.order_by(
                Competition.published_at.desc().nullslast(),
                Competition.updated_at.desc(),
            )
        elif req_params.sort_by == CompetitionsSortByEnum.OLDEST:
            stmt = stmt.order_by(
                Competition.published_at.asc().nullslast(),
                Competition.updated_at.desc(),
            )
        elif req_params.sort_by == CompetitionsSortByEnum.HOTTEST:
            stmt = stmt.outerjoin(
                participants_count_subq,
                Competition.id == participants_count_subq.c.competition_id,
            ).order_by(
                func.coalesce(participants_count_subq.c.participants_count, 0).desc(),
                Competition.updated_at.desc(),
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
            selectinload(Competition.timelines),
            selectinload(Competition.prize_pools),
            selectinload(Competition.participants),
            selectinload(Competition.submissions),
        )
        result = await db_session.execute(stmt)
        competitions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_competitions = []

        for competition in competitions:
            serialized_competition = RetrieveCompetitionsSchema.model_validate(
                competition
            ).model_dump(exclude={"participant_count", "submission_count"})

            # Calculate counts
            serialized_competition["participant_count"] = len(
                getattr(competition, "participants", [])
            )
            serialized_competition["submission_count"] = len(
                getattr(competition, "submissions", [])
            )

            serialized_competitions.append(serialized_competition)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Challenges retrieved successfully",
            data={
                "competitions": serialized_competitions,
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
            message="Challenges retrieval failed",
            details="An error occurred while retrieving the challenges. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def retrieve_competition_leaderboard_handler(
    req_params: RetrieveCompetitionLeaderboardParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves the leaderboard for a specific challenge.

    Args:
        req_params (RetrieveChallengeLeaderboardParams): The request body containing the sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved leaderboard and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        competition = await db_session.execute(
            select(Competition.id).where(Competition.id == req_params.competition_id)
        )
        competition = competition.scalars().first()

        if not competition:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Challenge not found",
                error={
                    "code": "NOT_FOUND",
                    "message": "The challenge does not exist. Please contact developers if the issue persists.",
                },
            )

        # -----------------------
        # Base selectable
        # -----------------------
        stmt = (
            select(CompetitionSubmission)
            .join(User, User.id == CompetitionSubmission.user_id)
            .join(Competition, Competition.id == CompetitionSubmission.competition_id)
            .where(
                CompetitionSubmission.competition_id == req_params.competition_id,
                CompetitionSubmission.is_disqualified.is_(False),
            )
        )

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.score:
            stmt = stmt.where(CompetitionSubmission.score == req_params.score)
        elif req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("simple", formatted_query)

            stmt = stmt.where(
                (Competition.title_vector.op("@@")(ts_query))
                | (CompetitionSubmission.title_vector.op("@@")(ts_query))
                | (User.name_vector.op("@@")(ts_query))
            )

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(CompetitionSubmission.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Sorting
        # -----------------------
        if (
            req_params.sort_by
            == RetrieveCompetitionLeaderboardSortByEnum.PARTICIPANT_NAME
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(func.lower(User.name).asc())
            else:
                stmt = stmt.order_by(func.lower(User.name).desc())

        elif (
            req_params.sort_by
            == RetrieveCompetitionLeaderboardSortByEnum.SUBMISSION_TITLE
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(func.lower(CompetitionSubmission.title).asc())
            else:
                stmt = stmt.order_by(func.lower(CompetitionSubmission.title).desc())

        elif req_params.sort_by == RetrieveCompetitionLeaderboardSortByEnum.SCORE:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.score.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.score.desc())

        elif (
            req_params.sort_by == RetrieveCompetitionLeaderboardSortByEnum.SUBMITTED_AT
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.updated_at.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.updated_at.desc())

        # -----------------------
        # Pagination
        # -----------------------
        offset = (req_params.page - 1) * req_params.limit
        stmt = stmt.offset(offset).limit(req_params.limit)

        # -----------------------
        # Execute and fetch
        # -----------------------
        stmt = stmt.options(
            selectinload(CompetitionSubmission.user),
            selectinload(CompetitionSubmission.competition),
        )
        result = await db_session.execute(stmt)
        submissions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_submissions = [
            RetrieveCompetitionsLeaderboardsSubmissions.model_validate(
                submission
            ).model_dump()
            for submission in submissions
        ]

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Challenge leaderboard retrieved successfully",
            data={
                "submissions": serialized_submissions,
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
            message="Challenge leaderboard retrieval failed",
            details="An error occurred while retrieving the challenge leaderboard. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def retrieve_participated_competitions_handler(
    req_params: RetrieveParticipatedCompetitionsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves challenges that the user has participated in.

    Args:
        req_params (RetrieveParticipatedChallengesParams): The request body containing the sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved challenges and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Base selectable
        # -----------------------
        user_submission_exists = (
            exists()
            .where(
                and_(
                    CompetitionSubmission.competition_id == Competition.id,
                    CompetitionSubmission.user_id == authorized_user["user_id"],
                )
            )
            .correlate(Competition)
        )

        stmt = (
            select(Competition)
            .join(
                CompetitionParticipant,
                CompetitionParticipant.competition_id == Competition.id,
            )
            .join(
                CompetitionTimeline,
                CompetitionTimeline.competition_id == Competition.id,
            )
            .join(
                CompetitionPrizePool,
                CompetitionPrizePool.competition_id == Competition.id,
            )
            .where(
                CompetitionParticipant.user_id == authorized_user["user_id"],
                Competition.status != CompetitionStatusEnum.COMPLETED,
                ~exists().where(
                    and_(
                        CompetitionSubmission.competition_id == Competition.id,
                        CompetitionSubmission.user_id == authorized_user["user_id"],
                    )
                ),
                ~and_(
                    Competition.status == CompetitionStatusEnum.EVALUATION,
                    user_submission_exists,
                ),
            )
        )

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("simple", formatted_query)

            stmt = stmt.where((Competition.title_vector.op("@@")(ts_query)))

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(Competition.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Sorting
        # -----------------------
        if req_params.sort_by == RetrieveParticipatedCompetitionsSortByEnum.TITLE:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(func.lower(Competition.title).asc())
            else:
                stmt = stmt.order_by(func.lower(Competition.title).desc())

        elif (
            req_params.sort_by
            == RetrieveParticipatedCompetitionsSortByEnum.TOTAL_POOL_AMOUNT
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionPrizePool.total_pool_amount.asc())
            else:
                stmt = stmt.order_by(CompetitionPrizePool.total_pool_amount.desc())

        elif (
            req_params.sort_by
            == RetrieveParticipatedCompetitionsSortByEnum.SUBMISSION_STARTS_AT
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionTimeline.submission_starts_at.asc())
            else:
                stmt = stmt.order_by(CompetitionTimeline.submission_starts_at.desc())

        elif (
            req_params.sort_by
            == RetrieveParticipatedCompetitionsSortByEnum.SUBMISSION_ENDS_AT
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionTimeline.submission_ends_at.asc())
            else:
                stmt = stmt.order_by(CompetitionTimeline.submission_ends_at.desc())

        # -----------------------
        # Pagination
        # -----------------------
        offset = (req_params.page - 1) * req_params.limit
        stmt = stmt.offset(offset).limit(req_params.limit)

        # -----------------------
        # Execute and fetch
        # -----------------------
        stmt = stmt.options(
            selectinload(Competition.participants),
            selectinload(Competition.prize_pools),
            selectinload(Competition.timelines),
        )
        result = await db_session.execute(stmt)
        competitions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_competitions = [
            ParticipatedCompetitionsSchema.model_validate(competition).model_dump()
            for competition in competitions
        ]

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Participated challenges retrieved successfully",
            data={
                "competitions": serialized_competitions,
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
            message="Participated challenges retrieval failed",
            details="An error occurred while retrieving the participated challenges. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def retrieve_bookmarked_competitions_handler(
    req_params: RetrieveBookmarkedCompetitionsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves challenges that the user has bookmarked.

    Args:
        req_params (RetrieveBookmarkedChallengesParams): The request body containing the sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved challenges and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Subquery
        # -----------------------
        participants_count_subq = (
            select(
                CompetitionParticipant.competition_id,
                func.count(CompetitionParticipant.id).label("participants_count"),
            )
            .group_by(CompetitionParticipant.competition_id)
            .subquery()
        )

        # -----------------------
        # Base selectable
        # -----------------------
        stmt = (
            select(BookmarkedCompetition)
            .join(
                Competition,
                Competition.id == BookmarkedCompetition.competition_id,
            )
            .where(
                BookmarkedCompetition.user_id == authorized_user["user_id"],
                BookmarkedCompetition.is_active.is_(True),
            )
        )

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("simple", formatted_query)

            stmt = stmt.where(Competition.title_vector.op("@@")(ts_query))

        # -----------------------
        # Total count
        # -----------------------
        count_stmt = stmt.with_only_columns(func.count(BookmarkedCompetition.id))
        total_count_result = await db_session.execute(count_stmt)
        total_count = total_count_result.scalar_one()
        total_pages = math.ceil(total_count / req_params.limit) if total_count else 1

        # -----------------------
        # Sorting
        # -----------------------
        if req_params.sort_by == CompetitionsSortByEnum.NEWEST:
            stmt = stmt.order_by(
                BookmarkedCompetition.created_at.desc(),
                Competition.updated_at.desc(),
            )
        elif req_params.sort_by == CompetitionsSortByEnum.OLDEST:
            stmt = stmt.order_by(
                BookmarkedCompetition.created_at.asc(),
                Competition.updated_at.desc(),
            )
        elif req_params.sort_by == CompetitionsSortByEnum.HOTTEST:
            stmt = stmt.outerjoin(
                participants_count_subq,
                Competition.id == participants_count_subq.c.competition_id,
            ).order_by(
                func.coalesce(participants_count_subq.c.participants_count, 0).desc(),
                Competition.updated_at.desc(),
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
            selectinload(BookmarkedCompetition.competition).selectinload(
                BookmarkedCompetition.competition.property.mapper.class_.prize_pools
            ),
            selectinload(BookmarkedCompetition.competition).selectinload(
                BookmarkedCompetition.competition.property.mapper.class_.timelines
            ),
            selectinload(BookmarkedCompetition.competition).selectinload(
                BookmarkedCompetition.competition.property.mapper.class_.participants
            ),
        )
        result = await db_session.execute(stmt)
        bookmarked_competitions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_bookmarked_competitions = []

        for bookmarked_competition in bookmarked_competitions:
            serialized_competition = (
                RetrieveBookmarkedCompetitionsSchema.model_validate(
                    bookmarked_competition
                ).model_dump(exclude={"participant_count"})
            )

            # Calculate counts
            serialized_competition["participant_count"] = len(
                getattr(bookmarked_competition.competition, "participants", [])
            )

            serialized_bookmarked_competitions.append(serialized_competition)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Bookmarked challenges retrieved successfully",
            data={
                "bookmarked_competitions": serialized_bookmarked_competitions,
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
            message="Bookmarked challenges retrieval failed",
            details="An error occurred while retrieving the bookmarked challenges. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def create_competition_handler(
    req_params: CreateCompetitionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        # Ensure we are starting from a clean transaction (in case a prior dep failed)
        try:
            await db_session.rollback()
        except Exception:
            pass

        # Validate basic temporal invariants (only if not draft and dates are provided)
        if (
            not req_params.is_drafted
            and req_params.submission_starts_at
            and req_params.submission_ends_at
        ):
            if req_params.submission_ends_at <= req_params.submission_starts_at:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Bad Request",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "submission_end must be after submission_start",
                    },
                )
            if (
                req_params.evaluation_ends_at
                and req_params.evaluation_ends_at <= req_params.submission_ends_at
            ):
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Bad Request",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "evaluation_end must be after submission_end",
                    },
                )

        # Derive status based on draft/publish schedule
        status_value = CompetitionStatusEnum.DRAFT
        published_at = None
        scheduled_publish_at = None
        now = datetime.now(pytz.timezone("Asia/Kolkata"))
        if not req_params.is_drafted:
            if req_params.publish_schedule:
                status_value = CompetitionStatusEnum.SCHEDULED
                scheduled_publish_at = req_params.publish_schedule
            else:
                status_value = CompetitionStatusEnum.PUBLISHED
                published_at = now

        # Create Competition
        competition = Competition(
            title=req_params.title,
            subtitle=req_params.subtitle,
            overview=req_params.overview,
            detailed_description=req_params.description,
            status=status_value,
            created_by=authorized_user["user_id"],
            published_at=published_at,
            scheduled_publish_at=scheduled_publish_at,
            image_url=req_params.comp_image_url,
            constraints=req_params.constraints,
            other_resources=req_params.other_resources,
        )
        db_session.add(competition)
        await db_session.flush()  # assign id

        if req_params.rules_and_guidelines:
            file_name = req_params.rules_and_guidelines.split("/")[-1]
            metadata = get_s3_file_metadata(req_params.rules_and_guidelines)

            if "error" in metadata:
                logger.error(
                    f"{authorized_user['email']} - Error fetching metadata for {req_params.rules_and_guidelines}: {metadata['error']}"
                )
                await db_session.rollback()
                return CustomBackendError(
                    message="Discussion creation failed",
                    details="An error occurred while creating the discussion. Please contact developers if the issue persists.",
                )

            # build permanent key and copy object to permanent location
            permanent_s3_key = f"public/{authorized_user['user_id']}/{competition.id}/rules_and_guidelines/{file_name}"

            try:
                s3_client.copy_object(
                    Bucket=env_config.CHALLENGE_S3_BUCKET,
                    CopySource=f"{env_config.CHALLENGE_S3_BUCKET}/{req_params.rules_and_guidelines}",
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

            competition.rules_and_guidelines = permanent_s3_key

        # Timeline (only create if dates are provided)
        if (
            req_params.submission_starts_at is not None
            or req_params.submission_ends_at is not None
        ):
            if competition.published_at and req_params.submission_starts_at:
                if req_params.submission_starts_at < competition.published_at.date():
                    await db_session.rollback()

                    logger.error(
                        f"{authorized_user['email']} - submission_starts_at must be after published_at"
                    )
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Bad Request",
                        error={
                            "code": "BAD_REQUEST",
                            "details": "submission_start must be after published_at",
                        },
                    )

            elif competition.scheduled_publish_at and req_params.submission_starts_at:
                if (
                    req_params.submission_starts_at
                    < competition.scheduled_publish_at.date()
                ):
                    await db_session.rollback()

                    logger.error(
                        f"{authorized_user['email']} - submission_starts_at must be after scheduled_publish_at"
                    )
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Bad Request",
                        error={
                            "code": "BAD_REQUEST",
                            "details": "submission_start must be after scheduled_publish_at",
                        },
                    )

            timeline = CompetitionTimeline(
                competition_id=competition.id,
                submission_starts_at=req_params.submission_starts_at,
                submission_ends_at=req_params.submission_ends_at,
                evaluation_ends_at=req_params.evaluation_ends_at,
            )
            db_session.add(timeline)

        # Prize Pool (only create if prize info is provided)
        if (
            req_params.prize_type is not None
            or req_params.total_pool_amount is not None
        ):
            # Validate and normalize currency
            currency = (
                req_params.currency.strip().upper() if req_params.currency else "INR"
            )
            if len(currency) > 3:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Validation Error",
                    error={
                        "code": "VALIDATION_ERROR",
                        "details": f"Currency code must be at most 3 characters. Received: '{currency}' ({len(currency)} characters)",
                    },
                )
            if len(currency) == 0:
                currency = "INR"  # Default to INR if empty

            prize_pool = CompetitionPrizePool(
                competition_id=competition.id,
                prize_type=req_params.prize_type
                or PrizeTypeEnum.CASH,  # Default if draft
                total_pool_amount=req_params.total_pool_amount
                or 0.0,  # Default if draft
                currency=currency,
                prize_description=req_params.prize_pool_description,
            )
            db_session.add(prize_pool)

        # Evaluation (always create, can be empty)
        evaluation = CompetitionEvaluation(
            competition_id=competition.id,
            evaluation_criteria=req_params.evaluation_criteria_definition,
            submission_criteria=req_params.submission_file_definition,
        )
        db_session.add(evaluation)

        # Dataset and resources (always create, can be empty)
        competition_dataset = CompetitionDataset(
            competition_id=competition.id,
            description=req_params.dataset_description,
            datasets=req_params.data_models,
            ai_models=req_params.ai_models,
        )
        db_session.add(competition_dataset)
        await db_session.flush()

        if req_params.additional_assets:
            attachment_objs: List[dict[str, Any]] = []

            for asset in req_params.additional_assets:
                s3_key = asset["object_key"]
                file_name = s3_key.split("/")[-1]
                metadata = get_s3_file_metadata(s3_key)

                if "error" in metadata:
                    logger.error(
                        f"{authorized_user['email']} - Error fetching metadata for {s3_key}: {metadata['error']}"
                    )
                    await db_session.rollback()
                    return CustomBackendError(
                        message="Discussion creation failed",
                        details="An error occurred while creating the discussion. Please contact developers if the issue persists.",
                    )

                # build permanent key and copy object to permanent location
                permanent_s3_key = f"private/{authorized_user['user_id']}/{competition.id}/datasets/additional_assets/{file_name}"

                try:
                    s3_client.copy_object(
                        Bucket=env_config.CHALLENGE_S3_BUCKET,
                        CopySource=f"{env_config.CHALLENGE_S3_BUCKET}/{s3_key}",
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
                    {
                        "file_name": file_name,
                        "metadata": metadata,
                        "s3_key": permanent_s3_key,
                        "description": asset["description"],
                    }
                )

            if attachment_objs:
                competition_dataset.additional_assets = attachment_objs

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Resource created successfully",
            data={
                "competition_id": str(competition.id),
                "status": competition.status.value,
            },
        )
    except Exception as e:
        logger.error(f"Create challenge failed: {e}", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(message="Failed to create challenge", details=str(e))


async def update_competition_handler(
    competition_id: UUID,
    req_params: UpdateCompetitionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        # Ensure we are starting from a clean transaction
        try:
            await db_session.rollback()
        except Exception:
            pass

        # Fetch the competition
        stmt = select(Competition).where(Competition.id == competition_id)
        result = await db_session.execute(stmt)
        competition = result.scalar_one_or_none()

        if not competition:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Challenge not found.",
                },
            )

        # Check if user is the creator
        if competition.created_by != authorized_user["user_id"]:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "details": "You are not authorized to update this challenge.",
                },
            )

        # Only allow updates to drafts or scheduled competitions
        if competition.status not in [
            CompetitionStatusEnum.DRAFT,
            CompetitionStatusEnum.SCHEDULED,
        ]:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "BAD_REQUEST",
                    "details": "Only draft or scheduled challenges can be updated.",
                },
            )

        # Update competition fields if provided
        if req_params.title is not None:
            competition.title = req_params.title
        if req_params.subtitle is not None:
            competition.subtitle = req_params.subtitle
        if req_params.overview is not None:
            competition.overview = req_params.overview
        if req_params.description is not None:
            competition.detailed_description = req_params.description
        if req_params.comp_image_url is not None:
            competition.image_url = req_params.comp_image_url
        if req_params.constraints is not None:
            competition.constraints = req_params.constraints
        if req_params.rules_and_guidelines is not None:
            competition.rules_and_guidelines = req_params.rules_and_guidelines

        # Handle status change (draft to publish)
        now = datetime.now(pytz.timezone("Asia/Kolkata"))
        if req_params.is_drafted is not None:
            if not req_params.is_drafted:
                # Publishing the competition
                if req_params.publish_schedule:
                    competition.status = CompetitionStatusEnum.SCHEDULED
                    competition.scheduled_publish_at = req_params.publish_schedule
                    competition.published_at = None
                else:
                    competition.status = CompetitionStatusEnum.PUBLISHED
                    competition.published_at = now
                    competition.scheduled_publish_at = None
            else:
                # Keeping as draft
                competition.status = CompetitionStatusEnum.DRAFT
                competition.published_at = None
                competition.scheduled_publish_at = None

        competition.updated_at = now
        await db_session.flush()

        # Update or create Timeline
        timeline_stmt = select(CompetitionTimeline).where(
            CompetitionTimeline.competition_id == competition_id
        )
        timeline_result = await db_session.execute(timeline_stmt)
        timeline = timeline_result.scalar_one_or_none()

        if (
            req_params.submission_starts_at is not None
            or req_params.submission_ends_at is not None
        ):
            if competition.published_at and req_params.submission_starts_at:
                if req_params.submission_starts_at < competition.published_at.date():
                    await db_session.rollback()

                    logger.error(
                        f"{authorized_user['email']} - submission_starts_at must be after published_at"
                    )
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Bad Request",
                        error={
                            "code": "BAD_REQUEST",
                            "details": "submission_start must be after published_at",
                        },
                    )

            elif competition.scheduled_publish_at and req_params.submission_starts_at:
                if (
                    req_params.submission_starts_at
                    < competition.scheduled_publish_at.date()
                ):
                    await db_session.rollback()

                    logger.error(
                        f"{authorized_user['email']} - submission_starts_at must be after scheduled_publish_at"
                    )
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Bad Request",
                        error={
                            "code": "BAD_REQUEST",
                            "details": "submission_start must be after scheduled_publish_at",
                        },
                    )

            if timeline:
                if req_params.submission_starts_at is not None:
                    timeline.submission_starts_at = req_params.submission_starts_at
                if req_params.submission_ends_at is not None:
                    timeline.submission_ends_at = req_params.submission_ends_at
                if req_params.evaluation_ends_at is not None:
                    timeline.evaluation_ends_at = req_params.evaluation_ends_at
            else:
                timeline = CompetitionTimeline(
                    competition_id=competition.id,
                    submission_starts_at=req_params.submission_starts_at,
                    submission_ends_at=req_params.submission_ends_at,
                    evaluation_ends_at=req_params.evaluation_ends_at,
                )
                db_session.add(timeline)

        # Validate temporal invariants if dates are being updated
        if timeline and timeline.submission_starts_at and timeline.submission_ends_at:
            if timeline.submission_ends_at <= timeline.submission_starts_at:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Bad Request",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "submission_end must be after submission_start",
                    },
                )
            if (
                timeline.evaluation_ends_at
                and timeline.evaluation_ends_at <= timeline.submission_ends_at
            ):
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Bad Request",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "evaluation_end must be after submission_end",
                    },
                )

        # Update or create Prize Pool
        prize_pool_stmt = select(CompetitionPrizePool).where(
            CompetitionPrizePool.competition_id == competition_id
        )
        prize_pool_result = await db_session.execute(prize_pool_stmt)
        prize_pool = prize_pool_result.scalar_one_or_none()

        if (
            req_params.prize_type is not None
            or req_params.total_pool_amount is not None
            or req_params.currency is not None
            or req_params.prize_pool_description is not None
        ):
            currency = (
                req_params.currency.strip().upper()
                if req_params.currency
                else (prize_pool.currency if prize_pool else "INR")
            )
            if len(currency) > 3:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Validation Error",
                    error={
                        "code": "VALIDATION_ERROR",
                        "details": f"Currency code must be at most 3 characters. Received: '{currency}' ({len(currency)} characters)",
                    },
                )
            if len(currency) == 0:
                currency = "INR"

            if prize_pool:
                if req_params.prize_type is not None:
                    prize_pool.prize_type = req_params.prize_type
                if req_params.total_pool_amount is not None:
                    prize_pool.total_pool_amount = req_params.total_pool_amount
                if req_params.currency is not None:
                    prize_pool.currency = currency
                if req_params.prize_pool_description is not None:
                    prize_pool.prize_description = req_params.prize_pool_description
            else:
                prize_pool = CompetitionPrizePool(
                    competition_id=competition.id,
                    prize_type=req_params.prize_type or PrizeTypeEnum.CASH,
                    total_pool_amount=req_params.total_pool_amount or 0.0,
                    currency=currency,
                    prize_description=req_params.prize_pool_description,
                )
                db_session.add(prize_pool)

        # Update or create Evaluation
        evaluation_stmt = select(CompetitionEvaluation).where(
            CompetitionEvaluation.competition_id == competition_id
        )
        evaluation_result = await db_session.execute(evaluation_stmt)
        evaluation = evaluation_result.scalar_one_or_none()

        if (
            req_params.evaluation_criteria_definition is not None
            or req_params.submission_file_definition is not None
        ):
            if evaluation:
                if req_params.evaluation_criteria_definition is not None:
                    evaluation.evaluation_criteria = (
                        req_params.evaluation_criteria_definition
                    )
                if req_params.submission_file_definition is not None:
                    evaluation.submission_criteria = (
                        req_params.submission_file_definition
                    )
            else:
                evaluation = CompetitionEvaluation(
                    competition_id=competition.id,
                    evaluation_criteria=req_params.evaluation_criteria_definition,
                    submission_criteria=req_params.submission_file_definition,
                )
                db_session.add(evaluation)

        # Update or create Dataset
        dataset_stmt = select(CompetitionDataset).where(
            CompetitionDataset.competition_id == competition_id
        )
        dataset_result = await db_session.execute(dataset_stmt)
        competition_dataset = dataset_result.scalar_one_or_none()

        if (
            req_params.dataset_description is not None
            or req_params.data_models is not None
            or req_params.ai_models is not None
            or req_params.other_resources is not None
            or req_params.additional_assets is not None
        ):
            if competition_dataset:
                if req_params.dataset_description is not None:
                    competition_dataset.description = req_params.dataset_description
                if req_params.data_models is not None:
                    competition_dataset.datasets = req_params.data_models
                if req_params.ai_models is not None:
                    competition_dataset.ai_models = req_params.ai_models
                if (
                    req_params.other_resources is not None
                    or req_params.additional_assets is not None
                ):
                    competition_dataset.additional_assets = (
                        {
                            "other_resources": req_params.other_resources,
                            "assets": req_params.additional_assets,
                        }
                        if (req_params.other_resources or req_params.additional_assets)
                        else None
                    )
            else:
                competition_dataset = CompetitionDataset(
                    competition_id=competition.id,
                    description=req_params.dataset_description,
                    datasets=req_params.data_models,
                    ai_models=req_params.ai_models,
                    additional_assets=(
                        {
                            "other_resources": req_params.other_resources,
                            "assets": req_params.additional_assets,
                        }
                        if (req_params.other_resources or req_params.additional_assets)
                        else None
                    ),
                )
                db_session.add(competition_dataset)

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Resource updated successfully",
            data={
                "competition_id": str(competition.id),
                "status": competition.status.value,
            },
        )
    except Exception as e:
        logger.error(f"Update challenge failed: {e}", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(message="Failed to update challenge", details=str(e))


async def delete_competition_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        try:
            await db_session.rollback()
        except Exception:
            pass

        stmt = select(Competition).where(Competition.id == competition_id)
        result = await db_session.execute(stmt)
        competition = result.scalar_one_or_none()

        if not competition:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Challenge not found.",
                },
            )

        if competition.created_by != authorized_user["user_id"]:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "details": "You are not authorized to delete this challenge.",
                },
            )

        if competition.status == CompetitionStatusEnum.PUBLISHED:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "BAD_REQUEST",
                    "details": "Published challenges cannot be deleted.",
                },
            )

        await db_session.delete(competition)
        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Resource deleted successfully",
            data={
                "competition_id": str(competition_id),
            },
        )
    except Exception as e:
        logger.error(f"Delete challenge failed: {e}", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(message="Failed to delete challenge", details=str(e))


async def announce_result_service(competition_id: UUID, db: AsyncSession):
    query = select(CompetitionTimeline).where(
        CompetitionTimeline.competition_id == competition_id
    )
    result = await db.execute(query)
    timeline = result.scalar_one_or_none()

    if not timeline:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
            message="Challenge timeline not found.",
        )

    # Fix: timezone-aware datetime
    current_date = datetime.now(pytz.timezone("Asia/Kolkata")).date()

    if not timeline.submission_ends_at:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Submission end date not set.",
        )

    if timeline.submission_ends_at >= current_date:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Submission period has not ended yet.",
        )

    update_stmt = (
        update(Competition)
        .where(Competition.id == competition_id)
        .values(
            status=CompetitionStatusEnum.COMPLETED,
            updated_at=datetime.now(pytz.timezone("Asia/Kolkata")),
            results_announced_at=datetime.now(pytz.timezone("Asia/Kolkata")),
        )
    )

    await db.execute(update_stmt)
    await db.commit()

    return CustomJSONResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Result has been announced successfully",
    )


async def admin_announce_competition_result_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Announces the results for a challenge.

    Args:
        challenge_id (UUID): The ID of the challenge to announce results for.
        authorized_user (AuthorizationData): The authenticated admin user.
        db_session (AsyncSession): The database session.

    Returns:
        CustomJSONResponse: A JSON response indicating success or failure.

    """
    logger.info(f"{authorized_user['email']} - Execution started")
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        competition_stmt = select(Competition).where(Competition.id == competition_id)
        competition_stmt = competition_stmt.options(
            selectinload(Competition.timelines),
            selectinload(Competition.submissions),
        )
        competition = await db_session.execute(competition_stmt)
        competition = competition.scalars().one_or_none()

        if not competition:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Challenge not found",
                error={
                    "code": "NOT_FOUND",
                    "message": "The challenge does not exist. Please contact developers if the issue persists.",
                },
            )

        if not competition.timelines:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Challenge has no timeline.",
                error={
                    "code": "BAD_REQUEST",
                    "message": "The challenge has no timeline. Please contact developers if the issue persists.",
                },
            )

        if not competition.timelines.submission_ends_at:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Submission end date not set.",
                error={
                    "code": "BAD_REQUEST",
                    "message": "The challenge has no submission end date. Please contact developers if the issue persists.",
                },
            )

        if competition.timelines.submission_ends_at >= current_timestamp.date():
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Submission period has not ended yet.",
                error={
                    "code": "BAD_REQUEST",
                    "message": "The submission period has not ended yet. Please contact developers if the issue persists.",
                },
            )

        if any(
            submission.is_disqualified == False and submission.score in [None, 0]
            for submission in competition.submissions
        ):
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Submissions have not been evaluated yet.",
                error={
                    "code": "BAD_REQUEST",
                    "message": "Please evaluate all the submissions before announcing the results. Please contact developers if the issue persists.",
                },
            )

        competition.status = CompetitionStatusEnum.COMPLETED
        competition.updated_at = current_timestamp
        competition.results_announced_at = current_timestamp

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Result has been announced successfully",
        )

    except Exception as e:
        await db_session.rollback()

        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to announce results",
            details="An error occurred while announcing the results. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
