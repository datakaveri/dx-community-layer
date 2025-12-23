from uuid import UUID
import pytz
from sqlalchemy import select, func
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path, Query, status, Body


from ...configs.db_config import get_challenge_db_session
from ...database.challenge.enums import CompetitionStatusEnum
from ...schemas.challenge.competition_requests import CompetitionsSortByEnum
from ...database.challenge.models import (
    Competition,
    CompetitionSubmission,
    CompetitionTimeline,
    CompetitionPrizePool,
    CompetitionParticipant,
    CompetitionEvaluation,
    CompetitionDataset,
    BookmarkedCompetition,
)
from ...middlewares.logging import logger
from ...middlewares.authorization import (
    http_bearer_header,
    http_bearer_header_public,
)
from ...schemas.default_schemas import AuthorizationData
from ...schemas.custom_responses import CustomJSONResponse
from ...schemas.challenge.participant_responses import JOIN_COMPETITION_RESPONSE_MODEL
from ...schemas.challenge.bookmark_responses import (
    BOOKMARK_COMPETITION_RESPONSE_MODEL,
    UNBOOKMARK_COMPETITION_RESPONSE_MODEL,
    BOOKMARKED_COMPETITIONS_RESPONSE_MODEL,
)
from ...schemas.challenge.submission_requests import (
    DownloadSubmissionParams,
    UpdateSubmissionParams,
)
from ...schemas.challenge.submission_responses import (
    CREATE_SUBMISSION_RESPONSE_MODEL,
    LIST_SUBMISSIONS_RESPONSE_MODEL,
)
from ...services.challenge.competition_participant_services import (
    user_join_competition_handler,
)
from ...services.challenge.bookmark_services import (
    bookmark_competition_handler,
    unbookmark_competition_handler,
    get_bookmarked_competitions_handler,
)
from ...services.challenge.submission_services import (
    create_user_submission_handler,
    download_user_submission_handler,
    get_submission_interests_handler,
    get_user_submissions_handler,
    update_user_submission_handler,
)


router = APIRouter(prefix="/users")


