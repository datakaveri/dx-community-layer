from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ...schemas.default_schemas import AuthorizationData
from ...database.challenge.models import Competition, CompetitionParticipant
from ...database.challenge.enums import CompetitionStatusEnum


async def user_join_competition_handler(
    competition_id: UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Handles the user join competition operation.
    Ensures the competition exists, is published, and the user hasn't already joined.
    """

    try:
        user_id = authorized_user["user_id"]

        # Ensure user_id is available (authorization middleware should enforce this)
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

        # Check if the user already joined
        existing_participant_stmt = select(CompetitionParticipant.id).where(
            CompetitionParticipant.competition_id == competition_id,
            CompetitionParticipant.user_id == user_id,
        )
        existing_participant_result = await db_session.execute(existing_participant_stmt)
        existing_participant = existing_participant_result.first()

        if existing_participant:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_409_CONFLICT,
                message="Resource already exists",
                error={
                    "code": "CONFLICT",
                    "details": "You have already joined this competition.",
                },
            )

        # Create new participant entry
        new_participant = CompetitionParticipant(
            competition_id=competition_id,
            user_id=user_id,
        )
        db_session.add(new_participant)
        await db_session.commit()
        await db_session.refresh(new_participant)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_201_CREATED,
            message="Successfully joined the competition",
            data={
                "participant_id": str(new_participant.id),
                "competition_id": str(competition_id),
                "user_id": str(user_id),
                "joined_at": new_participant.joined_at.isoformat(),
            },
        )
    except Exception as exc:
        logger.error("Failed to join competition", exc_info=True)
        await db_session.rollback()
        return CustomBackendError(
            message="Failed to join competition",
            details=str(exc),
        )


