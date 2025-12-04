import math
import pytz
from uuid import UUID
from fastapi import status
from typing import Any, List
from sqlalchemy import func, select
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ...configs.s3_config import s3_client
from ...configs.env_config import env_config
from ...services.discussion.search_services import format_tsquery
from ...schemas.default_schemas import AuthorizationData, UserRole
from ...schemas.challenge.submission_responses import UserSubmissionsSchema
from ...schemas.custom_responses import CustomBackendError, CustomJSONResponse
from ...schemas.challenge.submission_requests import (
    CreateSubmissionRequest,
    DownloadSubmissionParams,
    DownloadSubmissionType,
    PublishSubmissionParams,
    RetrieveUserSubmissionsChoice,
    RetrieveUserSubmissionsParams,
    RetrieveUserSubmissionsSortByEnum,
    SortOrder,
    UpdateSubmissionParams,
    AdminEditSubmissionParams,
)
from ...database.challenge.models import (
    Competition,
    CompetitionTimeline,
    CompetitionParticipant,
    CompetitionSubmission,
    CompetitionPrizePool,
    User,
)
from ...database.challenge.enums import CompetitionStatusEnum


async def retrieve_user_submissions_handler(
    req_params: RetrieveUserSubmissionsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Retrieves submissions for a user across competitions based on their choice.

    Args:
        req_params (RetrieveUserSubmissionsParams): The request body containing the choice and sorting parameters.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the retrieved submission interests and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        # -----------------------
        # Base selectable
        # -----------------------
        stmt = select(CompetitionSubmission).where(
            CompetitionSubmission.user_id == authorized_user["user_id"]
        )
        stmt = stmt.join(
            Competition, Competition.id == CompetitionSubmission.competition_id
        )
        stmt = stmt.join(
            CompetitionTimeline,
            CompetitionTimeline.competition_id == Competition.id,
            isouter=True,
        )

        # -----------------------
        # Apply choice filters
        # -----------------------
        if req_params.choice != RetrieveUserSubmissionsChoice.SUBMITTED:
            if req_params.choice == RetrieveUserSubmissionsChoice.EVALUATION:
                stmt = stmt.where(
                    Competition.status == CompetitionStatusEnum.EVALUATION
                )

            elif req_params.choice == RetrieveUserSubmissionsChoice.COMPLETED:
                stmt = stmt.where(Competition.status == CompetitionStatusEnum.COMPLETED)

        # -----------------------
        # Search Query
        # -----------------------
        if req_params.query:
            formatted_query = format_tsquery(req_params.query)
            ts_query = func.to_tsquery("english", formatted_query)

            stmt = stmt.where(
                (Competition.title_vector.op("@@")(ts_query))
                | (CompetitionSubmission.title_vector.op("@@")(ts_query))
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
        if req_params.sort_by == RetrieveUserSubmissionsSortByEnum.COMPETITION_TITLE:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(Competition.title.asc())
            else:
                stmt = stmt.order_by(Competition.title.desc())

        elif req_params.sort_by == RetrieveUserSubmissionsSortByEnum.TITLE:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.title.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.title.desc())

        elif req_params.sort_by == RetrieveUserSubmissionsSortByEnum.DESCRIPTION:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.description.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.description.desc())

        elif req_params.sort_by == RetrieveUserSubmissionsSortByEnum.CREATED_AT:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.created_at.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.created_at.desc())

        elif req_params.sort_by == RetrieveUserSubmissionsSortByEnum.UPDATED_AT:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionSubmission.updated_at.asc())
            else:
                stmt = stmt.order_by(CompetitionSubmission.updated_at.desc())

        elif req_params.sort_by == RetrieveUserSubmissionsSortByEnum.EVALUATION_ENDS_AT:
            if req_params.sort_order == SortOrder.ASC:
                stmt = stmt.order_by(CompetitionTimeline.evaluation_ends_at.asc())
            else:
                stmt = stmt.order_by(CompetitionTimeline.evaluation_ends_at.desc())

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
            selectinload(CompetitionSubmission.competition).selectinload(
                CompetitionSubmission.competition.property.mapper.class_.timelines
            ),
        )
        result = await db_session.execute(stmt)
        submissions = result.scalars().unique().all()

        # -----------------------
        # Serialize
        # -----------------------
        serialized_submissions = [
            UserSubmissionsSchema.model_validate(submission).model_dump()
            for submission in submissions
        ]

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Discussions retrieved successfully",
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
            message="User submissions retrieval failed",
            details="An error occurred while retrieving the submissions. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def _get_submission_window(db_session: AsyncSession, competition_id: UUID):
    stmt = (
        select(
            Competition.status,
            CompetitionTimeline.submission_starts_at,
            CompetitionTimeline.submission_ends_at,
        )
        .join(
            CompetitionTimeline,
            CompetitionTimeline.competition_id == Competition.id,
            isouter=True,
        )
        .where(Competition.id == competition_id)
    )
    result = await db_session.execute(stmt)
    return result.first()


