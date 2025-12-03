from datetime import datetime
import uuid
from typing import List, Literal, Optional, Union, Any, Dict
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel

from ...database.discussion.enums import (
    DiscussionsTypeEnum,
    DiscussionsCategoryEnum,
    DiscussionsStatusEnum,
)
from ..default_schemas import (
    BackendErrorResponse,
    CreatedResponse,
    BadRequestErrorResponse,
    ForbiddenErrorResponse,
    SuccessfulResponse,
    UnauthorizedErrorResponse,
    ConflictErrorResponse,
    ValidationErrorResponse,
    NotFoundErrorResponse,
)


class PaginatedResponseMeta(BaseModel):
    total_count: int
    total_pages: int
    current_page: int
    limit: int


class UserSchema(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class TagSchema(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class RetrieveDiscussionsResponseDiscussionTags(BaseModel):
    id: uuid.UUID
    tag: TagSchema

    model_config = {"from_attributes": True}


class RetrieveDiscussionsResponseDiscussionAttachments(BaseModel):
    id: uuid.UUID
    attachment_metadata: Dict[str, Any]
    s3_key: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DiscussionReactionsSummary(BaseModel):
    emojis: Dict[str, int]
    user_reaction: Dict[str, str]

    model_config = {"from_attributes": True}


class RetrieveDiscussionsResponseDiscussion(BaseModel):
    id: uuid.UUID
    user: UserSchema
    title: str
    type: DiscussionsTypeEnum
    category: DiscussionsCategoryEnum
    sub_category: str
    sub_category_id: Optional[uuid.UUID]
    status: DiscussionsStatusEnum
    created_at: datetime
    updated_at: datetime
    votes: int = 0
    is_bookmarked: bool = False
    is_pinned: bool = False
    is_voted: bool = False

    model_config = {"from_attributes": True}


class RetrieveDiscussionByIDResponseDiscussionReview(BaseModel):
    id: uuid.UUID
    discussion_id: uuid.UUID
    reviewer: UserSchema
    comment: Optional[str]
    updated_status: DiscussionsStatusEnum
    created_at: datetime

    model_config = {"from_attributes": True}


class RetrieveDiscussionByIDResponseDiscussion(BaseModel):
    id: uuid.UUID
    user: UserSchema
    title: str
    type: DiscussionsTypeEnum
    category: DiscussionsCategoryEnum
    sub_category: str
    sub_category_id: Optional[uuid.UUID]
    content: str
    status: DiscussionsStatusEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime
    discussion_tags: List[RetrieveDiscussionsResponseDiscussionTags]
    discussion_attachments: List[RetrieveDiscussionsResponseDiscussionAttachments]
    reactions: Optional[DiscussionReactionsSummary] = None
    votes: int = 0
    is_bookmarked: bool = False
    is_pinned: bool = False
    is_voted: bool = False
    discussion_reviews: List[RetrieveDiscussionByIDResponseDiscussionReview]

    model_config = {"from_attributes": True}


class RetrieveDiscussionByIDSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussion retrieved successfully"]
    data: RetrieveDiscussionByIDResponseDiscussion
    meta: PaginatedResponseMeta


class RetrieveDiscussionByIDForbiddenError(BaseModel):
    code: Literal["FORBIDDEN"]
    details: Literal[
        "You do not have permission to view this discussion. Please contact developers if the issue persists."
    ]


class RetrieveDiscussionByIDForbiddenErrorResponse(ForbiddenErrorResponse):
    message: Literal["Forbidden access"]
    error: RetrieveDiscussionByIDForbiddenError


class RetrieveDiscussionByIDNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The discussion does not exist. Please contact developers if the issue persists."
    ]


class RetrieveDiscussionByIDNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Discussion not found"]
    error: RetrieveDiscussionByIDNotFoundError


class RetrieveDiscussionByIDBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "An error occurred while retrieving the discussion. Please contact developers if the issue persists."
    ]


class RetrieveDiscussionByIDBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion retrieval failed"]
    error: RetrieveDiscussionByIDBackendError


