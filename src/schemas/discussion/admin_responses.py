import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Any, List, Literal, Optional, Union

from ..default_schemas import (
    BackendErrorResponse,
    BadRequestErrorResponse,
    SuccessfulResponse,
    UnauthorizedErrorResponse,
    NotFoundErrorResponse,
    ForbiddenErrorResponse,
    ValidationErrorResponse,
)
from ...database.discussion.enums import (
    CommentsStatusEnum,
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
    reviewed_at: Optional[datetime] = None
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


class AdminPendingCommentsDiscussion(BaseModel):
    id: uuid.UUID
    title: str
    type: DiscussionsTypeEnum
    category: DiscussionsCategoryEnum

    model_config = {"from_attributes": True}


class AdminPendingCommentsCommentAttachments(BaseModel):
    id: uuid.UUID
    attachment_metadata: dict[str, Any]
    s3_key: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class AdminRetrieveCommentsSchema(BaseModel):
    id: uuid.UUID
    discussion: AdminPendingCommentsDiscussion
    user: UserSchema
    comment: str
    comment_attachments: Optional[List[AdminPendingCommentsCommentAttachments]]
    created_at: datetime
    status: CommentsStatusEnum
    approved_at: Optional[datetime]
    approved_by_user: Optional[UserSchema]

    model_config = {"from_attributes": True}


ADMIN_REVIEW_COMMENT_RESPONSE_MODEL = {
    200: {
        "description": "Comment reviewed successfully",
        "content": {
            "application/json": {
                "example": {"success": True, "message": "Comment reviewed successfully"}
            }
        },
    },
    404: {
        "description": "Comment not found",
    },
    403: {
        "description": "Forbidden",
    },
}