async def create_user_submission_handler(
    competition_id: UUID,
    payload: CreateSubmissionRequest,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        user_id = authorized_user.get("user_id")

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

        # Fetch competition submission window
        submission_window = await _get_submission_window(
            db_session=db_session, competition_id=competition_id
        )

        if not submission_window:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Competition not found.",
                },
            )

        competition_status, submission_starts_at, submission_ends_at = submission_window

        if competition_status != CompetitionStatusEnum.PUBLISHED:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "SUBMISSION_NOT_ALLOWED",
                    "details": "Submissions can be created only for published competitions.",
                },
            )

        if submission_starts_at is None or submission_ends_at is None:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "SUBMISSION_WINDOW_NOT_CONFIGURED",
                    "details": "Submission window is not configured for this competition.",
                },
            )

        now = datetime.now(timezone.utc)
        if submission_starts_at.tzinfo is None:
            submission_starts_at = submission_starts_at.replace(tzinfo=timezone.utc)
        if submission_ends_at.tzinfo is None:
            submission_ends_at = submission_ends_at.replace(tzinfo=timezone.utc)

        if now < submission_starts_at:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "SUBMISSIONS_NOT_STARTED",
                    "details": "Submission window has not started yet.",
                },
            )

        if now > submission_ends_at:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "SUBMISSIONS_CLOSED",
                    "details": "Submission window has already ended.",
                },
            )

        # Ensure the user has joined the competition
        participant_stmt = select(CompetitionParticipant.id).where(
            CompetitionParticipant.competition_id == competition_id,
            CompetitionParticipant.user_id == user_id,
        )
        participant_result = await db_session.execute(participant_stmt)
        participant = participant_result.scalar_one_or_none()

        if not participant:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "NOT_A_PARTICIPANT",
                    "details": "You must join the competition before submitting.",
                },
            )

        # Determine next submission count for the user
        submission_count_stmt = select(func.count()).where(
            CompetitionSubmission.competition_id == competition_id,
            CompetitionSubmission.user_id == user_id,
        )
        submission_count = (
            await db_session.execute(submission_count_stmt)
        ).scalar_one()
        next_count = submission_count + 1

        submission = CompetitionSubmission(
            competition_id=competition_id,
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            submission_count=next_count,
        )

        db_session.add(submission)
        await db_session.flush()

        if payload.attachments:
            attachment_objs: List[dict[str, Any]] = []

            for source_s3_key in payload.attachments:
                file_name = source_s3_key.split("/")[-1]
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
                permanent_s3_key = f"private/{authorized_user['user_id']}/{submission.competition_id}/{submission.id}/attachments/{file_name}"

                try:
                    s3_client.copy_object(
                        Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                        CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{source_s3_key}",
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
                    }
                )

            if attachment_objs:
                submission.attachments = attachment_objs

        await db_session.commit()
        await db_session.refresh(submission)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Submission created successfully",
            data={
                "submission_id": str(submission.id),
                "competition_id": str(competition_id),
                "user_id": str(user_id),
                "title": submission.title,
                "description": submission.description,
                "attachments": submission.attachments,
                "submission_count": submission.submission_count,
                "is_disqualified": submission.is_disqualified,
                "score": submission.score,
                "evaluation_comment": submission.evaluation_comment,
                "created_at": submission.created_at.isoformat(),
                "updated_at": submission.updated_at.isoformat(),
            },
        )
    except Exception as exc:
        logger.error("Failed to create submission", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(
            message="Failed to create submission",
            details=str(exc),
        )


async def get_user_submissions_handler(
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
    page: int = 1,
    limit: int = 10,
    competition_id: UUID | None = None,
) -> CustomJSONResponse:
    try:
        user_id = authorized_user.get("user_id")
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

        base_filters = [
            CompetitionSubmission.user_id == user_id,
        ]
        if competition_id:
            base_filters.append(CompetitionSubmission.competition_id == competition_id)

        count_stmt = (
            select(func.count()).select_from(CompetitionSubmission).where(*base_filters)
        )
        total_submissions = (await db_session.execute(count_stmt)).scalar_one()

        total_pages = (
            (total_submissions + limit - 1) // limit if total_submissions > 0 else 0
        )
        offset = (page - 1) * limit

        submissions_stmt = (
            select(
                CompetitionSubmission,
                Competition.title.label("competition_title"),
                Competition.status.label("competition_status"),
                # Prizepool
                CompetitionPrizePool.prize_type,
                CompetitionPrizePool.total_pool_amount,
                CompetitionPrizePool.currency,
                CompetitionPrizePool.prize_description,
                # Timeline
                CompetitionTimeline.submission_starts_at,
                CompetitionTimeline.submission_ends_at,
            )
            .join(Competition, Competition.id == CompetitionSubmission.competition_id)
            .join(
                CompetitionPrizePool,
                CompetitionPrizePool.competition_id == Competition.id,
                isouter=True,
            )
            .join(
                CompetitionTimeline,
                CompetitionTimeline.competition_id == Competition.id,
                isouter=True,
            )
            .where(*base_filters)
            .order_by(CompetitionSubmission.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        submissions_result = await db_session.execute(submissions_stmt)
        rows = submissions_result.all()

        submissions = []
        for (
            submission,
            competition_title,
            competition_status,
            prize_type,
            total_pool_amount,
            currency,
            prize_description,
            submission_starts_at,
            submission_ends_at,
        ) in rows:
            submissions.append(
                {
                    "submission_id": str(submission.id),
                    "competition_id": str(submission.competition_id),
                    "user_id": str(submission.user_id),
                    "competition_title": competition_title,
                    "title": submission.title,
                    "description": submission.description,
                    "attachments": submission.attachments,
                    "submission_count": submission.submission_count,
                    "is_disqualified": (
                        submission.is_disqualified
                        if competition_status == CompetitionStatusEnum.COMPLETED
                        else False
                    ),
                    "score": (
                        submission.score
                        if competition_status == CompetitionStatusEnum.COMPLETED
                        else None
                    ),
                    "evaluation_comment": (
                        submission.evaluation_comment
                        if competition_status == CompetitionStatusEnum.COMPLETED
                        else None
                    ),
                    "prize_pool": {
                        "prize_type": prize_type.value if prize_type else None,
                        "total_pool_amount": total_pool_amount,
                        "currency": currency,
                        "prize_description": prize_description,
                    },
                    "timeline": {
                        "submission_starts_at": (
                            submission_starts_at.isoformat()
                            if submission_starts_at
                            else None
                        ),
                        "submission_ends_at": (
                            submission_ends_at.isoformat()
                            if submission_ends_at
                            else None
                        ),
                    },
                    "created_at": submission.created_at.isoformat(),
                    "updated_at": submission.updated_at.isoformat(),
                }
            )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submissions retrieved successfully",
            data={"submissions": submissions},
            meta={
                "total_submissions": total_submissions,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
                "competition_id": str(competition_id) if competition_id else None,
            },
        )
    except Exception as exc:
        logger.error("Failed to retrieve submissions", exc_info=True)
        return CustomBackendError(
            message="Failed to retrieve submissions",
            details=str(exc),
        )


async def get_admin_competition_submissions_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
    page: int = 1,
    limit: int = 10,
) -> CustomJSONResponse:
    try:
        if authorized_user.get("user_role") != UserRole.COS_ADMIN:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "details": "You are not authorized to access this resource.",
                },
            )

        # Ensure competition exists
        competition_exists_stmt = select(Competition.id).where(
            Competition.id == competition_id
        )
        competition_exists = (
            await db_session.execute(competition_exists_stmt)
        ).scalar_one_or_none()

        if not competition_exists:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Competition not found.",
                },
            )

        count_stmt = (
            select(func.count())
            .select_from(CompetitionSubmission)
            .where(CompetitionSubmission.competition_id == competition_id)
        )
        total_submissions = (await db_session.execute(count_stmt)).scalar_one()

        total_pages = (
            (total_submissions + limit - 1) // limit if total_submissions > 0 else 0
        )
        offset = (page - 1) * limit

        submissions_stmt = (
            select(
                CompetitionSubmission,
                User.name.label("user_name"),
                User.email.label("user_email"),
            )
            .join(User, User.id == CompetitionSubmission.user_id)
            .where(CompetitionSubmission.competition_id == competition_id)
            .order_by(
                CompetitionSubmission.created_at.desc(),
                CompetitionSubmission.submission_count.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        submissions_result = await db_session.execute(submissions_stmt)
        rows = submissions_result.all()

        submissions = []
        for submission, user_name, user_email in rows:
            submissions.append(
                {
                    "submission_id": str(submission.id),
                    "competition_id": str(submission.competition_id),
                    "user_id": str(submission.user_id),
                    "user_name": user_name,
                    "user_email": user_email,
                    "title": submission.title,
                    "description": submission.description,
                    "attachments": submission.evaluation_attachments,
                    "submission_count": submission.submission_count,
                    "is_disqualified": submission.is_disqualified,
                    "score": submission.score,
                    "evaluation_comment": submission.evaluation_comment,
                    "created_at": submission.created_at.isoformat(),
                    "updated_at": submission.updated_at.isoformat(),
                }
            )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submissions retrieved successfully",
            data={"submissions": submissions},
            meta={
                "total_submissions": total_submissions,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
                "competition_id": str(competition_id),
            },
        )
    except Exception as exc:
        logger.error("Failed to retrieve competition submissions", exc_info=True)
        return CustomBackendError(
            message="Failed to retrieve competition submissions",
            details=str(exc),
        )


async def disqualify_submission_service(
    competition_id: str, submission_id: str, comments: str, db
):

    try:
        logger.info(
            f"Checking submission {submission_id} under competition {competition_id}"
        )

        query = select(CompetitionSubmission).where(
            CompetitionSubmission.id == submission_id,
            CompetitionSubmission.competition_id == competition_id,
        )

        result = await db.execute(query)
        submission = result.scalar_one_or_none()

        if not submission:
            logger.warning(
                "Submission does not belong to this competition or does not exist"
            )
            return None

        submission.is_disqualified = True
        submission.evaluation_comment = comments
        await db.commit()
        await db.refresh(submission)

        return {
            "submission_id": str(submission.id),
            "competition_id": str(submission.competition_id),
            "is_disqualified": submission.is_disqualified,
        }

    except Exception as e:
        logger.error(f"Error disqualifying submission: {e}")
        raise e


def get_s3_file_metadata(object_key: str) -> dict:
    try:
        response = s3_client.head_object(
            Bucket=env_config.CHALLENGE_AWS_S3_BUCKET, Key=object_key
        )

        metadata = {
            "content_type": response.get("ContentType"),
            "content_length_bytes": response.get("ContentLength"),
            "size_in_kb": round(response.get("ContentLength") / 1024, 2),
        }

        return metadata

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"error": str(e)}


