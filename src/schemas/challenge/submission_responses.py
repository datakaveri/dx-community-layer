import uuid
from datetime import datetime, date
from pydantic import BaseModel
from typing import Any, List, Literal, Optional, Union

from ..default_schemas import (
    BadRequestErrorResponse,
    SuccessfulResponse,
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
    NotFoundErrorResponse,
    ConflictErrorResponse,
    BackendErrorResponse,
    ValidationErrorResponse,
)
from ..discussion.discussion_responses import PaginatedResponseMeta, UserSchema


class CompetitionTimelinesSchema(BaseModel):
    id: uuid.UUID
    submission_starts_at: date
    submission_ends_at: date
    evaluation_ends_at: Optional[date]

    model_config = {"from_attributes": True}


class UserSubmissionCompetitionSchema(BaseModel):
    id: uuid.UUID
    title: str
    timelines: CompetitionTimelinesSchema

    model_config = {"from_attributes": True}


class UserSubmissionsSchema(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    user: UserSchema
    competition: UserSubmissionCompetitionSchema
    is_disqualified: bool
    score: Optional[float]
    evaluation_comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RetrieveUserSubmissionsData(BaseModel):
    submissions: List[UserSubmissionsSchema]


class RetrieveUserSubmissionsSuccessResponse(SuccessfulResponse):
    message: Literal["Discussions retrieved successfully"]
    data: RetrieveUserSubmissionsData
    meta: PaginatedResponseMeta


class RetrieveUserSubmissionsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while retrieving the submissions. Please contact developers if the issue persists."
        ],
    ]


class RetrieveUserSubmissionsBackendErrorResponse(BackendErrorResponse):
    message: Literal["User submissions retrieval failed"]
    error: RetrieveUserSubmissionsBackendError


RETRIEVE_USER_SUBMISSIONS_RESPONSE_MODEL = {
    200: {"model": RetrieveUserSubmissionsSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": RetrieveUserSubmissionsBackendErrorResponse},
}


class SubmissionAttachment(BaseModel):
    file_name: str
    metadata: dict[str, Any]
    s3_key: str


class SubmissionData(BaseModel):
    submission_id: str
    competition_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    competition_title: Optional[str] = None
    title: str
    description: str
    attachments: Optional[dict[str, Any]] = None
    submission_count: int
    is_disqualified: bool
    score: Optional[float] = None
    evaluation_comment: Optional[str] = None
    created_at: str
    updated_at: str


class CreateSubmissionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: Literal["Submission created successfully"]
    data: SubmissionData
    error: None = None
    meta: None = None


CREATE_SUBMISSION_RESPONSE_MODEL = {
    201: {"model": CreateSubmissionSuccessResponse},
    400: {"description": "Validation errors for submission window or request"},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    409: {"model": ConflictErrorResponse},
    500: {"model": BackendErrorResponse},
}


class SubmissionListData(BaseModel):
    submissions: List[SubmissionData]


class SubmissionListMeta(BaseModel):
    total_submissions: int
    total_pages: int
    current_page: int
    limit: int


class SubmissionListSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: Literal["Submissions retrieved successfully"]
    data: SubmissionListData
    error: None = None
    meta: SubmissionListMeta


LIST_SUBMISSIONS_RESPONSE_MODEL = {
    200: {"model": SubmissionListSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


class DisqualifySubmissionResponse(BaseModel):
    submission_id: str
    is_disqualified: bool
    message: str
