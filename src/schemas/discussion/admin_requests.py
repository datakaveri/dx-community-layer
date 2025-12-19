from datetime import datetime, date
import pytz
import enum
import json
import uuid
from typing import Literal, Optional
from fastapi import Body, Path, Query
from pydantic import BaseModel, Field, ValidationError
from fastapi.exceptions import RequestValidationError

from .discussion_requests import RetrieveDiscussionsFilters
from ...database.discussion.enums import DiscussionsStatusEnum, DiscussionsTypeEnum


class TimeRangeFilter(BaseModel):
    start_date: str = Field(
        ...,
        description="Start date of the time range to filter by",
    )
    end_date: str = Field(
        ...,
        description="End date of the time range to filter by",
    )


class AdminRetrieveDiscussionsFilters(RetrieveDiscussionsFilters):
    time_range: Optional[TimeRangeFilter] = Field(
        default=None, description="Time range to filter by"
    )


class AdminRetrieveDiscussionsChoices(enum.Enum):
    ALL = "all"
    REVIEW_HISTORY = "review_history"


class AdminRetrieveDiscussionsSortByEnum(enum.Enum):
    created_at = "created_at"
    updated_at = "updated_at"


class AdminRetrieveDiscussionParams:
    DATE_FORMAT = "%Y-%m-%d"

    def __init__(
        self,
        choice: AdminRetrieveDiscussionsChoices = Path(
            ...,
            description="Choice of the discussion to retrieve",
        ),
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of discussions per page"),
        filters: Optional[str] = Query(
            default=None,
            description=(
                "JSON string of filters to apply to the analysis.<br>"
                "The keys can be 'type'.<br>"
                "Each key should map to a list of strings, boolean or null.<br>"
                "Optional 'time_range': {'start_date': 'YYYY-MM-DD', 'end_date': 'YYYY-MM-DD'}<br>"
            ),
            example=json.dumps(
                {
                    "type": [DiscussionsTypeEnum.GENERAL.value],
                    "status": [DiscussionsStatusEnum.PENDING.value],
                    "tags": ["tag1", "tag2"],
                    "time_range": {
                        "start_date": "2023-01-01",
                        "end_date": "2023-01-31",
                    },
                }
            ),
        ),
        sort_by: Optional[AdminRetrieveDiscussionsSortByEnum] = Query(
            default=None,
            description="The field to sort by",
        ),
        sort_order: Optional[Literal["asc", "desc"]] = Query(
            default=None,
            description="The order to sort by",
        ),
    ):
        self.choice = choice
        self.query = query
        self.page = page
        self.limit = limit

        # Parse the filters string into a dictionary
        try:
            self.filters: AdminRetrieveDiscussionsFilters = (
                AdminRetrieveDiscussionsFilters.model_validate_json(filters)
                if filters
                else AdminRetrieveDiscussionsFilters()
            )
        except (json.JSONDecodeError, ValidationError):
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

        # Validate the time range
        if self.filters.time_range:
            try:
                if self.filters.time_range.start_date:
                    datetime.strptime(
                        self.filters.time_range.start_date, self.DATE_FORMAT
                    ).astimezone(pytz.UTC).date()
            except ValueError:
                raise RequestValidationError(
                    [
                        {
                            "loc": ["query", "filters", "time_range", "start_date"],
                            "msg": "Invalid date format for start_date",
                            "type": "value_error",
                            "input": self.filters.time_range.start_date,
                        }
                    ]
                )

            try:
                if self.filters.time_range.end_date:
                    datetime.strptime(
                        self.filters.time_range.end_date, self.DATE_FORMAT
                    ).astimezone(pytz.UTC).date()
            except ValueError:
                raise RequestValidationError(
                    [
                        {
                            "loc": ["query", "filters", "time_range", "end_date"],
                            "msg": "Invalid date format for end_date",
                            "type": "value_error",
                            "input": self.filters.time_range.end_date,
                        }
                    ]
                )

        self.sort_by = sort_by
        self.sort_order = sort_order


class ReviewDiscussionStatusEnum(enum.Enum):
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AdminReviewDiscussionParams:
    def __init__(
        self,
        discussion_id: uuid.UUID = Path(
            ..., description="ID of the discussion to review"
        ),
        review_status: ReviewDiscussionStatusEnum = Body(
            ...,
            description="Review status of the discussion",
        ),
        comment: Optional[str] = Body(
            default=None,
            description="Comment to add to the discussion",
        ),
    ):
        self.discussion_id = discussion_id
        self.review_status = review_status
        self.comment = comment

        if self.review_status in [
            DiscussionsStatusEnum.CHANGES_REQUIRED,
            DiscussionsStatusEnum.REJECTED,
        ]:
            if not comment:
                raise RequestValidationError(
                    [
                        {
                            "loc": ["body", "comment"],
                            "msg": "Comment is required for changing the status to 'Changes Required' or 'Rejected'",
                            "type": "value_error",
                            "input": comment,
                        }
                    ]
                )


class AdminRetrievePendingCommentsParams:
    def __init__(
        self,
        page: int = Query(1, gt=0, description="Page number"),
        limit: int = Query(10, gt=0, description="Items per page"),
        sort_by: Literal["discussion_title", "created_at"] = Query(
            "created_at",
            description="Sort field",
        ),
        sort_order: Literal["asc", "desc"] = Query(
            "desc",
            description="Sort order",
        ),
    ):
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order


class AdminReviewCommentParams:
    def __init__(
        self,
        comment_id: uuid.UUID = Path(..., description="ID of the comment to review"),
        status: Literal["APPROVED", "REJECTED"] = Body(
            ..., description="Review status of the comment"
        ),
        comment: Optional[str] = Body(
            default=None,
            description="Admin comment (required if status is REJECTED)",
        ),
    ):
        self.comment_id = comment_id
        self.status = status
        self.comment = comment

        if self.status == "REJECTED" and not comment:
            raise RequestValidationError(
                [
                    {
                        "loc": ["body", "comment"],
                        "msg": "Comment is required when rejecting a comment",
                        "type": "value_error",
                        "input": comment,
                    }
                ]
            )
