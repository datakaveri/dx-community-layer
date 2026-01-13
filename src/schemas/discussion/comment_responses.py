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
from ...database.discussion.enums import CommentsStatusEnum
from .discussion_responses import PaginatedResponseMeta, UserSchema


class CommentAttachmentSchema(BaseModel):
    id: uuid.UUID
    comment_id: uuid.UUID
    attachment_metadata: dict[str, Any]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class CommentReactionsSchema(BaseModel):
    emojis: dict[str, int] = {}
    user_reaction: dict[str, str] = {}

    model_config = {"from_attributes": True}


class CommentSchema(BaseModel):
    id: uuid.UUID
    discussion_id: uuid.UUID
    user: UserSchema
    parent_id: Optional[uuid.UUID]
    replied_to: Optional[UserSchema]
    comment: str
    created_at: datetime
    status: CommentsStatusEnum
    approved_at: Optional[datetime]
    sub_comments_count: int = 0
    comment_attachments: List[CommentAttachmentSchema]
    votes: int = 0
    is_voted: bool = False
    comment_reactions: CommentReactionsSchema = CommentReactionsSchema()

    model_config = {"from_attributes": True}


class RetrieveCommentsSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussion comments retrieved successfully"]
    data: List[CommentSchema]
    meta: PaginatedResponseMeta


class RetrieveCommentsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "An error occurred while retrieving the discussion comments. Please contact developers if the issue persists."
    ]


class RetrieveCommentsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion comments retrieval failed"]
    error: RetrieveCommentsBackendError


RETRIEVE_COMMENTS_RESPONSE_MODEL = {
    200: {"model": RetrieveCommentsSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": NotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": RetrieveCommentsBackendErrorResponse},
}


# Reaction response models


class AddUpdateCommentReactionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Comment reaction added/updated successfully"]


ADD_UPDATE_COMMENT_REACTION_RESPONSE_MODEL = {
    200: {"model": AddUpdateCommentReactionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": NotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
}


class DeleteCommentReactionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Comment reaction removed successfully"]


DELETE_COMMENT_REACTION_RESPONSE_MODEL = {
    200: {"model": DeleteCommentReactionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": NotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
}


class DeleteCommentSuccessfulResponse(SuccessfulResponse):
    message: Literal["Comment deleted successfully"]


class DeleteCommentForbiddenError(BaseModel):
    code: Literal["FORBIDDEN"]
    details: Literal[
        "You do not have permission to delete this comment. Please contact developers if the issue persists."
    ]


class DeleteCommentForbiddenErrorResponse(ForbiddenErrorResponse):
    error: DeleteCommentForbiddenError


class DeleteCommentNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The comment does not exist. Please contact developers if the issue persists."
    ]


class DeleteCommentNotFoundErrorResponse(NotFoundErrorResponse):
    error: DeleteCommentNotFoundError


class DeleteCommentBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "An error occurred while deleting the comment. Please contact developers if the issue persists."
    ]


class DeleteCommentBackendErrorResponse(BackendErrorResponse):
    error: DeleteCommentBackendError


DELETE_COMMENT_RESPONSE_MODEL = {
    200: {"model": DeleteCommentSuccessfulResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": DeleteCommentForbiddenErrorResponse},
    404: {"model": DeleteCommentNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": DeleteCommentBackendErrorResponse},
}
