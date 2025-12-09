from datetime import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel

from ..discussion.discussion_responses import UserSchema
from .submission_responses import CompetitionTimelinesSchema
from .competition_responses import CompetitionPrizePoolSchema
from ...database.challenge.enums import CompetitionStatusEnum


class AdminRetrieveCompetitionsSchema(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: Optional[str]
    overview: Optional[str]
    detailed_description: Optional[str]
    status: CompetitionStatusEnum
    image_url: Optional[str]
    updated_at: datetime
    published_at: Optional[datetime]
    scheduled_publish_at: Optional[datetime]
    prize_pools: Optional[CompetitionPrizePoolSchema]
    timelines: Optional[CompetitionTimelinesSchema]
    participant_count: Optional[int] = 0
    submission_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class AdminRetrieveCompetitionsData(BaseModel):
    competitions: List[AdminRetrieveCompetitionsSchema]


class AdminRetrieveCompetitionSubmissionSchema(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    user: UserSchema
    attachments: Optional[List]
    is_disqualified: bool
    score: Optional[float]
    submission_count: int
    evaluation_comment: Optional[str]
    evaluation_attachments: Optional[List]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminRetrieveCompetitionSubmissionCompetitionSchema(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: Optional[str]
    status: CompetitionStatusEnum
    results_announced_at: Optional[datetime]

    model_config = {"from_attributes": True}
