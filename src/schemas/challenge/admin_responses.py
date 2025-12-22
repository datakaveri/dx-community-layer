import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import List, Literal, Optional, Union

from ...schemas.default_schemas import (
    BackendErrorResponse,
    BadRequestErrorResponse,
    ConflictErrorResponse,
    CreatedResponse,
    ForbiddenErrorResponse,
    UnauthorizedErrorResponse,
)
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


class AdminCreateCompetitionCreatedData(BaseModel):
    competition_id: uuid.UUID
    status: CompetitionStatusEnum


class AdminCreateCompetitionCreatedResponse(CreatedResponse):
    message: Literal["Competition created successfully"]
    data: AdminCreateCompetitionCreatedData


class AdminCreateCompetitionConflictError(BaseModel):
    code: Literal["CONFLICT"]
    details: Literal[
        "A competition with the same title already exists. Please use a different title."
    ]


class AdminCreateCompetitionConflictErrorResponse(ConflictErrorResponse):
    message: Literal["Competition already exists"]
    error: AdminCreateCompetitionConflictError


class AdminCreateCompetitionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while creating the competition. Please contact developers if the issue persists."
        ],
    ]


class AdminCreateCompetitionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Competition creation failed"]
    error: AdminCreateCompetitionBackendError


ADMIN_CREATE_COMPETITION_RESPONSE_MODEL = {
    201: {"model": AdminCreateCompetitionCreatedResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    409: {"model": AdminCreateCompetitionConflictErrorResponse},
    500: {"model": AdminCreateCompetitionBackendErrorResponse},
}
