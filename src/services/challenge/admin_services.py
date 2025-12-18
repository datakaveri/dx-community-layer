from datetime import datetime
import math
from uuid import UUID
from fastapi import status
import pytz
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ..discussion.search_services import format_tsquery
from ...schemas.default_schemas import AuthorizationData
from ...database.challenge.enums import CompetitionStatusEnum
from ...schemas.challenge.submission_requests import SortOrder
from ...schemas.custom_responses import CustomBackendError, CustomJSONResponse
from ...schemas.challenge.admin_responses import (
    AdminRetrieveCompetitionSubmissionCompetitionSchema,
    AdminRetrieveCompetitionSubmissionSchema,
    AdminRetrieveCompetitionsSchema,
)
from ...schemas.challenge.admin_requests import (
    AdminRetreiveCompetitionsSortBy,
    AdminRetrieveCompetitionSubmissionsParams,
    AdminRetrieveCompetitionSubmissionsSortByEnum,
    AdminRetrieveCompetitionsParams,
)
from ...database.challenge.models import (
    Competition,
    CompetitionSubmission,
    CompetitionTimeline,
    CompetitionPrizePool,
    CompetitionParticipant,
    CompetitionEvaluation,
    CompetitionDataset,
    User,
)


async def admin_retrieve_challenges_handler(
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
    page: int,
    limit: int,
    status_filter: CompetitionStatusEnum | None,
    sort_by: str,
) -> CustomJSONResponse:
    """
    Retrieves a paginated list of challenges for the admin panel.

    This handler:
    - Applies optional status filter (Draft, Scheduled, Live, etc.)
    - Computes participants and submissions count per challenge
    - Supports sorting by:
        - "Hottest" (most participants)
        - "Newest"  (latest contextual date)
        - "Oldest"  (oldest contextual date)
    - Returns pagination + meta information for the admin UI.

    Args:
        authorized_user: Authenticated admin user data.
        db_session: Active async DB session.
        page: Page number (1-based).
        limit: Number of items per page.
        status_filter: Optional challenge status to filter on.
        sort_by: Sorting strategy - "Hottest" | "Newest" | "Oldest".

    Returns:
        CustomJSONResponse: List of challenges plus pagination metadata.
    """
    logger.info(
        f"{authorized_user['email']} - Admin Retrieve Challenges handler started"
    )

    # Participants count subquery
    participants_count_sq = (
        select(
            CompetitionParticipant.competition_id.label("c_id"),
            func.count(CompetitionParticipant.id).label("participants_count"),
        )
        .group_by(CompetitionParticipant.competition_id)
        .subquery()
    )

    # Submission count subquery
    submission_count_sq = (
        select(
            CompetitionSubmission.competition_id.label("c_id"),
            func.count(CompetitionSubmission.id).label("submission_count"),
        )
        .group_by(CompetitionSubmission.competition_id)
        .subquery()
    )

    # Base query
    stmt = (
        select(
            Competition.id,
            Competition.title,
            Competition.subtitle,
            Competition.overview,
            Competition.detailed_description.label("description"),
            Competition.image_url,
            Competition.status,
            Competition.published_at,
            Competition.scheduled_publish_at,
            Competition.updated_at,
            CompetitionTimeline.submission_starts_at,
            CompetitionTimeline.submission_ends_at,
            CompetitionTimeline.evaluation_ends_at,
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

    # Status filter
    if status_filter is not None:
        stmt = stmt.where(Competition.status == status_filter)

    # Overall counts (ignores filters)
    overall_counts_result = await db_session.execute(
        select(Competition.status, func.count()).group_by(Competition.status)
    )

    status_counts = {status.value: 0 for status in CompetitionStatusEnum}
    overall_total_competitions = 0
    for status_value, count in overall_counts_result:
        overall_total_competitions += count
        if status_value:
            status_counts[status_value.value] = count
        else:
            status_counts.setdefault("UNKNOWN", 0)
            status_counts["UNKNOWN"] += count

    # Filtered total count (for pagination)
    filtered_count_stmt = select(func.count()).select_from(Competition)
    if status_filter is not None:
        filtered_count_stmt = filtered_count_stmt.where(
            Competition.status == status_filter
        )
    filtered_total_competitions = (
        await db_session.execute(filtered_count_stmt)
    ).scalar_one()

    total_pages = (
        (filtered_total_competitions + limit - 1) // limit
        if filtered_total_competitions > 0
        else 0
    )

    # Determine base sort column depending on status filter
    sort_date_column = Competition.published_at
    sort_date_attr = "published_at"
    if status_filter == CompetitionStatusEnum.SCHEDULED:
        sort_date_column = Competition.scheduled_publish_at
        sort_date_attr = "scheduled_publish_at"
    elif status_filter == CompetitionStatusEnum.DRAFT:
        sort_date_column = Competition.updated_at
        sort_date_attr = "updated_at"

    # Sorting
    if sort_by == "Hottest":
        stmt = stmt.order_by(
            func.coalesce(participants_count_sq.c.participants_count, 0).desc(),
            sort_date_column.desc().nullslast(),
        )
    elif sort_by == "Newest":
        stmt = stmt.order_by(sort_date_column.desc().nullslast())
    else:  # Oldest
        stmt = stmt.order_by(sort_date_column.asc().nullsfirst())

    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    rows = (await db_session.execute(stmt)).all()

    data = []
    for r in rows:
        sorting_date_value = getattr(r, sort_date_attr)
        data.append(
            {
                "id": str(r.id),
                "title": r.title,
                "subtitle": r.subtitle,
                "overview": r.overview,
                "description": r.description,
                "prize_pool": {
                    "total_pool_amount": r.total_pool_amount or 0.0,
                    "currency": r.currency or "INR",
                    "prize_type": r.prize_type.value if r.prize_type else None,
                },
                "dates": {
                    "submission_starts_at": r.submission_starts_at,
                    "submission_ends_at": r.submission_ends_at,
                    "evaluation_ends_at": r.evaluation_ends_at,
                    "published_at": r.published_at,
                    "scheduled_publish_at": r.scheduled_publish_at,
                    "updated_at": r.updated_at,
                },
                "image_url": r.image_url,
                "participants_count": r.participants_count,
                "submission_count": r.submission_count,
                "status": r.status.value if r.status else None,
                "sorting_reference": {
                    "sort_by": sort_by,
                    "date_field": sort_date_attr,
                    "date_value": sorting_date_value,
                },
            }
        )

    return CustomJSONResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Challenges retrieved successfully",
        data={"competitions": data},
        meta={
            "total_counts": {
                "total_competitions": overall_total_competitions,
                "by_status": status_counts,
            },
            "total_pages": total_pages,
            "current_page": page,
            "limit": limit,
            "sorting": {
                "applied_sort_by": sort_by,
                "date_field": sort_date_attr,
                "status_filter": status_filter.value if status_filter else None,
            },
        },
    )


async def admin_retrieve_competitions_handler(
    req_params: AdminRetrieveCompetitionsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves a list of challenges for the admin panel.

    Args:
        req_params (AdminRetrieveChallengesParams): The request body containing the pagination and filters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved challenges and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Count by status
        # -----------------------
        count_by_status = await db_session.execute(
            select(Competition.status, func.count()).group_by(Competition.status)
        )

        counts_map = {status.value: 0 for status in CompetitionStatusEnum}
        for status_value, count in count_by_status:
            if status_value:
                counts_map[status_value.value] = count
            else:
                counts_map.setdefault("UNKNOWN", 0)
                counts_map["UNKNOWN"] += count

        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(Competition)

        # -----------------------
        # Apply choice filters
        # -----------------------
        if req_params.choice:
            stmt = stmt.where(Competition.status == req_params.choice)

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("english", formatted_query)

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
        if req_params.sort_by == AdminRetreiveCompetitionsSortBy.TITLE:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(Competition.title.asc())
            else:
                stmt = stmt.order_by(Competition.title.desc())

        elif req_params.sort_by == AdminRetreiveCompetitionsSortBy.PUBLISHED_AT:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(Competition.published_at.asc())
            else:
                stmt = stmt.order_by(Competition.published_at.desc())

        elif req_params.sort_by == AdminRetreiveCompetitionsSortBy.EVALUATION_ENDS_AT:
            stmt = stmt.outerjoin(
                CompetitionTimeline,
                CompetitionTimeline.competition_id == Competition.id,
            )
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionTimeline.evaluation_ends_at.asc())
            else:
                stmt = stmt.order_by(CompetitionTimeline.evaluation_ends_at.desc())

        elif req_params.sort_by == AdminRetreiveCompetitionsSortBy.SCHEDULED_PUBLISH_AT:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(Competition.scheduled_publish_at.asc())
            else:
                stmt = stmt.order_by(Competition.scheduled_publish_at.desc())

        elif req_params.sort_by == AdminRetreiveCompetitionsSortBy.UPDATED_AT:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(Competition.updated_at.asc())
            else:
                stmt = stmt.order_by(Competition.updated_at.desc())

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
            serialized_competition = AdminRetrieveCompetitionsSchema.model_validate(
                competition
            ).model_dump(exclude={"participant_count", "submission_count", "days_left"})

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
                "count_by_status": counts_map,
            },
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Admin challenges retrieval failed",
            details="An error occurred while retrieving the admin challenges. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def admin_retrieve_competition_submissions_handler(
    req_params: AdminRetrieveCompetitionSubmissionsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves all submissions for a challenge.

    Args:
        req_params (AdminRetrieveChallengeSubmissionsParams): The request body containing the challenge ID and pagination parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved submissions and relevant metadata.
    """
    logger.info(
        f"{authorized_user['email']} - Admin Retrieve Challenge Submissions handler started"
    )

    try:
        competition_stmt = select(Competition).where(
            Competition.id == req_params.competition_id
        )
        competition = await db_session.execute(competition_stmt)
        competition = competition.scalars().one_or_none()

        if not competition:
            logger.error(
                f"{authorized_user['email']} - Challenge not found (id={req_params.discussion_id})"
            )
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Challenge not found",
                error={
                    "code": "NOT_FOUND",
                    "message": "The challenge you are trying to retrieve submissions does not exist. Please contact support if the issue persists.",
                },
            )

        # -----------------------
        # Base selectable
        # -----------------------
        stmt = (
            select(CompetitionSubmission)
            .join(User, User.id == CompetitionSubmission.user_id)
            .where(CompetitionSubmission.competition_id == req_params.competition_id)
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
            == AdminRetrieveCompetitionSubmissionsSortByEnum.PARTICIPANT_NAME
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(func.lower(User.name).asc())
            else:
                stmt = stmt.order_by(func.lower(User.name).desc())

        elif (
            req_params.sort_by
            == AdminRetrieveCompetitionSubmissionsSortByEnum.SUBMITTED_AT
        ):
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.updated_at.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.updated_at.desc())

        elif req_params.sort_by == AdminRetrieveCompetitionSubmissionsSortByEnum.TITLE:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.title.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.title.desc())

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
        )
        result = await db_session.execute(stmt)
        submissions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_submissions = [
            AdminRetrieveCompetitionSubmissionSchema.model_validate(submission)
            for submission in submissions
        ]

        serialized_competition = (
            AdminRetrieveCompetitionSubmissionCompetitionSchema.model_validate(
                competition
            )
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Admin challenge submissions retrieved successfully",
            data={
                "submissions": serialized_submissions,
                "competition": serialized_competition,
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
            message="Admin challenge submissions retrieval failed",
            details="An error occurred while retrieving the admin challenge submissions. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def admin_retrieve_challenge_dataset_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves dataset (databanks, AI models, additional assets) for a given challenge.

    Args:
        challenge_id: ID of the challenge whose dataset needs to be fetched.
        authorized_user: Authenticated admin user data.
        db_session: Active async DB session.

    Returns:
        CustomJSONResponse: Dataset details or 404 if not found.
    """
    logger.info(
        f"{authorized_user['email']} - Admin Retrieve Challenge Dataset handler started"
    )

    stmt = select(CompetitionDataset).where(
        CompetitionDataset.competition_id == competition_id
    )
    result = await db_session.execute(stmt)
    dataset = result.scalar_one_or_none()

    if not dataset:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
            message="Resource not found",
            error={
                "code": "NOT_FOUND",
                "details": "Dataset not found for the provided challenge id.",
            },
        )

    data = {
        "id": str(dataset.id),
        "competition_id": str(dataset.competition_id),
        "description": dataset.description,
        "databanks": dataset.datasets,
        "ai_models": dataset.ai_models,
        "additional_assets": dataset.additional_assets,
    }

    return CustomJSONResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Dataset retrieved successfully",
        data=data,
    )


