import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import List, Literal, Union

from .default_schemas import (
    BackendErrorResponse,
    BadRequestErrorResponse,
    SuccessfulResponse,
    UnauthorizedErrorResponse,
    NotFoundErrorResponse,
    ForbiddenErrorResponse,
    ValidationErrorResponse,
)
from ..database.enums import (
    DiscussionsCategoryEnum,
    DiscussionsStatusEnum,
    DiscussionsTypeEnum,
)
from .discussion_responses import UserSchema


class AdminRetrieveDiscussionsResponseDiscussion(BaseModel):
    id: uuid.UUID
    user: UserSchema
    title: str
    type: DiscussionsTypeEnum
    category: DiscussionsCategoryEnum
    sub_category: str
    status: DiscussionsStatusEnum
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminRetrieveDiscussionsResponseMeta(BaseModel):
    total_count: int
    total_pages: int
    current_page: int
    limit: int


class AdminRetrieveDiscussionsSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussions retrieved successfully"]
    data: List[AdminRetrieveDiscussionsResponseDiscussion]
    meta: AdminRetrieveDiscussionsResponseMeta


class AdminRetrieveDiscussionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while retrieving discussions. Please contact developers if the issue persists."
        ],
    ]


class AdminRetrieveDiscussionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to retrieve discussions"]
    error: AdminRetrieveDiscussionBackendError


ADMIN_RETRIEVE_DISCUSSIONS_RESPONSE_MODEL = {
    200: {"model": AdminRetrieveDiscussionsSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": AdminRetrieveDiscussionBackendErrorResponse},
}


class AdminReviewDiscussionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussion reviewed successfully"]


class AdminReviewDiscussionNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The discussion does not exist. Please contact developers if the issue persists."
    ]


class AdminReviewDiscussionNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Discussion not found"]
    error: AdminReviewDiscussionNotFoundError


class AdminReviewDiscussionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while reviewing discussion. Please contact developers if the issue persists."
        ],
    ]


class AdminReviewDiscussionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to review discussion"]
    error: AdminReviewDiscussionBackendError


ADMIN_REVIEW_DISCUSSION_RESPONSE_MODEL = {
    200: {"model": AdminReviewDiscussionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": AdminReviewDiscussionNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": AdminReviewDiscussionBackendErrorResponse},
}
