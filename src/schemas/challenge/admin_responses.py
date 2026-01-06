import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, List, Literal, Optional, TypeVar, Union

from ...schemas.default_schemas import (
    BackendErrorResponse,
    BadRequestErrorResponse,
    ConflictErrorResponse,
    CreatedResponse,
    ForbiddenErrorResponse,
    UnauthorizedErrorResponse,
    NotFoundErrorResponse,
    SuccessfulResponse,
)
from ..discussion.discussion_responses import UserSchema, PaginatedResponseMeta
from .submission_responses import CompetitionTimelinesSchema
from .competition_responses import (
    ComepetitionDatasetsSchema,
    CompetitionEvaluationSchema,
    CompetitionPrizePoolSchema,
)
from ...database.challenge.enums import (
    CompetitionStatusEnum,
    RulesAndGuidelinesSchema,
    SubmissionAttachmentSchema,
)

# =====================================================================
# GENERIC BASE CLASSES FOR REDUCING REDUNDANCY
# =====================================================================
DataType = TypeVar("DataType")
MessageType = TypeVar("MessageType", bound=str)


class AdminBackendError(BaseModel):
    """Generic backend error for admin endpoints"""
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal["Failed to authorize user. Please contact developers if the issue persists."],
        Literal["An error occurred while processing your request. Please contact developers if the issue persists."],
    ]


class AdminBackendErrorResponse(BackendErrorResponse):
    """Generic backend error response for admin endpoints"""
    message: str
    error: AdminBackendError


# =====================================================================
# DATA SCHEMAS
# =====================================================================
class AdminRetrieveChanllengeByIDSchema(BaseModel):
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

    model_config = {"from_attributes": True}


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
    attachments: Optional[Dict[str, SubmissionAttachmentSchema]]
    is_disqualified: bool
    score: Optional[float]
    submission_count: int
    evaluation_comment: Optional[str]
    evaluation_attachments: Optional[Dict[str, SubmissionAttachmentSchema]]
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


class AdminRetrieveCompetitionSubmissionsData(BaseModel):
    submissions: List[AdminRetrieveCompetitionSubmissionSchema]


class AdminCreateCompetitionCreatedData(BaseModel):
    competition_id: uuid.UUID
    status: CompetitionStatusEnum


class EvaluationData(BaseModel):
    submission_id: uuid.UUID
    score: Optional[float]
    is_disqualified: bool
    evaluation_comment: Optional[str]
    evaluation_attachments: Optional[Dict[str, SubmissionAttachmentSchema]]


# =====================================================================
# RESPONSE MODELS - CREATE COMPETITION
# =====================================================================
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


ADMIN_CREATE_COMPETITION_RESPONSE_MODEL = {
    201: {"model": AdminCreateCompetitionCreatedResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    409: {"model": AdminCreateCompetitionConflictErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - RETRIEVE CHALLENGE BY ID
# =====================================================================
class AdminRetrieveChallengeByIDSuccessResponse(SuccessfulResponse):
    message: Literal["Challenge retrieved successfully"]
    data: AdminRetrieveChanllengeByIDSchema
    error: None = None
    meta: None = None


ADMIN_RETRIEVE_CHALLENGE_BY_ID_RESPONSE_MODEL = {
    200: {"model": AdminRetrieveChallengeByIDSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - RETRIEVE COMPETITIONS
# =====================================================================
class AdminRetrieveCompetitionsSuccessResponse(SuccessfulResponse):
    message: Literal["Competitions retrieved successfully"]
    data: AdminRetrieveCompetitionsData
    meta: PaginatedResponseMeta


ADMIN_RETRIEVE_COMPETITIONS_RESPONSE_MODEL = {
    200: {"model": AdminRetrieveCompetitionsSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - UPDATE COMPETITION
# =====================================================================
class AdminUpdateCompetitionSuccessResponse(SuccessfulResponse):
    message: Literal["Competition updated successfully"]
    data: AdminCreateCompetitionCreatedData
    error: None = None
    meta: None = None


ADMIN_UPDATE_COMPETITION_RESPONSE_MODEL = {
    200: {"model": AdminUpdateCompetitionSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - RETRIEVE CHALLENGE DATASET
# =====================================================================
class AdminRetrieveChallengeDatasetSuccessResponse(SuccessfulResponse):
    message: Literal["Challenge dataset retrieved successfully"]
    data: ComepetitionDatasetsSchema
    error: None = None
    meta: None = None


ADMIN_RETRIEVE_CHALLENGE_DATASET_RESPONSE_MODEL = {
    200: {"model": AdminRetrieveChallengeDatasetSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - RETRIEVE COMPETITION SUBMISSIONS
# =====================================================================
class AdminRetrieveCompetitionSubmissionsSuccessResponse(SuccessfulResponse):
    message: Literal["Competition submissions retrieved successfully"]
    data: AdminRetrieveCompetitionSubmissionsData
    meta: PaginatedResponseMeta


ADMIN_RETRIEVE_COMPETITION_SUBMISSIONS_RESPONSE_MODEL = {
    200: {"model": AdminRetrieveCompetitionSubmissionsSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - DELETE CHALLENGE
# =====================================================================
class AdminDeleteChallengeSuccessResponse(SuccessfulResponse):
    message: Literal["Challenge deleted successfully"]
    data: None = None
    error: None = None
    meta: None = None


ADMIN_DELETE_CHALLENGE_RESPONSE_MODEL = {
    200: {"model": AdminDeleteChallengeSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - EVALUATE SUBMISSION
# =====================================================================
class AdminEvaluateSubmissionSuccessResponse(SuccessfulResponse):
    message: Literal["Submission evaluated successfully"]
    data: EvaluationData
    error: None = None
    meta: None = None


ADMIN_EVALUATE_SUBMISSION_RESPONSE_MODEL = {
    200: {"model": AdminEvaluateSubmissionSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


# =====================================================================
# RESPONSE MODELS - ANNOUNCE COMPETITION RESULT
# =====================================================================
class AdminAnnounceCompetitionResultSuccessResponse(SuccessfulResponse):
    message: Literal["Competition result announced successfully"]
    data: None = None
    error: None = None
    meta: None = None


ADMIN_ANNOUNCE_COMPETITION_RESULT_RESPONSE_MODEL = {
    200: {"model": AdminAnnounceCompetitionResultSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}