async def publish_submission_service(
    req_params: PublishSubmissionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
):
    try:
        submission_stmt = select(CompetitionSubmission).where(
            CompetitionSubmission.id == req_params.submission_id
        )

        submission = (await db_session.execute(submission_stmt)).scalar_one_or_none()

        if not submission:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Submission not found.",
                },
            )

        submission.score = req_params.score
        submission.evaluation_comment = req_params.comments
        submission.updated_at = datetime.now(pytz.timezone("Asia/Kolkata"))

        if req_params.attachments:
            attachment_objs: List[dict[str, Any]] = []

            for source_s3_key in req_params.attachments:
                file_name = source_s3_key.split("/")[-1]
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
                permanent_s3_key = f"private/{authorized_user['user_id']}/{submission.competition_id}/{submission.id}/evaluation_attachments/{file_name}"

                try:
                    s3_client.copy_object(
                        Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                        CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{source_s3_key}",
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
                        "s3_key": permanent_s3_key,
                        "metadata": metadata,
                    }
                )

            if attachment_objs:
                submission.evaluation_attachments = attachment_objs

        await db_session.commit()
        await db_session.refresh(submission)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submission published successfully",
            data={"submission_id": str(submission.id)},
        )
    except Exception as exc:
        logger.error("Failed to publish submission", exc_info=True)
        return CustomBackendError(
            message="Failed to publish submission",
            details=str(exc),
        )


