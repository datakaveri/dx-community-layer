import json
import uuid
from typing import Optional
from fastapi import Path, Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError

from .discussion_requests import RetrieveDiscussionChoices, RetrieveDiscussionsSortByEnum
from ...database.discussion.enums import DiscussionsTypeEnum
from ...middlewares.search_validation import validate_search_query


class SearchDiscussionsFilters(BaseModel):
    sub_category_id: Optional[uuid.UUID] = Field(
        default=None, description="Sub-category ID of the discussion to retrieve"
    )
    type: Optional[DiscussionsTypeEnum] = Field(
        default=None, description="Discussion type filter (PUBLIC, GENERAL, etc.)"
    )


class SearchDiscussionsParams:
    def __init__(
        self,
        choice: RetrieveDiscussionChoices = Path(
            ...,
            description="Type of the discussion to retrieve (all, owned or bookmarked)",
        ),
        query: str = Query(..., description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of discussions per page"),
        filters: Optional[str] = Query(
            default=None,
            description=(
                "JSON string of filters to apply to the search.<br>"
                "The keys can be 'sub_category_id' and 'type'.<br>"
                "Each key should map to a UUID or null.<br>"
                "type should be one of: PUBLIC, GENERAL, GETTING_STARTED, PRODUCT_FEEDBACK, PRODUCT_ANNOUNCEMENTS.<br>"
            ),
            example=json.dumps(
                {
                    "sub_category_id": "00000000-0000-0000-0000-000000000000",
                    "type": "PUBLIC",
                }
            ),
        ),
        sort_by: RetrieveDiscussionsSortByEnum = Query(
            default=RetrieveDiscussionsSortByEnum.NEWEST,
            description="The field to sort by",
        ),
    ):
        validate_search_query(query)
        self.choice = choice
        self.query = query
        self.page = page
        self.limit = limit

        # Parse the filters string into a dictionary
        try:
            self.filters: SearchDiscussionsFilters = (
                SearchDiscussionsFilters.model_validate_json(filters)
                if filters
                else SearchDiscussionsFilters()
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


class SearchPinnedDiscussionsParams:
    def __init__(
        self,
        choice: RetrieveDiscussionChoices = Path(
            ...,
            description="Type of the discussion to retrieve (all, owned or bookmarked)",
        ),
        query: str = Query(..., description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of discussions per page"),
        filters: Optional[str] = Query(
            default=None,
            description=(
                "JSON string of filters to apply to the search.<br>"
                "The keys can be 'sub_category_id' and 'type'.<br>"
                "Each key should map to a UUID or null.<br>"
                "type should be one of: PUBLIC, GENERAL, GETTING_STARTED, PRODUCT_FEEDBACK, PRODUCT_ANNOUNCEMENTS.<br>"
            ),
            example=json.dumps(
                {
                    "sub_category_id": "00000000-0000-0000-0000-000000000000",
                    "type": "PUBLIC",
                }
            ),
        ),
        sort_by: RetrieveDiscussionsSortByEnum = Query(
            default=RetrieveDiscussionsSortByEnum.NEWEST,
            description="The field to sort by",
        ),
    ):
        validate_search_query(query)
        self.choice = choice
        self.query = query
        self.page = page
        self.limit = limit

        # Parse the filters string into a dictionary
        try:
            self.filters: SearchDiscussionsFilters = (
                SearchDiscussionsFilters.model_validate_json(filters)
                if filters
                else SearchDiscussionsFilters()
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


class SearchParams:
    def __init__(
        self,
        query: str = Query(..., description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of discussions per page"),
    ):
        validate_search_query(query)
        self.query = query
        self.page = page
        self.limit = limit