@router.get(
    path="/challenges",
    description=(
        "Public endpoint for users to retrieve all published challenges with a lightweight payload. "
        "Returns only basic challenge details for faster responses. Supports pagination."
    ),
)
async def users_list_challenges(
    status_filter: CompetitionStatusEnum | None = Query(
        None,
        alias="status",
        description="Filter by challenge status (defaults to only PUBLISHED if not provided)",
    ),
    sort_by: CompetitionsSortByEnum = Query(
        CompetitionsSortByEnum.NEWEST,
        alias="sort_by",
        description="Sort by field (defaults to NEWEST if not provided)",
    ),
    joined: bool = Query(
        False, alias="joined", description="Filter by joined challenges"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Returns a lightweight list of all *published* challenges for end users.

    The payload intentionally excludes heavy / admin specific metadata like overall totals
    to keep this endpoint fast. Each challenge item includes:
    - id
    - title
    - description
    - image_url
    - prize_pool (amount, currency, type)
    - days_left (based on submission_ends_at, if available)
    """
    logger.info("User List Challenges API is being called")

    # Participants count subquery
    participants_count_sq = (
        select(
            CompetitionParticipant.competition_id.label("c_id"),
            func.count(CompetitionParticipant.id).label("participants_count"),
        )
        .group_by(CompetitionParticipant.competition_id)
        .subquery()
    )

    submission_count_sq = (
        select(
            CompetitionSubmission.competition_id.label("c_id"),
            func.count(CompetitionSubmission.id).label("submission_count"),
        )
        .group_by(CompetitionSubmission.competition_id)
        .subquery()
    )

    # Join with timeline, prize pool, and participants count for minimal fields
    stmt = (
        select(
            Competition.id,
            Competition.title,
            Competition.subtitle,
            Competition.image_url,
            CompetitionTimeline.submission_ends_at,
            CompetitionPrizePool.total_pool_amount,
            CompetitionPrizePool.currency,
            CompetitionPrizePool.prize_type,
            func.coalesce(participants_count_sq.c.participants_count, 0).label(
                "participants_count"
            ),
            func.coalesce(submission_count_sq.c.submission_count, 0).label(
                "submission_count"
            ),
        )
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
        .join(
            submission_count_sq,
            submission_count_sq.c.c_id == Competition.id,
            isouter=True,
        )
    )

    # Apply joined filter if provided
    if joined:
        stmt = stmt.join(
            CompetitionParticipant,
            CompetitionParticipant.competition_id == Competition.id,
            isouter=True,
        )
        stmt = stmt.where(CompetitionParticipant.user_id == authorized_user["user_id"])

    # Apply status filter; default to PUBLISHED if not provided
    if status_filter is not None:
        stmt = stmt.where(Competition.status == status_filter)
    else:
        stmt = stmt.where(Competition.status == CompetitionStatusEnum.PUBLISHED)

    # Get total count for pagination (before applying limit/offset)
    count_stmt = select(func.count()).select_from(Competition)
    if status_filter is not None:
        count_stmt = count_stmt.where(Competition.status == status_filter)
    else:
        count_stmt = count_stmt.where(
            Competition.status == CompetitionStatusEnum.PUBLISHED
        )

    total_competitions = (await db_session.execute(count_stmt)).scalar_one()

    # Calculate pagination
    total_pages = (
        (total_competitions + limit - 1) // limit if total_competitions > 0 else 0
    )

    # Apply ordering
    if sort_by == CompetitionsSortByEnum.NEWEST:
        stmt = stmt.order_by(Competition.published_at.desc().nullslast())
    elif sort_by == CompetitionsSortByEnum.OLDEST:
        stmt = stmt.order_by(Competition.published_at.asc())
    elif sort_by == CompetitionsSortByEnum.HOTTEST:
        stmt = stmt.order_by(
            func.coalesce(participants_count_sq.c.participants_count, 0).desc()
        )

    # Apply pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    rows = (await db_session.execute(stmt)).all()
    now = datetime.now(pytz.timezone("Asia/Kolkata"))

    def get_days_left(timestamp: datetime) -> int:
        now = datetime.now(pytz.UTC)

        # Difference
        diff = (timestamp - now).days

        # If past or today → return 0
        return max(diff, 0)

    competitions = []
    for r in rows:
        days_left = None
        if r.submission_ends_at:
            # Calculate remaining days; clamp at 0 if already ended
            days_left = get_days_left(r.submission_ends_at)

        competitions.append(
            {
                "id": str(r.id),
                "title": r.title,
                "subtitle": r.subtitle,
                "image_url": r.image_url,
                "prize_pool": {
                    "total_pool_amount": r.total_pool_amount or 0.0,
                    "currency": r.currency or "INR",
                    "prize_type": r.prize_type.value if r.prize_type else None,
                },
                "days_left": days_left,
                "participants_count": r.participants_count,
                "submission_count": r.submission_count,
            }
        )

    return CustomJSONResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Challenges retrieved successfully",
        data={"competitions": competitions},
        meta={
            "total_competitions": total_competitions,
            "total_pages": total_pages,
            "current_page": page,
            "limit": limit,
        },
    )


@router.post(
    path="/challenges/{competition_id}/join",
    description="Endpoint for authenticated users to join a published challenge.",
    responses=JOIN_COMPETITION_RESPONSE_MODEL,
    tags=["Challenge APIs"],
)
async def users_join_competition(
    competition_id: UUID = Path(..., description="ID of the challenge to join"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User Join challenge API is being called")
    return await user_join_competition_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/challenges/{competition_id}/bookmark",
    description="Endpoint for authenticated users to bookmark a published challenge.",
    responses=BOOKMARK_COMPETITION_RESPONSE_MODEL,
    tags=["Challenge APIs"],
)
async def users_bookmark_competition(
    competition_id: UUID = Path(..., description="ID of the challenge to bookmark"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User Bookmark Challenge API is being called")
    return await bookmark_competition_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.delete(
    path="/challenges/{competition_id}/bookmark",
    description="Endpoint for authenticated users to unbookmark a challenge.",
    responses=UNBOOKMARK_COMPETITION_RESPONSE_MODEL,
    tags=["Challenge APIs"],
)
async def users_unbookmark_competition(
    competition_id: UUID = Path(..., description="ID of the challenge to unbookmark"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User Unbookmark Challenge API is being called")
    return await unbookmark_competition_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/bookmarks",
    description="Endpoint for authenticated users to get their bookmarked challenges with pagination.",
    responses=BOOKMARKED_COMPETITIONS_RESPONSE_MODEL,
)
async def users_get_bookmarked_competitions(
    sort_by: CompetitionsSortByEnum = Query(
        CompetitionsSortByEnum.NEWEST,
        alias="sort_by",
        description="Sort by field (defaults to NEWEST if not provided)",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User Get Bookmarked Challenges API is being called")
    return await get_bookmarked_competitions_handler(
        authorized_user=authorized_user,
        db_session=db_session,
        sort_by=sort_by,
        page=page,
        limit=limit,
    )


@router.get(
    path="/submissions",
    description="Endpoint for authenticated users to get all their submissions across challenges.",
    responses=LIST_SUBMISSIONS_RESPONSE_MODEL,
)
async def users_list_all_submissions(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User List Submissions API is being called")
    return await get_user_submissions_handler(
        authorized_user=authorized_user,
        db_session=db_session,
        page=page,
        limit=limit,
    )


@router.get(
    path="/challenges/{competition_id}/submissions",
    description="Endpoint for authenticated users to list their submissions for a specific challenge.",
    responses=LIST_SUBMISSIONS_RESPONSE_MODEL,
    tags=["Challenge - Submission APIs"],
)
async def users_list_competition_submissions(
    competition_id: UUID = Path(..., description="ID of the challenge"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User List Challenge Submissions API is being called")
    return await get_user_submissions_handler(
        authorized_user=authorized_user,
        db_session=db_session,
        page=page,
        limit=limit,
        competition_id=competition_id,
    )


@router.put(
    path="/submissions/{submission_id}",
    description="Endpoint for authenticated users to update their submission for a specific challenge.",
)
async def users_update_submission(
    req_params: UpdateSubmissionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User Update Submission API is being called")
    return await update_user_submission_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.post(
    path="/submission/{submission_id}/downloads",
    description="Endpoint for authenticated users to download the submissions for a specific challenge.",
)
async def users_download_submission(
    req_params: DownloadSubmissionParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User Download Submission API is being called")
    return await download_user_submission_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/challenges/{competition_id}/submissions/interests",
    description="Endpoint for authenticated users to get all their submissions across challenges with interests.",
)
async def users_get_submission_interests(
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    logger.info("User Get Submission Interests API is being called")
    return await get_submission_interests_handler(
        authorized_user=authorized_user,
        db_session=db_session,
    )