RETRIEVE_DISCUSSION_BY_ID_RESPONSE_MODEL = {
    200: {"model": RetrieveDiscussionByIDSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": RetrieveDiscussionByIDForbiddenErrorResponse},
    404: {"model": RetrieveDiscussionByIDNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": RetrieveDiscussionByIDBackendErrorResponse},
}


class RetrieveDiscussionsResponseData(BaseModel):
    discussions: List[RetrieveDiscussionsResponseDiscussion]
    pinned_discussions: List[RetrieveDiscussionsResponseDiscussion]


class RetrieveDiscussionsResponseMeta(BaseModel):
    total_count: int
    total_pages: int
    current_page: int
    limit: int


class RetrieveDiscussionsSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussions retrieved successfully"]
    data: RetrieveDiscussionsResponseData
    meta: RetrieveDiscussionsResponseMeta


class RetrieveDiscussionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while retrieving discussions. Please contact developers if the issue persists."
        ],
    ]


class RetrieveDiscussionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to retrieve discussions"]
    error: RetrieveDiscussionBackendError


RETRIEVE_DISCUSSION_RESPONSE_MODEL = {
    200: {"model": RetrieveDiscussionsSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": RetrieveDiscussionBackendErrorResponse},
}


class CreateDiscussionCreatedData(BaseModel):
    discussion_id: uuid.UUID


class CreateDiscussionCreatedResponse(CreatedResponse):
    message: Literal["Discussion created successfully"]
    data: CreateDiscussionCreatedData


class CreateDiscussionConflictError(BaseModel):
    code: Literal["CONFLICT"]
    details: Literal[
        (
            "A discussion with the same title, type, category, and sub-category already exists. "
            "Please use a different title, type, category, or sub-category."
        )
    ]


class CreateDiscussionConflictErrorResponse(ConflictErrorResponse):
    message: Literal["Discussion already exists"]
    error: CreateDiscussionConflictError


class CreateDiscussionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while creating the discussion. Please contact developers if the issue persists."
        ],
    ]


class CreateDiscussionBackendErrorResponse(BackendErrorResponse):
    message: Union[
        Literal["User authorization failed"], Literal["Discussion creation failed"]
    ]
    error: CreateDiscussionBackendError


CREATE_DISCUSSION_RESPONSE_MODEL = {
    201: {"model": CreateDiscussionCreatedResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    409: {"model": ConflictErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": CreateDiscussionBackendErrorResponse},
}


class UpdateDiscussionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussion updated successfully"]


class UpdateDiscussionForbiddenError(BaseModel):
    code: Literal["FORBIDDEN"]
    details: Literal[
        "You do not have permission to update this discussion. Please contact developers if the issue persists."
    ]


class UpdateDiscussionForbiddenErrorResponse(ForbiddenErrorResponse):
    message: Literal["Forbidden access"]
    error: UpdateDiscussionForbiddenError


class UpdateDiscussionNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The discussion does not exist. Please contact developers if the issue persists."
    ]


class UpdateDiscussionNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Discussion not found"]
    error: UpdateDiscussionNotFoundError


class UpdateDiscussionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "An error occurred while updating the discussion. Please contact developers if the issue persists."
    ]


class UpdateDiscussionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion update failed"]
    error: UpdateDiscussionBackendError


