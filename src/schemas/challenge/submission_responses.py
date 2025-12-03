from typing import Any, List, Literal, Optional

from pydantic import BaseModel

from ..default_schemas import (
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
    NotFoundErrorResponse,
    ConflictErrorResponse,
    BackendErrorResponse,
)


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
