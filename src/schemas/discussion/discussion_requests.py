import enum
import json
import uuid
from typing import List, Optional
from fastapi import Body, Path, Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError

from ...database.discussion.enums import (
    DiscussionsCategoryEnum,
    DiscussionsStatusEnum,
    DiscussionsTypeEnum,
)


class RetrieveDiscussionChoices(enum.Enum):
    ALL = "all"
    OWNED = "owned"
    BOOKMARKED = "bookmarked"


class RetrieveDiscussionsFilters(BaseModel):
    type: Optional[List[DiscussionsTypeEnum]] = Field(
        default=None, description="Type of the discussion to retrieve"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="Tags associated with the discussion"
    )
    status: Optional[List[DiscussionsStatusEnum]] = Field(
        default=None, description="Status of the discussion to retrieve"
    )
    sub_category_id: Optional[uuid.UUID] = Field(
        default=None, description="Sub-category ID of the discussion to retrieve"
    )


class RetrieveDiscussionsSortByEnum(enum.Enum):
    HOTTEST = "hottest"
    NEWEST = "newest"
    OLDEST = "oldest"


class RetrieveDiscussionParams:
    def __init__(
        self,
        choice: RetrieveDiscussionChoices = Path(
            ...,
            description="Type of the discussion to retrieve",
        ),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of discussions per page"),
        filters: Optional[str] = Query(
            default=None,
            description=(
                "JSON string of filters to apply to the analysis.<br>"
                "The keys can be 'type', 'status', 'tags', 'sub_category_id'.<br>"
                "Each key should map to a list of strings, boolean, UUID or null.<br>"
            ),
            example=json.dumps(
                {
                    "type": [DiscussionsTypeEnum.PUBLIC.value],
                    "status": [DiscussionsStatusEnum.PENDING.value],
                    "tags": ["tag1", "tag2"],
                    "sub_category_id": "00000000-0000-0000-0000-000000000000",
                }
            ),
        ),
        sort_by: RetrieveDiscussionsSortByEnum = Query(
            default=RetrieveDiscussionsSortByEnum.NEWEST,
            description="The field to sort by",
        ),
        pinned: bool = Query(
            default=False,
            description="Whether to retrieve pinned discussions seperately or not",
        ),
    ):
        self.choice = choice
        self.page = page
        self.limit = limit

        # Parse the filters string into a dictionary
        try:
            self.filters: RetrieveDiscussionsFilters = (
                RetrieveDiscussionsFilters.model_validate_json(filters)
                if filters
                else RetrieveDiscussionsFilters()
            )
        except (json.JSONDecodeError, ValidationError) as e:
            raise RequestValidationError(
                [
                    {
                        "loc": ["query", "filters"],
                        "msg": "Invalid JSON format for filters",
                        "type": "value_error.json",
                        "input": filters,
                    }
                ]
            )

        self.sort_by = sort_by
        self.pinned = pinned


class RetrievePinnedDiscussionParams:
    def __init__(
        self,
        choice: RetrieveDiscussionChoices = Path(
            ...,
            description="Type of the discussion to retrieve",
        ),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of discussions per page"),
        filters: Optional[str] = Query(
            default=None,
            description=(
                "JSON string of filters to apply to the analysis.<br>"
                "The keys can be 'type', 'status', 'tags', 'sub_category_id'.<br>"
                "Each key should map to a list of strings, boolean, UUID or null.<br>"
            ),
            example=json.dumps(
                {
                    "type": [DiscussionsTypeEnum.PUBLIC.value],
                    "status": [DiscussionsStatusEnum.PENDING.value],
                    "tags": ["tag1", "tag2"],
                    "sub_category_id": "00000000-0000-0000-0000-000000000000",
                }
            ),
        ),
        sort_by: RetrieveDiscussionsSortByEnum = Query(
            default=RetrieveDiscussionsSortByEnum.NEWEST,
            description="The field to sort by",
        ),
    ):
        self.choice = choice
        self.page = page
        self.limit = limit

        # Parse the filters string into a dictionary
        try:
            self.filters: RetrieveDiscussionsFilters = (
                RetrieveDiscussionsFilters.model_validate_json(filters)
                if filters
                else RetrieveDiscussionsFilters()
            )
        except (json.JSONDecodeError, ValidationError) as e:
            raise RequestValidationError(
                [
                    {
                        "loc": ["query", "filters"],
                        "msg": "Invalid JSON format for filters",
                        "type": "value_error.json",
                        "input": filters,
                    }
                ]
            )

        self.sort_by = sort_by



