import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, List, Literal, Optional, Union

from .submission_responses import CompetitionTimelinesSchema
from ...database.challenge.enums import (
    AdditionalAttachmentSchema,
    CompetitionStatusEnum,
    Datasets,
    PrizeTypeEnum,
    RulesAndGuidelinesSchema,
)
from ..discussion.discussion_responses import PaginatedResponseMeta, UserSchema
from ..default_schemas import (
    SuccessfulResponse,
    BackendErrorResponse,
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
    BadRequestErrorResponse,
)


class CompetitionEvaluationSchema(BaseModel):
    id: uuid.UUID
    evaluation_criteria: Optional[str]
    submission_criteria: Optional[str]

    model_config = {"from_attributes": True}


class ComepetitionDatasetsSchema(BaseModel):
    id: uuid.UUID
    description: Optional[str]
    datasets: Optional[List[Datasets]]
    ai_models: Optional[List[Datasets]]
    additional_assets: Optional[Dict[str, AdditionalAttachmentSchema]]

    model_config = {"from_attributes": True}


class CompetitionPrizePoolSchema(BaseModel):
    id: uuid.UUID
    prize_type: PrizeTypeEnum
    total_pool_amount: Optional[float]
    currency: Optional[str]
    prize_description: Optional[str]

    model_config = {"from_attributes": True}


class RetrieveChanllengeByIDSchema(BaseModel):
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
    constraints: Optional[str]
    rules_and_guidelines: Optional[RulesAndGuidelinesSchema]
    other_resources: Optional[str]
    results_announced_at: Optional[datetime]
    creator: UserSchema
    prize_pools: Optional[CompetitionPrizePoolSchema]
    timelines: Optional[CompetitionTimelinesSchema]
    evaluations: Optional[CompetitionEvaluationSchema]
    datasets: Optional[ComepetitionDatasetsSchema]
    participant_count: Optional[int] = 0
    submission_count: Optional[int] = 0
    is_joined: Optional[bool] = False
    is_drafted: Optional[bool] = False
    is_bookmarked: Optional[bool] = False

    model_config = {"from_attributes": True}


class ParticipatedCompetitionsSchema(BaseModel):
    id: uuid.UUID
    title: str
    status: CompetitionStatusEnum
    prize_pools: CompetitionPrizePoolSchema
    timelines: CompetitionTimelinesSchema

    model_config = {"from_attributes": True}


class RetrieveCompetitionsSchema(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: Optional[str]
    image_url: Optional[str]
    prize_pools: CompetitionPrizePoolSchema
    timelines: CompetitionTimelinesSchema
    participant_count: Optional[int] = 0
    submission_count: Optional[int] = 0
    results_announced_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RetrieveCompetitionsData(BaseModel):
    competitions: List[RetrieveCompetitionsSchema]


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
    message: Literal["Challenge leaderboard retrieved successfully"]
    data: RetrieveCompetitionsLeaderboardData
    meta: PaginatedResponseMeta


class RetrieveCompetitionsLeaderboardBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while retrieving the challenge leaderboard. Please contact developers if the issue persists."
        ],
    ]


class RetrieveCompetitionsLeaderboardBackendErrorResponse(BackendErrorResponse):
    message: Literal["Challenge leaderboard retrieval failed"]
    error: RetrieveCompetitionsLeaderboardBackendError


RETRIEVE_COMPETITION_LEADERBOARD_RESPONSE_MODEL = {
    200: {"model": RetrieveCompetitionsLeaderboardSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": RetrieveCompetitionsLeaderboardBackendErrorResponse},
}


class RetrieveParticipatedCompetitionsResponseData(BaseModel):
    competitions: List[ParticipatedCompetitionsSchema]


class RetrieveParticipatedCompetitionsSuccessResponse(SuccessfulResponse):
    message: Literal["Participated challenges retrieved successfully"]
    data: RetrieveParticipatedCompetitionsResponseData
    meta: PaginatedResponseMeta


class RetrieveParticipatedCompetitionsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while retrieving the participated challenges. Please contact developers if the issue persists."
        ],
    ]


class RetrieveParticipatedCompetitionsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Participated challenges retrieval failed"]
    error: RetrieveParticipatedCompetitionsBackendError


RETRIEVE_PARTICIPATED_COMPETITIONS_RESPONSE_MODEL = {
    200: {"model": RetrieveParticipatedCompetitionsSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": RetrieveParticipatedCompetitionsBackendErrorResponse},
}


class RetrieveBookmarkedCompetitionsCompetitionSchema(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: Optional[str]
    status: CompetitionStatusEnum
    image_url: Optional[str]
    timelines: Optional[CompetitionTimelinesSchema]
    prize_pools: Optional[CompetitionPrizePoolSchema]

    model_config = {"from_attributes": True}


class RetrieveBookmarkedCompetitionsSchema(BaseModel):
    id: uuid.UUID
    created_at: datetime
    competition: RetrieveBookmarkedCompetitionsCompetitionSchema
    participant_count: Optional[int] = 0

    model_config = {"from_attributes": True}


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


# =====================================================================
# RETRIEVE CHALLENGE BY ID RESPONSE MODELS
# =====================================================================
class RetrieveChallengeByIDSuccessResponse(SuccessfulResponse):
    message: Literal["Challenge retrieved successfully"]
    data: RetrieveChanllengeByIDSchema
    error: None = None
    meta: None = None


RETRIEVE_CHALLENGE_BY_ID_RESPONSE_MODEL = {
    200: {"model": RetrieveChallengeByIDSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": BadRequestErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RETRIEVE ALL COMPETITIONS RESPONSE MODELS
# =====================================================================
class RetrieveCompetitionsSuccessResponse(SuccessfulResponse):
    message: Literal["Challenges retrieved successfully"]
    data: RetrieveCompetitionsData
    meta: PaginatedResponseMeta


RETRIEVE_COMPETITIONS_RESPONSE_MODEL = {
    200: {"model": RetrieveCompetitionsSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# USERS LIST CHALLENGES RESPONSE MODELS
# =====================================================================
class UserListChallengesCompetitionSchema(BaseModel):
    id: uuid.UUID
    title: str
    image_url: Optional[str]
    status: CompetitionStatusEnum
    prize_pools: Optional[CompetitionPrizePoolSchema]
    timelines: Optional[CompetitionTimelinesSchema]
    participant_count: Optional[int] = 0
    submission_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class UserListChallengesData(BaseModel):
    competitions: List[UserListChallengesCompetitionSchema]


class UserListChallengesSuccessResponse(SuccessfulResponse):
    message: Literal["Published challenges retrieved successfully"]
    data: UserListChallengesData
    meta: PaginatedResponseMeta


USERS_LIST_CHALLENGES_RESPONSE_MODEL = {
    200: {"model": UserListChallengesSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    500: {"model": BackendErrorResponse},
}
