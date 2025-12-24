from copy import deepcopy
from datetime import datetime
import math
from uuid import UUID
from fastapi import status
import pytz
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ...configs.s3_config import s3_client
from ...configs.env_config import env_config
from ..discussion.search_services import format_tsquery
from ...schemas.default_schemas import AuthorizationData
from ...database.challenge.enums import CompetitionStatusEnum, PrizeTypeEnum
from ...schemas.challenge.submission_requests import SortOrder
from ...services.challenge.submission_services import get_s3_file_metadata
from ...schemas.custom_responses import CustomBackendError, CustomJSONResponse
from ...schemas.challenge.admin_responses import (
    AdminRetrieveChanllengeByIDSchema,
    AdminRetrieveCompetitionSubmissionCompetitionSchema,
    AdminRetrieveCompetitionSubmissionSchema,
    AdminRetrieveCompetitionsSchema,
)
from ...schemas.challenge.admin_requests import (
    AdminCreateCompetitionParams,
    AdminEvaluateSubmissionParams,
    AdminRetreiveCompetitionsSortBy,
    AdminRetrieveCompetitionSubmissionsParams,
    AdminRetrieveCompetitionSubmissionsSortByEnum,
    AdminRetrieveCompetitionsParams,
    AdminUpdateCompetitionParams,
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
    Retrieves a single challenge by ID with full details.

    Args:
        competition_id(UUID): The ID of the challenge to retrieve.
        authorized_user(AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session(AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: Challenge details or 404 if not found.
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
        serialized_challenge = AdminRetrieveChanllengeByIDSchema.model_validate(
            chanllenge
        ).model_dump(exclude={"participant_count", "submission_count"})

        serialized_challenge["participant_count"] = len(chanllenge.participants)
        serialized_challenge["submission_count"] = len(chanllenge.submissions)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Admin challenge retrieved successfully",
            data=serialized_challenge,
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Admin challenge retrieval failed",
            details="An error occurred while retrieving the admin challenge. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def admin_create_competition_handler(
    req_params: AdminCreateCompetitionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Creates a new competition (challenge) from the admin panel.

    Args:
        req_params: Competition creation payload (title, description, timeline, etc.).
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse with created competition details.
    """
    logger.info(f"{authorized_user['email']} - Execution started")
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        # Check existing title
        existing_competition = await db_session.execute(
            select(Competition).where(Competition.title == req_params.title)
        )
        existing_competition = existing_competition.scalars().first()

        if existing_competition:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_409_CONFLICT,
                message="Competition already exists",
                error={
                    "code": "CONFLICT",
                    "details": "Chanllenge with the same title already exists. Please use a different title.",
                },
            )

        # Create new competition
        if req_params.draft:
            competition_status = CompetitionStatusEnum.DRAFT
        elif req_params.publish_schedule:
            competition_status = CompetitionStatusEnum.SCHEDULED
        else:
            competition_status = CompetitionStatusEnum.PUBLISHED

        new_competition = Competition(
            title=req_params.title,
            subtitle=req_params.subtitle,
            overview=req_params.overview,
            detailed_description=req_params.description,
            status=competition_status,
            created_by=authorized_user["user_id"],
            published_at=(
                current_timestamp
                if competition_status == CompetitionStatusEnum.PUBLISHED
                else None
            ),
            scheduled_publish_at=(
                req_params.publish_schedule
                if competition_status == CompetitionStatusEnum.SCHEDULED
                else None
            ),
            constraints=req_params.constraints,
            other_resources=req_params.other_resources,
        )

        db_session.add(new_competition)
        await db_session.flush()

        # Competition image file
        if req_params.image_url:
            file_name = req_params.image_url.split("/")[-1]
            permanent_s3_key = f"public/{authorized_user['user_id']}/{new_competition.id}/image/{file_name}"

            try:
                s3_client.copy_object(
                    Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                    CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{req_params.image_url}",
                    Key=permanent_s3_key,
                )
            except Exception as s3_exc:
                logger.exception(
                    f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                )
                await db_session.rollback()
                return CustomBackendError(
                    message="Chanllenge creation failed",
                    details="An error occurred while creating the challenge. Please contact developers if the issue persists.",
                )

            new_competition.image_url = f"https://{env_config.CHALLENGE_AWS_S3_BUCKET}.s3.amazonaws.com/{permanent_s3_key}"

        # Competition rules and guidelines file
        if req_params.rules_and_guidelines:
            file_name = req_params.rules_and_guidelines.split("/")[-1]
            permanent_s3_key = f"public/{authorized_user['user_id']}/{new_competition.id}/rules_and_guidelines/{file_name}"
            metadata = get_s3_file_metadata(req_params.rules_and_guidelines)

            if "error" in metadata:
                await db_session.rollback()

                logger.error(
                    f"{authorized_user['email']} - Error fetching metadata for {req_params.rules_and_guidelines}: {metadata['error']}"
                )
                return CustomBackendError(
                    message="Chanllenge creation failed",
                    details="An error occurred while creating the challenge. Please contact developers if the issue persists.",
                )

            try:
                s3_client.copy_object(
                    Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                    CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{req_params.rules_and_guidelines}",
                    Key=permanent_s3_key,
                )
            except Exception as s3_exc:
                logger.exception(
                    f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                )
                await db_session.rollback()
                return CustomBackendError(
                    message="Chanllenge creation failed",
                    details="An error occurred while creating the challenge. Please contact developers if the issue persists.",
                )

            new_competition.rules_and_guidelines = {
                "file_name": file_name,
                "metadata": metadata,
                "s3_key": permanent_s3_key,
                "uploaded_at": current_timestamp.strftime("%Y-%m-%d %H:%M:%S +0530"),
            }

        # Competition evaluation
        new_competition_evaluation = CompetitionEvaluation(
            competition_id=new_competition.id,
            evaluation_criteria=req_params.evaluation_criteria_definition,
            submission_criteria=req_params.submission_file_definition,
        )

        db_session.add(new_competition_evaluation)

        # Competition prize pool
        new_competition_prize_pool = CompetitionPrizePool(
            competition_id=new_competition.id,
            prize_type=req_params.prize_type,
            total_pool_amount=req_params.total_pool_amount,
            currency=req_params.currency,
            prize_description=req_params.prize_pool_description,
        )

        db_session.add(new_competition_prize_pool)

        # Competition timelines
        new_competition_timeline = CompetitionTimeline(
            competition_id=new_competition.id,
            submission_starts_at=req_params.submission_starts_at,
            submission_ends_at=req_params.submission_ends_at,
            evaluation_ends_at=req_params.evaluation_ends_at,
        )

        db_session.add(new_competition_timeline)

        # Competition datasets
        if req_params.data_models:
            for data_model in req_params.data_models:
                data_model["id"] = str(data_model["id"])

        if req_params.ai_models:
            for ai_model in req_params.ai_models:
                ai_model["id"] = str(ai_model["id"])

        new_competition_datasets = CompetitionDataset(
            competition_id=new_competition.id,
            description=req_params.dataset_description,
            datasets=req_params.data_models,
            ai_models=req_params.ai_models,
        )

        db_session.add(new_competition_datasets)
        await db_session.flush()

        # Additional assets
        additional_assets = {}
        for asset in req_params.additional_assets or []:
            file_name = asset["object_key"].split("/")[-1]
            metadata = get_s3_file_metadata(asset["object_key"])

            if "error" in metadata:
                await db_session.rollback()

                logger.error(
                    f"{authorized_user['email']} - Error fetching metadata for {asset["object_key"]}: {metadata['error']}"
                )
                return CustomBackendError(
                    message="Chanllenge creation failed",
                    details="An error occurred while creating the challenge. Please contact developers if the issue persists.",
                )
            permanent_s3_key = f"private/{authorized_user['user_id']}/{new_competition.id}/additional_assets/{file_name}"

            try:
                s3_client.copy_object(
                    Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                    CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{asset['object_key']}",
                    Key=permanent_s3_key,
                )
            except Exception as s3_exc:
                logger.exception(
                    f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                )
                await db_session.rollback()
                return CustomBackendError(
                    message="Chanllenge creation failed",
                    details="An error occurred while creating the challenge. Please contact developers if the issue persists.",
                )

            additional_assets[file_name] = {
                "metadata": metadata,
                "s3_key": permanent_s3_key,
                "description": asset["description"],
                "uploaded_at": current_timestamp.strftime("%Y-%m-%d %H:%M:%S +0530"),
            }

        new_competition_datasets.additional_assets = additional_assets

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Chanllenge created successfully",
            data={
                "competition_id": new_competition.id,
                "status": new_competition.status.value,
            },
        )

    except Exception as e:
        await db_session.rollback()

        logger.error(f"{authorized_user['email']} - Error: {e}")
        return CustomBackendError(
            message="Competition creation failed",
            details="An error occurred while creating the competition. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def admin_update_competition_handler(
    req_params: AdminUpdateCompetitionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Updates an existing challenge (competition) from the admin panel.

    Args:
        req_params: Competition update payload (title, description, timeline, etc.).
        authorized_user: Authenticated admin user.
        db_session: Active DB session.

    Returns:
        CustomJSONResponse with updated competition details.
    """
    logger.info(f"{authorized_user['email']} - Execution started")
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        competition_stmt = select(Competition).where(
            Competition.id == req_params.competition_id
        )
        competition_stmt = competition_stmt.options(
            selectinload(Competition.evaluations),
            selectinload(Competition.prize_pools),
            selectinload(Competition.timelines),
            selectinload(Competition.datasets),
        )
        competition = await db_session.execute(competition_stmt)
        competition = competition.scalars().one_or_none()

        if not competition:
            logger.error(
                f"{authorized_user['email']} - Competition not found (id={req_params.competition_id})"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Competition not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Competition does not exist for the provided id. Please check the id and try again.",
                },
            )

        if competition.status not in [
            CompetitionStatusEnum.DRAFT,
            CompetitionStatusEnum.SCHEDULED,
        ]:
            logger.error(
                f"{authorized_user['email']} - Invalid competition status: {competition.status}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid competition status",
                error={
                    "code": "BAD_REQUEST",
                    "details": "Competition is not in draft or scheduled status. Please check the status and try again.",
                },
            )

        required_fields_map = {
            "title": bool(competition.title),
            "subtitle": bool(competition.subtitle),
            "overview": bool(competition.overview),
            "description": bool(competition.detailed_description),
            "constraints": bool(competition.constraints),
            "evaluation_criteria_definition": bool(
                competition.evaluations.evaluation_criteria
            ),
            "submission_file_definition": bool(
                competition.evaluations.submission_criteria
            ),
            "prize_pool_description": bool(competition.prize_pools.prize_description),
            "submission_starts_at": bool(competition.timelines.submission_starts_at),
            "submission_ends_at": bool(competition.timelines.submission_ends_at),
            "evaluation_ends_at": bool(competition.timelines.evaluation_ends_at),
            "rules_and_guidelines": bool(competition.rules_and_guidelines),
            "dataset_description": bool(competition.datasets.description),
        }

        # Update the competition
        if req_params.title and req_params.title != competition.title:
            competition.title = req_params.title
            required_fields_map["title"] = True

        if req_params.subtitle and req_params.subtitle != competition.subtitle:
            competition.subtitle = req_params.subtitle
            required_fields_map["subtitle"] = True

        if req_params.overview and req_params.overview != competition.overview:
            competition.overview = req_params.overview
            required_fields_map["overview"] = True

        if (
            req_params.description
            and req_params.description != competition.detailed_description
        ):
            competition.detailed_description = req_params.description
            required_fields_map["description"] = True

        if req_params.image_url:
            file_name = req_params.image_url.split("/")[-1]
            permanent_s3_key = f"public/{authorized_user['user_id']}/{competition.id}/image/{file_name}"

            try:
                s3_client.copy_object(
                    Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                    CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{req_params.image_url}",
                    Key=permanent_s3_key,
                )
            except Exception as s3_exc:
                logger.exception(
                    f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                )
                await db_session.rollback()
                return CustomBackendError(
                    message="Competition update failed",
                    details="An error occurred while updating the competition. Please contact developers if the issue persists.",
                )

            competition.image_url = f"https://{env_config.CHALLENGE_AWS_S3_BUCKET}.s3.amazonaws.com/{permanent_s3_key}"

        if req_params.constraints and req_params.constraints != competition.constraints:
            competition.constraints = req_params.constraints
            required_fields_map["constraints"] = True

        if (
            req_params.evaluation_criteria_definition
            and req_params.evaluation_criteria_definition
            != competition.evaluations.evaluation_criteria
        ):
            competition.evaluations.evaluation_criteria = (
                req_params.evaluation_criteria_definition
            )
            required_fields_map["evaluation_criteria_definition"] = True

        if (
            req_params.submission_file_definition
            and req_params.submission_file_definition
            != competition.evaluations.submission_criteria
        ):
            competition.evaluations.submission_criteria = (
                req_params.submission_file_definition
            )
            required_fields_map["submission_file_definition"] = True

        if (
            req_params.other_resources
            and req_params.other_resources != competition.other_resources
        ):
            competition.other_resources = req_params.other_resources

        if (
            req_params.prize_type
            and req_params.prize_type != competition.prize_pools.prize_type
        ):
            competition.prize_pools.prize_type = req_params.prize_type

        if (
            req_params.total_pool_amount
            and req_params.total_pool_amount
            != competition.prize_pools.total_pool_amount
        ):
            competition.prize_pools.total_pool_amount = req_params.total_pool_amount

        if (
            req_params.currency
            and req_params.currency != competition.prize_pools.currency
        ):
            competition.prize_pools.currency = req_params.currency

        if (
            req_params.prize_pool_description
            and req_params.prize_pool_description
            != competition.prize_pools.prize_description
        ):
            competition.prize_pools.prize_description = (
                req_params.prize_pool_description
            )
            required_fields_map["prize_pool_description"] = True

        if (
            req_params.submission_starts_at
            and req_params.submission_starts_at
            != competition.timelines.submission_starts_at
        ):
            competition.timelines.submission_starts_at = req_params.submission_starts_at
            required_fields_map["submission_starts_at"] = True

        if (
            req_params.submission_ends_at
            and req_params.submission_ends_at
            != competition.timelines.submission_ends_at
        ):
            competition.timelines.submission_ends_at = req_params.submission_ends_at
            required_fields_map["submission_ends_at"] = True

        if (
            req_params.evaluation_ends_at
            and req_params.evaluation_ends_at
            != competition.timelines.evaluation_ends_at
        ):
            competition.timelines.evaluation_ends_at = req_params.evaluation_ends_at
            required_fields_map["evaluation_ends_at"] = True

        if req_params.rules_and_guidelines:
            file_name = req_params.rules_and_guidelines.split("/")[-1]
            permanent_s3_key = f"public/{authorized_user['user_id']}/{competition.id}/rules_and_guidelines/{file_name}"
            metadata = get_s3_file_metadata(req_params.rules_and_guidelines)

            if "error" in metadata:
                await db_session.rollback()

                logger.error(
                    f"{authorized_user['email']} - Error fetching metadata for {req_params.rules_and_guidelines}: {metadata['error']}"
                )
                return CustomBackendError(
                    message="Chanllenge creation failed",
                    details="An error occurred while creating the challenge. Please contact developers if the issue persists.",
                )

            try:
                s3_client.copy_object(
                    Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                    CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{req_params.rules_and_guidelines}",
                    Key=permanent_s3_key,
                )
            except Exception as s3_exc:
                logger.exception(
                    f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                )
                await db_session.rollback()
                return CustomBackendError(
                    message="Competition update failed",
                    details="An error occurred while updating the competition. Please contact developers if the issue persists.",
                )

            competition.rules_and_guidelines = {
                "file_name": file_name,
                "metadata": metadata,
                "s3_key": permanent_s3_key,
                "uploaded_at": current_timestamp.strftime("%Y-%m-%d %H:%M:%S +0530"),
            }
            required_fields_map["rules_and_guidelines"] = True

        if (
            req_params.dataset_description
            and req_params.dataset_description != competition.datasets.description
        ):
            competition.datasets.description = req_params.dataset_description
            required_fields_map["dataset_description"] = True

        if req_params.data_models:
            if req_params.data_models.remove:
                new_models = []
                for models in competition.datasets.datasets:
                    if models["id"] not in req_params.data_models.remove:
                        new_models.append(models)

                competition.datasets.datasets = new_models

            if req_params.data_models.add:
                if not competition.datasets.datasets:
                    competition.datasets.datasets = []

                competition.datasets.datasets.extend(req_params.data_models.add)
                required_fields_map["data_models"] = True

        if req_params.ai_models:
            if req_params.ai_models.remove:
                new_models = []
                for models in competition.datasets.ai_models:
                    if models["id"] not in req_params.ai_models.remove:
                        new_models.append(models)

                competition.datasets.ai_models = new_models

            if req_params.ai_models.add:
                if not competition.datasets.ai_models:
                    competition.datasets.ai_models = []

                competition.datasets.ai_models.extend(req_params.ai_models.add)
                required_fields_map["ai_models"] = True

        if req_params.additional_assets:
            if req_params.additional_assets.updated_descriptions and competition.datasets.additional_assets:
                updated_assets = deepcopy(competition.datasets.additional_assets)

                for key, value in req_params.additional_assets.updated_descriptions.items():
                    updated_assets[key]["description"] = value
                
                competition.datasets.additional_assets = updated_assets

            if (
                req_params.additional_assets.remove
                and competition.datasets.additional_assets
            ):
                new_assets = {}
                for key, value in competition.datasets.additional_assets.items():
                    if value["s3_key"] in req_params.additional_assets.remove:
                        s3_client.delete_object(
                            Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                            Key=value["s3_key"],
                        )
                    else:
                        new_assets[key] = value

                competition.datasets.additional_assets = (
                    None if not new_assets else new_assets
                )

            if req_params.additional_assets.add:
                new_assets = deepcopy(competition.datasets.additional_assets) or {}

                for asset in req_params.additional_assets.add:
                    file_name = asset["object_key"].split("/")[-1]
                    metadata = get_s3_file_metadata(asset["object_key"])

                    if "error" in metadata:
                        await db_session.rollback()

                        logger.error(
                            f"{authorized_user['email']} - Error fetching metadata for {asset["object_key"]}: {metadata['error']}"
                        )
                        return CustomBackendError(
                            message="Competition update failed",
                            details="An error occurred while updating the discussion. Please contact developers if the issue persists.",
                        )
                    permanent_s3_key = f"private/{authorized_user['user_id']}/{competition.id}/additional_assets/{file_name}"

                    try:
                        s3_client.copy_object(
                            Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                            CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{asset['object_key']}",
                            Key=permanent_s3_key,
                        )
                    except Exception as s3_exc:
                        logger.exception(
                            f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                        )
                        await db_session.rollback()
                        return CustomBackendError(
                            message="Discussion creation failed",
                            details="An error occurred while creating the competition. Please contact developers if the issue persists.",
                        )

                    new_assets[file_name] = {
                        "metadata": metadata,
                        "s3_key": permanent_s3_key,
                        "description": asset["description"],
                        "uploaded_at": current_timestamp.strftime(
                            "%Y-%m-%d %H:%M:%S +0530"
                        ),
                    }

                competition.datasets.additional_assets = new_assets

        if not req_params.draft:
            if not all(required_fields_map.values()):
                missing_fields = [
                    field for field, value in required_fields_map.items() if not value
                ]
                await db_session.rollback()
                logger.error(
                    f"{authorized_user['email']} - Missing required fields: {", ".join(missing_fields)}"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Missing required fields",
                    error={
                        "code": "BAD_REQUEST",
                        "details": f"Missing required fields: {", ".join(missing_fields)}",
                    },
                )

            if competition.prize_pools.prize_type == PrizeTypeEnum.CASH:
                if (
                    not competition.prize_pools.currency
                    or not competition.prize_pools.total_pool_amount
                ):
                    missing_fields = []
                    if not competition.prize_pools.currency:
                        missing_fields.append("currency")
                    if not competition.prize_pools.total_pool_amount:
                        missing_fields.append("total_pool_amount")

                    await db_session.rollback()
                    logger.error(
                        f"{authorized_user['email']} - Missing required fields: {", ".join(missing_fields)}"
                    )

                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Missing required fields",
                        error={
                            "code": "BAD_REQUEST",
                            "details": f"Missing required fields: {', '.join(missing_fields)}",
                        },
                    )

            if not competition.datasets.datasets and not competition.datasets.ai_models:
                await db_session.rollback()
                logger.error(
                    f"{authorized_user['email']} - Missing required fields: datasets"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Missing required fields",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "Missing required fields: data_models/ai_models",
                    },
                )

            if req_params.publish_schedule:
                competition.scheduled_publish_at = req_params.publish_schedule
                competition.status = CompetitionStatusEnum.SCHEDULED

            else:
                competition.published_at = current_timestamp
                competition.status = CompetitionStatusEnum.PUBLISHED

        competition.updated_at = current_timestamp

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Competition updated successfully",
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {e}")
        return CustomBackendError(
            message="Competition update failed",
            details="An error occurred while updating the competition. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def admin_evaluate_submission_handler(
    req_params: AdminEvaluateSubmissionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Evaluates a specific submission for a given competition.

    Args:
        req_params (AdminDisqualifySubmissionParams): The request body containing the submission ID and disqualification reason.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response indicating the disqualification result.
    """
    logger.info(
        f"{authorized_user['email']} - Admin Disqualify Submission handler started"
    )
    current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        submission_stmt = select(CompetitionSubmission).where(
            CompetitionSubmission.id == req_params.submission_id
        )
        submission_stmt = submission_stmt.options(
            selectinload(CompetitionSubmission.competition)
        )
        submission = await db_session.execute(submission_stmt)
        submission = submission.scalars().one_or_none()

        if not submission:
            logger.error(
                f"{authorized_user['email']} - Submission not found (id={req_params.submission_id})"
            )
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Submission not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Submission does not exist for the provided id. Please check the id and try again.",
                },
            )

        if submission.competition.status == CompetitionStatusEnum.CANCELLED:
            logger.error(
                f"{authorized_user['email']} - Competition is cancelled for submission (id={req_params.submission_id})"
            )
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Competition is cancelled",
                error={
                    "code": "BAD_REQUEST",
                    "details": "Competition is cancelled for this submission. Please contact developers if the issue persists.",
                },
            )

        if req_params.comments:
            submission.evaluation_comment = req_params.comments

        if req_params.disqualify:
            submission.is_disqualified = True
            submission.score = None

            if submission.evaluation_attachments:
                for attachment in submission.evaluation_attachments.values():
                    s3_client.delete_object(
                        Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                        Key=attachment["s3_key"],
                    )

                submission.evaluation_attachments = None

        else:
            submission.is_disqualified = False

            if req_params.score:
                submission.score = req_params.score

            if req_params.attachments:
                if req_params.attachments.remove:
                    new_attachments = deepcopy(submission.attachments) or {}

                    if not submission.evaluation_attachments:
                        submission.evaluation_attachments = {}

                    for key, value in submission.evaluation_attachments.items():
                        if value["s3_key"] in req_params.attachments.remove:
                            s3_client.delete_object(
                                Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                                Key=value["s3_key"],
                            )
                        else:
                            new_attachments[key] = value

                    submission.evaluation_attachments = (
                        new_attachments if new_attachments else None
                    )

                if req_params.attachments.add:
                    new_attachments = deepcopy(submission.evaluation_attachments) or {}

                    for source_s3_key in req_params.attachments.add:
                        file_name = source_s3_key.split("/")[-1]
                        metadata = get_s3_file_metadata(source_s3_key)

                        if "error" in metadata:
                            await db_session.rollback()

                            logger.error(
                                f"{authorized_user['email']} - Error fetching metadata for {source_s3_key}: {metadata['error']}"
                            )
                            return CustomBackendError(
                                message="Discussion creation failed",
                                details="An error occurred while creating the discussion. Please contact developers if the issue persists.",
                            )

                        # build permanent key and copy object to permanent location
                        permanent_s3_key = f"private/{authorized_user['user_id']}/{submission.competition_id}/{submission.id}/evaluation_attachments/{file_name}"

                        try:
                            s3_client.copy_object(
                                Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                                CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{source_s3_key}",
                                Key=permanent_s3_key,
                            )
                        except Exception as s3_exc:
                            await db_session.rollback()

                            logger.exception(
                                f"{authorized_user['email']} - S3 copy failed: {str(s3_exc)}"
                            )
                            return CustomBackendError(
                                message="Submission creation failed",
                                details="An error occurred while creating the submission. Please contact developers if the issue persists.",
                            )

                        new_attachments[file_name] = {
                            "metadata": metadata,
                            "s3_key": permanent_s3_key,
                            "uploaded_at": current_timestamp.strftime(
                                "%Y-%m-%d %H:%M:%S +0530"
                            ),
                        }

                    submission.evaluation_attachments = new_attachments

        submission.updated_at = current_timestamp

        if submission.is_disqualified:
            if not submission.evaluation_comment:
                logger.error(
                    f"{authorized_user['email']} - Evaluation comment not provided (id={req_params.submission_id})"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Evaluation comment not provided",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "Evaluation comment is required for disqualified submission. Please provide a comment and try again.",
                    },
                )

        else:
            if not submission.evaluation_comment:
                logger.error(
                    f"{authorized_user['email']} - Evaluation comment not provided (id={req_params.submission_id})"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Evaluation comment not provided",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "Evaluation comment is required for qualified submission. Please provide a comment and try again.",
                    },
                )

            if submission.score == None:
                logger.error(
                    f"{authorized_user['email']} - Score not provided (id={req_params.submission_id})"
                )
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Score not provided",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "Score is required for qualified submission. Please provide a score and try again.",
                    },
                )

        await db_session.commit()

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submission evaluated successfully",
        )

    except Exception as e:
        await db_session.rollback()

        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Admin evaluate submission failed",
            details="An error occurred while evaluating the submission. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