class CreateDiscussionParams:
    def __init__(
        self,
        title: str = Body(
            ...,
            description="Title of the discussion",
            min_length=1,
            max_length=255,
        ),
        type: DiscussionsTypeEnum = Body(
            default=DiscussionsTypeEnum.PUBLIC, description="Type of the discussion"
        ),
        category: DiscussionsCategoryEnum = Body(
            default=DiscussionsCategoryEnum.OTHERS,
            description="Category of the discussion",
        ),
        sub_category: str = Body(
            ...,
            description="Sub-category of the discussion",
            min_length=1,
            max_length=255,
        ),
        sub_category_id: Optional[uuid.UUID] = Body(
            default=None,
            description="ID of the sub-category of the discussion",
        ),
        content: str = Body(
            ...,
            description="Content of the discussion",
            min_length=1,
        ),
        tags: Optional[List[str]] = Body(
            default=None,
            description="Tags associated with the discussion",
            max_length=10,
        ),
        attachments: Optional[List[str]] = Body(
            default=None,
            description="Attachments associated with the discussion",
            max_length=10,
        ),
    ):
        self.title = title.strip()
        self.type = type
        self.category = category
        self.sub_category = sub_category.strip()
        self.sub_category_id = sub_category_id

        if (
            self.category
            in [
                DiscussionsCategoryEnum.AI_MODELS,
                DiscussionsCategoryEnum.DATA_BANKS,
                DiscussionsCategoryEnum.USECASES,
            ]
            and not self.sub_category_id
        ):
            raise RequestValidationError(
                [
                    {
                        "loc": ["body", "sub_category_id"],
                        "msg": "sub_category_id is required for AI_MODELS, DATA_BANKS and USECASES category",
                        "type": "value_error",
                    }
                ]
            )

        self.content = content.strip()
        self.tags = [tag.strip() for tag in tags] if tags else None
        self.attachments = attachments


class UpdateDiscussionTags(BaseModel):
    add: Optional[List[str]] = None
    remove: Optional[List[str]] = None


class UpdateDiscussionParams:
    def __init__(
        self,
        discussion_id: uuid.UUID = Path(
            ..., description="ID of the discussion to update"
        ),
        title: Optional[str] = Body(
            default=None,
            description="New title for the discussion",
            min_length=1,
            max_length=255,
        ),
        category: Optional[DiscussionsCategoryEnum] = Body(
            default=None,
            description="New category for the discussion",
        ),
        sub_category: Optional[str] = Body(
            default=None,
            description="New sub-category for the discussion",
            min_length=1,
            max_length=255,
        ),
        sub_category_id: Optional[uuid.UUID] = Body(
            default=None,
            description="New ID of the sub-category for the discussion",
        ),
        content: Optional[str] = Body(
            default=None,
            description="New content for the discussion",
            min_length=1,
        ),
        tags: UpdateDiscussionTags = Body(
            default=None,
            description=(
                "Object with 'add' and 'remove' lists.\n"
                "- add: create tags if missing and link them to the discussion.\n"
                "- remove: unlink tags from the discussion if currently linked (skips missing)."
            ),
        ),
        added_attachments: Optional[List[str]] = Body(
            default=None,
            description="List of object keys of attachments to add to the discussion",
        ),
    ):
        self.discussion_id = discussion_id
        self.title = title.strip() if title else None
        self.category = category
        self.sub_category = sub_category.strip() if sub_category else None
        self.sub_category_id = sub_category_id

        if (
            self.category
            in [
                DiscussionsCategoryEnum.AI_MODELS,
                DiscussionsCategoryEnum.DATA_BANKS,
                DiscussionsCategoryEnum.USECASES,
            ]
            and not self.sub_category_id
        ):
            raise RequestValidationError(
                [
                    {
                        "loc": ["body", "sub_category_id"],
                        "msg": "sub_category_id is required for AI_MODELS, DATA_BANKS and USECASES category",
                        "type": "value_error",
                    }
                ]
            )

        self.content = content.strip() if content else None
        self.tags = tags
        self.added_attachments = added_attachments


class DiscussionActions(enum.Enum):
    BOOKMARK = "bookmark"
    UNBOOKMARK = "unbookmark"
    PIN = "pin"
    UNPIN = "unpin"


class DiscussionActionsParams:
    def __init__(
        self,
        discussion_id: uuid.UUID = Path(
            ..., description="ID of the discussion to perform action on"
        ),
        action: DiscussionActions = Path(
            ..., description="Action to perform on the discussion"
        ),
    ):
        self.discussion_id = discussion_id
        self.action = action


class AddUpdateDiscussionReactionParams:
    def __init__(
        self,
        discussion_id: uuid.UUID = Path(
            ..., description="ID of the discussion to add/update reaction to"
        ),
        emoji_code: Optional[str] = Body(
            default=None,
            description="Emoji code to add/update",
        ),
        temp: Optional[bool] = Body(
            default=False,
            description="Whether to add a temporary reaction or not",
        ),
    ):
        self.discussion_id = discussion_id
        self.emoji_code = emoji_code
