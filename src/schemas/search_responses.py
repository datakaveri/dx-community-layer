from datetime import datetime
from typing import List, Literal, Union
import uuid
from pydantic import BaseModel

from .default_schemas import (
    BackendErrorResponse,
    BadRequestErrorResponse,
    SuccessfulResponse,
    UnauthorizedErrorResponse,
    ValidationErrorResponse,
)
from ..database.enums import (
    DiscussionsCategoryEnum,
    DiscussionsStatusEnum,
    DiscussionsTypeEnum,
)
from .discussion_responses import UserSchema, TagSchema


class SearchSuccessfulMeta(BaseModel):
    total_count: int
    total_pages: int
    current_page: int
    limit: int
    query: str


class SearchDiscussionSuccessfulResponseDiscussion(BaseModel):
    id: uuid.UUID
    user: UserSchema
    title: str
    type: DiscussionsTypeEnum
    category: DiscussionsCategoryEnum
    sub_category: str
    status: DiscussionsStatusEnum
    created_at: datetime
    updated_at: datetime
    votes: int = 0
    is_bookmarked: bool = False
    is_pinned: bool = False

    model_config = {"from_attributes": True}


class SearchDiscussionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Search completed successfully"]
    data: List[SearchDiscussionSuccessfulResponseDiscussion]
    meta: SearchSuccessfulMeta


class SearchDiscussionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while searching discussions for the provided query. Please contact developers if the issue persists."
        ],
    ]


class SearchDiscussionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to search discussions"]
    error: SearchDiscussionBackendError


SEARCH_DISCUSSIONS_RESPONSE_MODEL = {
    200: {"model": SearchDiscussionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": SearchDiscussionBackendErrorResponse},
}


class SearchTagSuccessfulResponse(SuccessfulResponse):
    message: Literal["Search completed successfully"]
    data: List[TagSchema]
    meta: SearchSuccessfulMeta


class SearchTagBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while searching tags for the provided query. Please contact developers if the issue persists."
        ],
    ]


class SearchTagBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to search tags"]
    error: SearchTagBackendError


SEARCH_TAGS_RESPONSE_MODEL = {
    200: {"model": SearchTagSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": SearchTagBackendErrorResponse},
}


class SearchAuthorSuccessfulResponse(SuccessfulResponse):
    message: Literal["Search completed successfully"]
    data: List[UserSchema]
    meta: SearchSuccessfulMeta


class SearchAuthorBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while searching authors for the provided query. Please contact developers if the issue persists."
        ],
    ]


class SearchAuthorBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to search authors"]
    error: SearchAuthorBackendError


SEARCH_AUTHORS_RESPONSE_MODEL = {
    200: {"model": SearchAuthorSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": SearchAuthorBackendErrorResponse},
}
