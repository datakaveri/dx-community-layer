import enum
import uuid
from fastapi import Body, Path, Query
from typing import Any, Optional
from pydantic import BaseModel, Field


class RetrieveUserSubmissionsChoice(enum.Enum):
    SUBMITTED = "submitted"
    EVALUATION = "evaluation"
    COMPLETED = "completed"


class RetrieveUserSubmissionsSortByEnum(enum.Enum):
    COMPETITION_TITLE = "competition_title"
    TITLE = "title"
    DESCRIPTION = "description"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    EVALUATION_ENDS_AT = "evaluation_ends_at"


class SortOrder(enum.Enum):
    ASC = "asc"
    DESC = "desc"


class RetrieveUserSubmissionsParams:
    def __init__(
        self,
        choice: RetrieveUserSubmissionsChoice = Path(
            ..., description="Type of the submission to retrieve"
        ),
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of submissions per page"),
        sort_by: Optional[RetrieveUserSubmissionsSortByEnum] = Query(
            default=None,
            description="The field to sort by",
        ),
        sort_order: Optional[SortOrder] = Query(
            default=None,
            description="The order to sort by",
        ),
    ):
        self.choice = choice
        self.query = query
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.score = None

        if self.query:
            score = None
            try:
                score = float(self.query)
            except ValueError:
                pass

            if 0 <= score <= 100:
                self.score = score


class CreateSubmissionRequest(BaseModel):
    title: str = Field(..., max_length=300, description="Title for the submission")
    description: str = Field(..., description="Detailed explanation of the submission")
    attachments: Optional[list[str]] = Field(
        default=None,
        description="Optional attachment metadata (e.g., S3 keys, urls)",
    )


class PublishSubmissionParams:
    def __init__(
        self,
        submission_id: uuid.UUID = Path(
            ..., description="ID of the submission to publish"
        ),
        score: float = Body(
            ...,
            description="Score for the submission",
        ),
        comments: str = Body(
            ...,
            description="Comments for the submission",
        ),
        attachments: Optional[list[str]] = Body(
            default=None,
            description="Optional attachment metadata (S3 keys)",
        ),
    ):
        self.submission_id = submission_id
        self.score = score
        self.comments = comments
        self.attachments = attachments


class UpdateSubmissionAttachment(BaseModel):
    add: Optional[list[str]] = Field(
        default=None,
        description="Optional attachment metadata (S3 keys)",
    )
    remove: Optional[list[str]] = Field(
        default=None,
        description="Optional attachment metadata (S3 keys)",
    )


class UpdateSubmissionParams:
    def __init__(
        self,
        submission_id: uuid.UUID = Path(
            ..., description="ID of the submission to update"
        ),
        title: Optional[str] = Body(
            default=None, max_length=300, description="Title for the submission"
        ),
        description: Optional[str] = Body(
            default=None, description="Detailed explanation of the submission"
        ),
        attachments: Optional[UpdateSubmissionAttachment] = Body(
            ..., description="Attachments to add or remove"
        ),
    ):
        self.submission_id = submission_id
        self.title = title.strip()
        self.description = description.strip()
        self.attachments = attachments


class AdminEditSubmissionParams:
    def __init__(
        self,
        submission_id: uuid.UUID = Path(
            ...,
            description="ID of the submission to update evaluation for",
        ),
        score: Optional[float] = Body(
            default=None,
            description="Updated score for the submission (optional)",
        ),
        comments: Optional[str] = Body(
            default=None,
            description="Updated evaluation comments (optional)",
        ),
        is_disqualified: Optional[bool] = Body(
            default=None,
            description="Updated disqualification flag (optional)",
        ),
        attachments: Optional[UpdateSubmissionAttachment] = Body(
            default=None,
            description="Attachments to add or remove",
        ),
    ):
        self.submission_id = submission_id
        self.score = score
        self.comments = comments
        self.is_disqualified = is_disqualified
        self.attachments = attachments


class DownloadSubmissionType(enum.Enum):
    SUBMISSION = "submission"
    EVALUATION = "evaluation"


class DownloadSubmissionParams:
    def __init__(
        self,
        submission_id: uuid.UUID = Path(
            ..., description="ID of the submission to download"
        ),
        type: DownloadSubmissionType = Query(
            ..., description="Type of the submission to download"
        ),
    ):
        self.submission_id = submission_id
        self.type = type