async def admin_edit_submission_evaluation_service(
    req_params: AdminEditSubmissionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        submission_stmt = select(CompetitionSubmission).where(
            CompetitionSubmission.id == req_params.submission_id
        )

        submission = (await db_session.execute(submission_stmt)).scalar_one_or_none()

        if not submission:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Submission not found.",
                },
            )

        # Update only provided fields
        if req_params.score is not None:
            submission.score = req_params.score

        if req_params.comments is not None:
            submission.evaluation_comment = req_params.comments

        if req_params.is_disqualified is not None:
            submission.is_disqualified = req_params.is_disqualified

        if req_params.comments or req_params.score:
            submission.is_disqualified = False

        if req_params.is_disqualified:
            submission.score = 0

        if req_params.attachments.remove:
            for source_s3_key in req_params.attachments.remove:
                if source_s3_key in [
                    a["s3_key"] for a in submission.evaluation_attachments
                ]:
                    permanent_s3_key = source_s3_key
                    try:
                        s3_client.delete_object(
                            Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                            Key=permanent_s3_key,
                        )
                    except Exception as s3_exc:
                        logger.exception(
                            f"{authorized_user['email']} - S3 delete failed: {str(s3_exc)}"
                        )
                        await db_session.rollback()
                        return CustomBackendError(
                            message="Submission update failed",
                            details="An error occurred while updating the submission. Please contact developers if the issue persists.",
                        )

                    submission.evaluation_attachments = [
                        a
                        for a in submission.evaluation_attachments
                        if a["s3_key"] != permanent_s3_key
                    ]

        if req_params.attachments.add:
            attachment_objs: List[dict[str, Any]] = []

            for source_s3_key in req_params.attachments.add:
                file_name = source_s3_key.split("/")[-1]
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
                permanent_s3_key = f"private/{authorized_user['user_id']}/{submission.competition_id}/{submission.id}/evaluation_attachments/{file_name}"

                try:
                    s3_client.copy_object(
                        Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                        CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{source_s3_key}",
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
                    }
                )

            if attachment_objs:
                if submission.evaluation_attachments:
                    submission.evaluation_attachments.extend(attachment_objs)
                else:
                    submission.evaluation_attachments = attachment_objs

        # If nothing was provided, it’s basically a no-op except timestamp
        submission.updated_at = datetime.now(pytz.timezone("Asia/Kolkata"))

        await db_session.commit()
        await db_session.refresh(submission)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submission evaluation updated successfully",
            data={
                "submission_id": str(submission.id),
            },
        )
    except Exception as exc:
        logger.error("Failed to update submission evaluation", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(
            message="Failed to update submission evaluation",
            details=str(exc),
        )


async def update_user_submission_handler(
    req_params: UpdateSubmissionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
):
    try:
        submission_stmt = select(CompetitionSubmission).where(
            CompetitionSubmission.id == req_params.submission_id
        )

        submission = (await db_session.execute(submission_stmt)).scalar_one_or_none()

        if not submission:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Submission not found.",
                },
            )

        if submission.user_id != authorized_user["user_id"]:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "details": "You are not authorized to access this resource.",
                },
            )

        if req_params.title != submission.title:
            submission.title = req_params.title
        if req_params.description != submission.description:
            submission.description = req_params.description

        if req_params.attachments.remove:
            for source_s3_key in req_params.attachments.remove:
                if source_s3_key in [a["s3_key"] for a in submission.attachments]:
                    permanent_s3_key = source_s3_key
                    try:
                        s3_client.delete_object(
                            Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                            Key=permanent_s3_key,
                        )
                    except Exception as s3_exc:
                        logger.exception(
                            f"{authorized_user['email']} - S3 delete failed: {str(s3_exc)}"
                        )
                        await db_session.rollback()
                        return CustomBackendError(
                            message="Submission update failed",
                            details="An error occurred while updating the submission. Please contact developers if the issue persists.",
                        )

                    submission.attachments = [
                        a
                        for a in submission.attachments
                        if a["s3_key"] != permanent_s3_key
                    ]

        if req_params.attachments.add:
            attachment_objs: List[dict[str, Any]] = []

            for source_s3_key in req_params.attachments.add:
                file_name = source_s3_key.split("/")[-1]
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
                permanent_s3_key = f"private/{authorized_user['user_id']}/{submission.competition_id}/{submission.id}/attachments/{file_name}"

                try:
                    s3_client.copy_object(
                        Bucket=env_config.CHALLENGE_AWS_S3_BUCKET,
                        CopySource=f"{env_config.CHALLENGE_AWS_S3_BUCKET}/{source_s3_key}",
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
                    }
                )

            if attachment_objs:
                attachment_objs.extend(submission.attachments)
                submission.attachments = attachment_objs

        submission.updated_at = datetime.now(pytz.timezone("Asia/Kolkata"))
        await db_session.commit()
        await db_session.refresh(submission)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submission updated successfully",
            data={"submission_id": str(submission.id)},
        )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return CustomBackendError(
            message="Failed to update submission",
            details=str(e),
        )