UPDATE_DISCUSSION_RESPONSE_MODEL = {
    200: {"model": UpdateDiscussionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": UpdateDiscussionForbiddenErrorResponse},
    404: {"model": UpdateDiscussionNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": UpdateDiscussionBackendErrorResponse},
}


class DiscussionActionsSuccessfulResponse(SuccessfulResponse):
    message: Union[
        Literal["Discussion bookmarked successfully"],
        Literal["Discussion pinned successfully"],
        Literal["Discussion unbookmarked successfully"],
        Literal["Discussion unpinned successfully"],
    ]


class DiscussionActionsNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Union[
        Literal[
            "The discussion you are trying to perform an action does not exist. Please try again later or contact support if the issue persists."
        ],
        Literal[
            "The discussion is not bookmarked. Please try again later or contact support if the issue persists."
        ],
        Literal[
            "The discussion is not pinned. Please try again later or contact support if the issue persists."
        ],
    ]


class DiscussionActionsNotFoundErrorResponse(NotFoundErrorResponse):
    message: Union[
        Literal["Discussion not found"],
        Literal["Bookmark not found"],
        Literal["Pin not found"],
    ]
    error: DiscussionActionsNotFoundError


class DiscussionActionsConflictError(BaseModel):
    code: Literal["CONFLICT"]
    details: Union[
        Literal[
            "The discussion has already been bookmarked. Please try again later or contact support if the issue persists."
        ],
        Literal[
            "The discussion has already been pinned. Please try again later or contact support if the issue persists."
        ],
    ]


class DiscussionActionsConflictErrorResponse(ConflictErrorResponse):
    message: Union[
        Literal["Discussion already bookmarked"],
        Literal["Discussion already pinned"],
    ]
    error: DiscussionActionsConflictError


class DiscussionActionsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while performing the discussion action. Please contact developers if the issue persists."
        ],
    ]


class DiscussionActionsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion action failed"]
    error: DiscussionActionsBackendError


DISCUSSION_ACTIONS_RESPONSE_MODEL = {
    200: {"model": DiscussionActionsSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": DiscussionActionsNotFoundErrorResponse},
    409: {"model": DiscussionActionsConflictErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": DiscussionActionsBackendErrorResponse},
}


class AddUpdateDiscussionReactionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Reaction added/updated successfully"]


class DiscussionNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The discussion does not exist. Please contact developers if the issue persists."
    ]


class AddUpdateDiscussionReactionNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Discussion not found"]
    error: DiscussionNotFoundError


class AddUpdateDiscussionReactionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while adding/updating the discussion reaction. Please contact developers if the issue persists."
        ],
    ]


class AddUpdateDiscussionReactionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion reaction failed"]
    error: AddUpdateDiscussionReactionBackendError


ADD_UPDATE_DISCUSSION_REACTION_RESPONSE_MODEL = {
    200: {"model": AddUpdateDiscussionReactionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": AddUpdateDiscussionReactionNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": AddUpdateDiscussionReactionBackendErrorResponse},
}


class DeleteDiscussionReactionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Reaction deleted successfully"]


class DeleteDiscussionReactionNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The discussion reaction does not exist. Please contact developers if the issue persists."
    ]


class DeleteDiscussionReactionNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Reaction not found"]
    error: DeleteDiscussionReactionNotFoundError


class DeleteDiscussionReactionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while deleting the discussion reaction. Please contact developers if the issue persists."
        ],
    ]


class DeleteDiscussionReactionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion reaction failed"]
    error: DeleteDiscussionReactionBackendError


DELETE_DISCUSSION_REACTION_RESPONSE_MODEL = {
    200: {"model": DeleteDiscussionReactionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": DeleteDiscussionReactionNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": DeleteDiscussionReactionBackendErrorResponse},
}


class AddDiscussionVoteSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussion vote added successfully"]


class AddDiscussionVoteNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Discussion not found"]
    error: DiscussionNotFoundError


class AddDiscussionVoteConflictError(BaseModel):
    code: Literal["CONFLICT"]
    details: Literal[
        "You have already voted for this discussion. Please try again later or contact support if the issue persists."
    ]


class AddDiscussionVoteConflictErrorResponse(ConflictErrorResponse):
    message: Literal["Discussion already voted"]
    error: AddDiscussionVoteConflictError


class AddDiscussionVoteBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while adding the discussion vote. Please contact developers if the issue persists."
        ],
    ]


class AddDiscussionVoteBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion vote failed"]
    error: AddDiscussionVoteBackendError


ADD_DISCUSSION_VOTE_RESPONSE_MODEL = {
    200: {"model": AddDiscussionVoteSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": AddDiscussionVoteNotFoundErrorResponse},
    409: {"model": AddDiscussionVoteConflictErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": AddDiscussionVoteBackendErrorResponse},
}


class DeleteDiscussionVoteSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussion vote deleted successfully"]


class DiscussionVoteNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The discussion vote does not exist. Please contact developers if the issue persists."
    ]


class DeleteDiscussionVoteNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Discussion not found"]
    error: DiscussionVoteNotFoundError


class DeleteDiscussionVoteBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while deleting the discussion vote. Please contact developers if the issue persists."
        ],
    ]


class DeleteDiscussionVoteBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to delete discussion vote"]
    error: DeleteDiscussionVoteBackendError


DELETE_DISCUSSION_VOTE_RESPONSE_MODEL = {
    200: {"model": DeleteDiscussionVoteSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": DeleteDiscussionVoteNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": DeleteDiscussionVoteBackendErrorResponse},
}


class DeleteDiscussionSuccessfulResponse(SuccessfulResponse):
    message: Literal["Discussion deleted successfully"]


class DeleteDiscussionForbiddenError(BaseModel):
    code: Literal["FORBIDDEN"]
    details: Literal[
        "You are not authorized to delete this discussion. Please contact developers if the issue persists."
    ]


class DeleteDiscussionForbiddenErrorResponse(ForbiddenErrorResponse):
    message: Literal["Forbidden access"]
    error: DeleteDiscussionForbiddenError


class DeleteDiscussionNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The discussion does not exist. Please contact developers if the issue persists."
    ]


class DeleteDiscussionNotFoundErrorResponse(NotFoundErrorResponse):
    message: Literal["Discussion not found"]
    error: DeleteDiscussionNotFoundError


class DeleteDiscussionBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while deleting the discussion. Please contact developers if the issue persists."
        ],
    ]


class DeleteDiscussionBackendErrorResponse(BackendErrorResponse):
    message: Literal["Discussion deletion failed"]
    error: DeleteDiscussionBackendError


DELETE_DISCUSSION_RESPONSE_MODEL = {
    200: {"model": DeleteDiscussionSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": DeleteDiscussionForbiddenErrorResponse},
    404: {"model": DeleteDiscussionNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": DeleteDiscussionBackendErrorResponse},
}


class PopularTagsResponseData(BaseModel):
    tags: List[str]


class PopularTagsSuccessfulResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    data: PopularTagsResponseData
    meta: Optional[Dict[str, Any]] = None


class RecentDiscussionsResponseData(BaseModel):
    discussions: List[RetrieveDiscussionsResponseDiscussion]


class RecentDiscussionsSuccessfulResponse(SuccessfulResponse):
    message: Literal["Recent discussions retrieved successfully"]
    data: RecentDiscussionsResponseData


class RecentDiscussionsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "An error occurred while retrieving recent discussions. Please contact developers if the issue persists."
    ]


class RecentDiscussionsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to retrieve recent discussions"]
    error: RecentDiscussionsBackendError


RECENT_DISCUSSIONS_RESPONSE_MODEL = {
    200: {"model": RecentDiscussionsSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": RecentDiscussionsBackendErrorResponse},
}


class GetPopularTagsSuccessfulResponseData(TagSchema):
    count: int


class GetPopularTagsSuccessfullResponse(SuccessfulResponse):
    message: Literal["Popular tags retrieved successfully"]
    data: List[GetPopularTagsSuccessfulResponseData]


class GetPopularTagsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "An error occurred while retrieving popular tags. Please contact developers if the issue persists."
    ]


class GetPopularTagsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to retrieve popular tags"]
    error: GetPopularTagsBackendError


GET_POPULAR_TAGS_RESPONSE_MODEL = {
    200: {"model": GetPopularTagsSuccessfullResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": GetPopularTagsBackendErrorResponse},
}


class RecentAuthorsSuccessfulResponse(SuccessfulResponse):
    message: Literal["Recent discussion authors retrieved successfully"]
    data: List[UserSchema]


class RecentAuthorsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "An error occurred while retrieving recent discussion authors. Please contact developers if the issue persists."
    ]


class RecentAuthorsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to retrieve recent discussion authors"]
    error: RecentAuthorsBackendError


RECENT_AUTHORS_RESPONSE_MODEL = {
    200: {"model": RecentAuthorsSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": RecentAuthorsBackendErrorResponse},
}
