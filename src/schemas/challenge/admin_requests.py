import enum
from typing import Optional
from fastapi import Path, Query

from .submission_requests import SortOrder
from ...database.challenge.enums import CompetitionStatusEnum


class AdminRetreiveCompetitionsSortBy(enum.Enum):
    TITLE = "title"
    PUBLISHED_AT = "published_at"
    EVALUATION_ENDS_AT = "evaluation_ends_at"
    SCHEDULED_PUBLISH_AT = "scheduled_publish_at"
    UPDATED_AT = "updated_at"


class AdminRetrieveCompetitionsChoices(enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    EVALUATION = "evaluation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AdminRetrieveCompetitionsParams:
    STATUS_MAP = {
        "draft": CompetitionStatusEnum.DRAFT,
        "scheduled": CompetitionStatusEnum.SCHEDULED,
        "published": CompetitionStatusEnum.PUBLISHED,
        "evaluation": CompetitionStatusEnum.EVALUATION,
        "completed": CompetitionStatusEnum.COMPLETED,
        "cancelled": CompetitionStatusEnum.CANCELLED,
    }

    def __init__(
        self,
        choice: AdminRetrieveCompetitionsChoices = Path(
            ..., description="Type of the competition to retrieve"
        ),
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of competitions per page"),
        sort_by: Optional[AdminRetreiveCompetitionsSortBy] = Query(
            default=None,
            description="The field to sort by",
        ),
        sort_order: Optional[SortOrder] = Query(
            default=None,
            description="The order to sort by",
        ),
    ):
        self.choice: CompetitionStatusEnum = self.STATUS_MAP[choice.value]
        self.query = query
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order