async def download_user_submission_handler(
    req_params: DownloadSubmissionParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        submission_stmt = select(CompetitionSubmission).where(
            CompetitionSubmission.id == req_params.submission_id
        )

        submission = (await db_session.execute(submission_stmt)).scalar_one_or_none()

        if not submission:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Resource not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Submission not found.",
                },
            )

        download_urls = []

        if req_params.type == DownloadSubmissionType.SUBMISSION:
            download_attachments = submission.attachments
        else:
            download_attachments = submission.evaluation_attachments

        for attachment in download_attachments:
            # Generate presigned download URL
            download_url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": env_config.CHALLENGE_AWS_S3_BUCKET,
                    "Key": attachment["s3_key"],
                },
                ExpiresIn=300,
            )

            download_urls.append(download_url)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Download URLs generated successfully",
            data={"download_urls": download_urls},
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return CustomBackendError(
            message="Failed to download submission",
            details=str(e),
        )


async def get_submission_interests_handler(
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        stmt = (
            select(
                Competition.id,
                Competition.title,
                CompetitionPrizePool.prize_type,
                CompetitionPrizePool.total_pool_amount,
                CompetitionPrizePool.currency,
                CompetitionTimeline.submission_starts_at,
                CompetitionTimeline.submission_ends_at,
            )
            .join(
                CompetitionPrizePool,
                CompetitionPrizePool.competition_id == Competition.id,
            )
            .join(
                CompetitionTimeline,
                CompetitionTimeline.competition_id == Competition.id,
            )
            .join(
                CompetitionParticipant,
                CompetitionParticipant.competition_id == Competition.id,
            )
            .where(
                CompetitionParticipant.user_id == authorized_user["user_id"],
            )
        )

        submission_interests = (await db_session.execute(stmt)).all()
        interests = []

        for interest in submission_interests:
            interest_dict = {
                "id": str(interest[0]),
                "title": interest[1],
                "prize_type": interest[2],
                "total_pool_amount": interest[3],
                "currency": interest[4],
                "submission_starts_at": interest[5],
                "submission_ends_at": interest[6],
            }
            interests.append(interest_dict)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submission interests fetched successfully",
            data={"interests": interests},
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return CustomBackendError(
            message="Failed to get submission interests",
            details=str(e),
        )
