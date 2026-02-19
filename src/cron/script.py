import pytz
import asyncio
from typing import List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..middlewares.logging import logger
from ..configs.db_config import ChallengeAsyncSessionLocal
from ..database.challenge.enums import CompetitionStatusEnum
from ..database.challenge.models import Competition, CompetitionTimeline


async def get_pending_publish_competitions(db: AsyncSession):
    try:
        current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))
        stmt = select(Competition).where(
            Competition.scheduled_publish_at <= current_timestamp,
            Competition.status != CompetitionStatusEnum.PUBLISHED,
        )
        result = await db.execute(stmt)
        return result.scalars().unique().all()
    except Exception as e:
        logger.error(f"Failed to get pending publish competitions: {e}")
        return None


async def publish_competitions(competitions: List[Competition], db: AsyncSession):
    try:
        current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

        for competition in competitions:
            competition.status = CompetitionStatusEnum.PUBLISHED
            competition.published_at = current_timestamp

        await db.commit()
        logger.info(f"Published {len(competitions)} competitions.")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to publish competitions: {e}")
        return False


async def get_pending_evaluation_competitions(db: AsyncSession):
    try:
        current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata")).date()
        stmt = (
            select(Competition)
            .join(
                CompetitionTimeline,
                Competition.id == CompetitionTimeline.competition_id,
            )
            .filter(
                CompetitionTimeline.submission_ends_at < current_timestamp,
                Competition.status == CompetitionStatusEnum.PUBLISHED,
            )
        )
        records = await db.execute(stmt)
        return records.scalars().unique().all()
    except Exception as e:
        logger.error(f"Failed to get pending evaluation competitions: {e}")
        return None


async def evaluate_competitions(competitions: List[Competition], db: AsyncSession):
    try:
        current_timestamp = datetime.now(pytz.timezone("Asia/Kolkata"))

        for competition in competitions:
            competition.status = CompetitionStatusEnum.EVALUATION
            competition.updated_at = current_timestamp

        await db.commit()
        logger.info(f"Evaluation started for {len(competitions)} competitions.")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to evaluate competitions: {e}")
        return False


async def run_cron_job():
    logger.info("Cron publisher job started.")
    try:
        async with ChallengeAsyncSessionLocal() as db:
            competitions_to_publish = await get_pending_publish_competitions(db)
            competitions_to_evaluate = await get_pending_evaluation_competitions(db)

            if competitions_to_publish:
                await publish_competitions(competitions_to_publish, db)
            else:
                logger.info("No pending records to publish.")

            if competitions_to_evaluate:
                await evaluate_competitions(competitions_to_evaluate, db)
            else:
                logger.info("No pending records to evaluate.")

    except Exception as e:
        logger.exception(f"Unexpected error in cron job: {e}")
    finally:
        logger.info("Cron publisher job completed.")


def main():
    asyncio.run(run_cron_job())


if __name__ == "__main__":
    main()
