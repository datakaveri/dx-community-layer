from datetime import datetime
from typing import List, Literal, Optional, Union
import uuid
from pydantic import BaseModel

from .submission_responses import CompetitionTimelinesSchema
from ...database.challenge.enums import PrizeTypeEnum
from ..discussion.discussion_responses import PaginatedResponseMeta, UserSchema
from ..default_schemas import (
    SuccessfulResponse,
    BackendErrorResponse,
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
    BadRequestErrorResponse,
)


class RetrieveCompetitionsLeaderboardsCompetition(BaseModel):
    id: uuid.UUID
    title: str

    model_config = {"from_attributes": True}


class RetrieveCompetitionsLeaderboardsSubmissions(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    user: UserSchema
    competition: RetrieveCompetitionsLeaderboardsCompetition
    score: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RetrieveCompetitionsLeaderboardData(BaseModel):
    submissions: List[RetrieveCompetitionsLeaderboardsSubmissions]


class RetrieveCompetitionsLeaderboardSuccessResponse(SuccessfulResponse):
    message: Literal["Competition leaderboard retrieved successfully"]
    data: RetrieveCompetitionsLeaderboardData
    meta: PaginatedResponseMeta


class RetrieveCompetitionsLeaderboardBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while retrieving the competition leaderboard. Please contact developers if the issue persists."
        ],
    ]


class RetrieveCompetitionsLeaderboardBackendErrorResponse(BackendErrorResponse):
    message: Literal["Competition leaderboard retrieval failed"]
    error: RetrieveCompetitionsLeaderboardBackendError


RETRIEVE_COMPETITION_LEADERBOARD_RESPONSE_MODEL = {
    200: {"model": RetrieveCompetitionsLeaderboardSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": RetrieveCompetitionsLeaderboardBackendErrorResponse},
}


class CompetitionPrizePoolSchema(BaseModel):
    id: uuid.UUID
    prize_type: PrizeTypeEnum
    total_pool_amount: Optional[float]
    currency: Optional[str]
    prize_description: Optional[str]

    model_config = {"from_attributes": True}


class ParticipatedCompetitionsSchema(BaseModel):
    id: uuid.UUID
    title: str
    prize_pools: CompetitionPrizePoolSchema
    timelines: CompetitionTimelinesSchema

    model_config = {"from_attributes": True}


class RetrieveParticipatedCompetitionsResponseData(BaseModel):
    competitions: List[ParticipatedCompetitionsSchema]


class RetrieveParticipatedCompetitionsSuccessResponse(SuccessfulResponse):
    message: Literal["Participated competitions retrieved successfully"]
    data: RetrieveParticipatedCompetitionsResponseData
    meta: PaginatedResponseMeta


class RetrieveParticipatedCompetitionsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while retrieving the participated competitions. Please contact developers if the issue persists."
        ],
    ]


class RetrieveParticipatedCompetitionsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Participated competitions retrieval failed"]
    error: RetrieveParticipatedCompetitionsBackendError


RETRIEVE_PARTICIPATED_COMPETITIONS_RESPONSE_MODEL = {
    200: {"model": RetrieveParticipatedCompetitionsSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": RetrieveParticipatedCompetitionsBackendErrorResponse},
}


class CreateCompetitionData(BaseModel):
    competition_id: str
    status: str


class CreateCompetitionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: str = "Resource created successfully"
    data: CreateCompetitionData
    error: None = None
    meta: None = None


CREATE_COMPETITION_RESPONSE_MODEL = {
    201: {"model": CreateCompetitionSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}


class CreateCompetitionData(BaseModel):
    competition_id: str
    status: str


class CreateCompetitionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: str = "Resource created successfully"
    data: CreateCompetitionData
    error: None = None
    meta: None = None


CREATE_COMPETITION_RESPONSE_MODEL = {
    201: {"model": CreateCompetitionSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}