async def admin_retrieve_challenge_by_id_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves a single challenge with full details for the admin panel.

    This includes:
    - Core challenge details
    - Timeline (submission / evaluation dates)
    - Prize pool info
    - Evaluation criteria
    - Dataset (models, data, additional assets)
    - Participants and submissions count
    - Draft status flag

    Args:
        challenge_id: ID of the challenge to retrieve.
        authorized_user: Authenticated admin user data.
        db_session: Active async DB session.

    Returns:
        CustomJSONResponse: Challenge details or 404 if not found.
    """
    logger.info(
        f"{authorized_user['email']} - Admin Retrieve Challenge by ID handler started"
    )

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

    stmt = (
        select(
            Competition.id,
            Competition.title,
            Competition.subtitle,
            Competition.overview,
            Competition.detailed_description.label("description"),
            Competition.image_url,
            Competition.status,
            Competition.published_at,
            Competition.scheduled_publish_at,
            Competition.updated_at,
            Competition.created_by,
            Competition.constraints,
            Competition.rules_and_guidelines,
            CompetitionTimeline.submission_starts_at,
            CompetitionTimeline.submission_ends_at,
            CompetitionTimeline.evaluation_ends_at,
            CompetitionPrizePool.total_pool_amount,
            CompetitionPrizePool.currency,
            CompetitionPrizePool.prize_type,
            CompetitionPrizePool.prize_description,
            CompetitionEvaluation.evaluation_criteria,
            CompetitionEvaluation.submission_criteria,
            CompetitionDataset.description.label("dataset_description"),
            CompetitionDataset.datasets,
            CompetitionDataset.ai_models,
            CompetitionDataset.additional_assets,
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
            CompetitionEvaluation,
            CompetitionEvaluation.competition_id == Competition.id,
            isouter=True,
        )
        .join(
            CompetitionDataset,
            CompetitionDataset.competition_id == Competition.id,
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
        .where(Competition.id == competition_id)
    )

    result = await db_session.execute(stmt)
    row = result.first()

    if not row:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
            message="Resource not found",
            error={
                "code": "NOT_FOUND",
                "details": "Challenge not found.",
            },
        )

    other_resources = None
    additional_assets = None
    if row.additional_assets:
        if isinstance(row.additional_assets, dict):
            other_resources = row.additional_assets.get("other_resources")
            additional_assets = row.additional_assets.get("assets")

    data = {
        "id": str(row.id),
        "title": row.title,
        "subtitle": row.subtitle,
        "overview": row.overview,
        "description": row.description,
        "image_url": row.image_url,
        "status": row.status.value if row.status else None,
        "constraints": row.constraints,
        "rules_and_guidelines": row.rules_and_guidelines,
        "prize_pool": {
            "total_pool_amount": row.total_pool_amount or 0.0,
            "currency": row.currency or "INR",
            "prize_type": row.prize_type.value if row.prize_type else None,
            "prize_description": row.prize_description,
        },
        "timeline": {
            "submission_starts_at": row.submission_starts_at,
            "submission_ends_at": row.submission_ends_at,
            "evaluation_ends_at": row.evaluation_ends_at,
        },
        "dates": {
            "published_at": row.published_at,
            "scheduled_publish_at": row.scheduled_publish_at,
            "updated_at": row.updated_at,
        },
        "evaluation": {
            "evaluation_criteria": row.evaluation_criteria,
            "submission_criteria": row.submission_criteria,
        },
        "dataset": {
            "description": row.dataset_description,
            "data_models": row.datasets,
            "ai_models": row.ai_models,
            "other_resources": other_resources,
            "additional_assets": additional_assets,
        },
        "participants_count": row.participants_count,
        "submission_count": row.submission_count,
        "created_by": str(row.created_by),
        "is_drafted": row.status == CompetitionStatusEnum.DRAFT,
    }

    return CustomJSONResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Resource retrieved successfully",
        data=data,
    )
