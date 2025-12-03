# app/services/challenge_leaderboard_services.py

from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from ...middlewares.logging import logger
from ...schemas.custom_responses import CustomJSONResponse
from ...database.challenge.models import Competition, CompetitionSubmission, User


async def get_competition_leaderboard_handler(
    competition_id: UUID,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Handler that retrieves leaderboard data for a competition.
    """

    logger.info(f"Leaderboard handler started for competition_id={competition_id}")

    # ------------------------
    # 1) Check competition exists
    # ------------------------
    comp_result = await db_session.execute(
        select(Competition.id).where(Competition.id == competition_id)
    )
    if comp_result.scalar_one_or_none() is None:
        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
            message="Resource not found",
            error={
                "code": "NOT_FOUND",
                "details": "Competition not found.",
            },
        )

    # ------------------------
    # 2) Query leaderboard with user info
    # ------------------------
    stmt = (
        select(
            CompetitionSubmission.id.label("submission_id"),
            CompetitionSubmission.competition_id.label("competition_id"),
            CompetitionSubmission.title.label("title"),
            CompetitionSubmission.description.label("description"),
            CompetitionSubmission.score.label("score"),
            CompetitionSubmission.created_at.label("submitted_on"),
            CompetitionSubmission.updated_at.label("challenge_last_updated"),
            User.id.label("user_id"),
            User.name.label("user_name"),
            User.email.label("user_email"),
        )
        .join(User, User.id == CompetitionSubmission.user_id)
        .where(
            CompetitionSubmission.competition_id == competition_id,
            CompetitionSubmission.is_disqualified.is_(False),
        )
        .order_by(CompetitionSubmission.score.desc().nullslast())
    )

    # ------------------------
    # 3) Count total submissions
    # ------------------------
    total_submissions = (
        await db_session.execute(
            select(func.count())
            .select_from(CompetitionSubmission)
            .where(
                CompetitionSubmission.competition_id == competition_id,
                CompetitionSubmission.is_disqualified.is_(False),
            )
        )
    ).scalar_one()

    total_pages = 1 if total_submissions > 0 else 0

    result = await db_session.execute(stmt)
    rows = result.all()

    # ------------------------
    # 4) Shape response
    # ------------------------
    submissions = []
    current_rank = 1

    for row in rows:
        submissions.append(
            {
                "rank": current_rank,
                "competition_id": str(row.competition_id),
                "submission_id": str(row.submission_id),
                "title": row.title,
                "description": row.description,
                "score": float(row.score) if row.score is not None else None,
                "submitted_on": row.submitted_on.isoformat() if row.submitted_on else None,
                "challenge_last_updated": (
                    row.challenge_last_updated.isoformat()
                    if row.challenge_last_updated
                    else None
                ),
                "user": {
                    "id": str(row.user_id),
                    "name": row.user_name,
                    "email": row.user_email,
                },
            }
        )
        current_rank += 1

    return CustomJSONResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Leaderboard retrieved successfully",
        data={"submissions": submissions},
        meta={
            "competition_id": str(competition_id),
            "total_submissions": total_submissions,
            "total_pages": total_pages,
        },
    )
