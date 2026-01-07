import enum
import uuid
from typing import List, Optional
from fastapi import Body, Path, Query
from pydantic import BaseModel, Field
from fastapi.exceptions import RequestValidationError
from ...middlewares.search_validation import validate_search_query


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
        validate_search_query(query)
        self.choice = choice
        self.query = query
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order


class CreateUserSubmissionsParams:
    def __init__(
        self,
        competition_id: uuid.UUID = Path(..., description="ID of the competition"),
        title: str = Body(..., max_length=300, description="Title for the submission"),
        description: str = Body(..., description="Description of the submission"),
        attachments: List[str] = Body(
            default=None,
            description="Attachments to add to the submission (s3 keys)",
            min_length=2,
            max_length=2,
        ),
    ):
        self.competition_id = competition_id
        self.title = title.strip()
        self.description = description.strip()
        self.attachments = attachments

        # Attachment validation
        try:
            extensions = set(
                [
                    attachment.split("/")[-1].split(".")[-1].lower()
                    for attachment in self.attachments
                ]
            )

            allowed_docs = {"pdf", "doc", "docx"}

            # File type validation
            has_zip = "zip" in extensions
            has_doc = any(ext in allowed_docs for ext in extensions)

            if not has_zip and not has_doc:
                raise RequestValidationError(
                    [
                        {
                            "loc": ["body", "attachments"],
                            "msg": "Invalid file extension for attachment. Must be a zip file and one of pdf, doc, or docx.",
                            "type": "value_error.invalid",
                            "input": attachments,
                        }
                    ]
                )
        except Exception:
            raise RequestValidationError(
                [
                    {
                        "loc": ["body", "attachments"],
                        "msg": "Invalid attachment key",
                        "type": "value_error.invalid",
                        "input": attachments,
                    }
                ]
            )


class UpdateSubmissionAttachmetsSchema(BaseModel):
    add: Optional[List[str]] = Field(
        default=None,
        description="Optional attachment metadata (S3 keys) to add",
    )
    remove: Optional[List[str]] = Field(
        default=None,
        description="Optional attachment metadata (S3 keys) to remove",
    )


class UpdateUserSubmissionsParams:
    def __init__(
        self,
        submission_id: uuid.UUID = Path(..., description="ID of the competition"),
        title: Optional[str] = Body(
            default=None, max_length=300, description="Title for the submission"
        ),
        description: Optional[str] = Body(
            default=None, description="Description of the submission"
        ),
        attachments: Optional[UpdateSubmissionAttachmetsSchema] = Body(
            default=None,
            description="Attachments to add to the submission (s3 keys)",
        ),
    ):
        self.submission_id = submission_id
        self.title = title
        self.description = description
        self.attachments = attachments


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
