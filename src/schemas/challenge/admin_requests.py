from datetime import date, datetime
import enum
from typing import Dict, List, Optional, TypedDict
import uuid
from fastapi import Body, Path, Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from .submission_requests import SortOrder, UpdateSubmissionAttachmetsSchema
from ...database.challenge.enums import CompetitionStatusEnum, Datasets, PrizeTypeEnum


class AdminRetreiveCompetitionsSortBy(enum.Enum):
    TITLE = "title"
    PUBLISHED_AT = "published_at"
    EVALUATION_ENDS_AT = "evaluation_ends_at"
    SCHEDULED_PUBLISH_AT = "scheduled_publish_at"
    UPDATED_AT = "updated_at"


class AdminRetrieveCompetitionsChoices(enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    EVALUATION = "evaluation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AdminRetrieveCompetitionsParams:
    STATUS_MAP = {
        "draft": CompetitionStatusEnum.DRAFT,
        "scheduled": CompetitionStatusEnum.SCHEDULED,
        "published": CompetitionStatusEnum.PUBLISHED,
        "evaluation": CompetitionStatusEnum.EVALUATION,
        "completed": CompetitionStatusEnum.COMPLETED,
        "cancelled": CompetitionStatusEnum.CANCELLED,
    }

    def __init__(
        self,
        choice: AdminRetrieveCompetitionsChoices = Path(
            ..., description="Type of the challenge to retrieve"
        ),
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of challenges per page"),
        sort_by: Optional[AdminRetreiveCompetitionsSortBy] = Query(
            default=None,
            description="The field to sort by",
        ),
        sort_order: Optional[SortOrder] = Query(
            default=None,
            description="The order to sort by",
        ),
    ):
        self.choice: CompetitionStatusEnum = self.STATUS_MAP[choice.value]
        self.query = query
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order


class AdminRetrieveCompetitionSubmissionsSortByEnum(enum.Enum):
    PARTICIPANT_NAME = "participant_name"
    TITLE = "title"
    SUBMITTED_AT = "submitted_at"


class AdminRetrieveCompetitionSubmissionsParams:
    def __init__(
        self,
        competition_id: uuid.UUID = Path(..., description="ID of the challenge"),
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of submissions per page"),
        sort_by: Optional[AdminRetrieveCompetitionSubmissionsSortByEnum] = Query(
            default=None,
            description="The field to sort by",
        ),
        sort_order: Optional[SortOrder] = Query(
            default=None,
            description="The order to sort by",
        ),
    ):
        self.competition_id = competition_id
        self.query = query
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order


class CompetitionAssets(TypedDict):
    object_key: str = Field(..., description="S3 object key of the asset")
    description: str = Field(..., description="Description of the asset")


class AdminCreateCompetitionParams:
    def __init__(
        self,
        draft: bool = Body(..., description="Whether the competition is a draft"),
        title: str = Body(..., description="Title of the competition"),
        subtitle: Optional[str] = Body(
            default=None, description="Subtitle of the competition"
        ),
        overview: Optional[str] = Body(
            default=None, description="Overview of the competition"
        ),
        description: Optional[str] = Body(
            default=None, description="Description of the competition"
        ),
        image_url: Optional[str] = Body(
            default=None, description="Image URL of the competition (s3 key)"
        ),
        constraints: Optional[str] = Body(
            default=None, description="Constraints of the competition"
        ),
        evaluation_criteria_definition: Optional[str] = Body(
            default=None,
            description="Evaluation criteria definition of the competition",
        ),
        submission_file_definition: Optional[str] = Body(
            default=None,
            description="Submission file definition of the competition",
        ),
        other_resources: Optional[str] = Body(
            default=None, description="Other resources of the competition"
        ),
        prize_type: PrizeTypeEnum = Body(
            default=PrizeTypeEnum.NO_CASH,
            description="Prize type of the competition",
        ),
        total_pool_amount: Optional[float] = Body(
            default=0,
            description="Total pool amount of the competition",
        ),
        currency: Optional[str] = Body(
            default=None,
            description="Currency of the competition",
            min_length=1,
            max_length=3,
        ),
        prize_pool_description: Optional[str] = Body(
            default=None,
            description="Prize pool description of the competition",
        ),
        submission_starts_at: Optional[date] = Body(
            default=None,
            description="Submission start time of the competition",
        ),
        submission_ends_at: Optional[date] = Body(
            default=None,
            description="Submission end time of the competition",
        ),
        evaluation_ends_at: Optional[date] = Body(
            default=None,
            description="Evaluation end time of the competition",
        ),
        rules_and_guidelines: Optional[str] = Body(
            default=None,
            description="Rules and guidelines of the competition (s3 key)",
        ),
        dataset_description: Optional[str] = Body(
            default=None,
            description="Dataset description of the competition",
        ),
        data_models: Optional[List[Datasets]] = Body(
            default=None,
            description="Data models of the competition (s3 key)",
        ),
        ai_models: Optional[List[Datasets]] = Body(
            default=None,
            description="AI models of the competition (s3 key)",
        ),
        additional_assets: Optional[List[CompetitionAssets]] = Body(
            default=None,
            description="Additional assets of the competition (s3 key)",
        ),
        publish_schedule: Optional[datetime] = Body(
            default=None,
            description="Publish schedule of the competition",
        ),
    ):
        self.draft = draft
        self.title = title.strip()
        self.subtitle = subtitle.strip() if isinstance(subtitle, str) else subtitle
        self.overview = overview.strip() if isinstance(overview, str) else overview
        self.description = (
            description.strip() if isinstance(description, str) else description
        )
        self.image_url = image_url
        self.constraints = (
            constraints.strip() if isinstance(constraints, str) else constraints
        )
        self.evaluation_criteria_definition = (
            evaluation_criteria_definition.strip()
            if isinstance(evaluation_criteria_definition, str)
            else evaluation_criteria_definition
        )
        self.submission_file_definition = (
            submission_file_definition.strip()
            if isinstance(submission_file_definition, str)
            else submission_file_definition
        )
        self.other_resources = other_resources
        self.prize_type = prize_type
        self.total_pool_amount = total_pool_amount
        self.currency = currency.strip() if isinstance(currency, str) else currency
        self.prize_pool_description = (
            prize_pool_description.strip()
            if isinstance(prize_pool_description, str)
            else prize_pool_description
        )
        self.submission_starts_at = submission_starts_at
        self.submission_ends_at = submission_ends_at
        self.evaluation_ends_at = evaluation_ends_at
        self.rules_and_guidelines = rules_and_guidelines
        self.dataset_description = dataset_description
        self.data_models = data_models
        self.ai_models = ai_models
        self.additional_assets = additional_assets
        self.publish_schedule = publish_schedule

        if not self.draft:
            errors = []

            required_fields = {
                "subtitle": self.subtitle,
                "overview": self.overview,
                "description": self.description,
                "constraints": self.constraints,
                "evaluation_criteria_definition": self.evaluation_criteria_definition,
                "submission_file_definition": self.submission_file_definition,
                "prize_pool_description": self.prize_pool_description,
                "submission_starts_at": self.submission_starts_at,
                "submission_ends_at": self.submission_ends_at,
                "evaluation_ends_at": self.evaluation_ends_at,
                "rules_and_guidelines": self.rules_and_guidelines,
                "dataset_description": self.dataset_description,
                "data_models": self.data_models,
            }

            for key, value in required_fields.items():
                if value is None:
                    errors.append(
                        {
                            "loc": ["body", key],
                            "msg": f"{key.replace('_', ' ').capitalize()} is required when draft is False",
                            "type": "value_error.missing",
                            "input": value,
                        }
                    )

            if errors:
                raise RequestValidationError(errors)

        if self.prize_type == PrizeTypeEnum.CASH:
            if self.currency is None:
                raise RequestValidationError(
                    [
                        {
                            "loc": ["body", "currency"],
                            "msg": "Currency is required when prize_type is CASH",
                            "type": "value_error.missing",
                            "input": currency,
                        }
                    ]
                )
            if self.total_pool_amount is None:
                raise RequestValidationError(
                    [
                        {
                            "loc": ["body", "total_pool_amount"],
                            "msg": "Total pool amount is required when prize_type is CASH",
                            "type": "value_error.missing",
                            "input": total_pool_amount,
                        }
                    ]
                )


class UpdateAttachmetsSchema(BaseModel):
    add: Optional[List[CompetitionAssets]] = Field(
        default=None,
        description="Optional attachment metadata (S3 keys, description) to add",
    )
    remove: Optional[List[str]] = Field(
        default=None,
        description="Optional attachment metadata (S3 keys) to remove",
    )
    updated_descriptions: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional attachment metadata (file_name, description) to update",
    )


class UpdateDatasetsSchema(BaseModel):
    add: Optional[List[Datasets]] = Field(
        default=None,
        description="Optional dataset metadata (id, name) to add",
    )
    remove: Optional[List[str]] = Field(
        default=None,
        description="Optional dataset metadata (id) to remove",
    )


class AdminUpdateCompetitionParams:
    def __init__(
        self,
        competition_id: uuid.UUID = Path(..., description="ID of the competition"),
        draft: bool = Body(..., description="Whether the competition is a draft"),
        title: Optional[str] = Body(
            default=None, description="Title of the competition"
        ),
        subtitle: Optional[str] = Body(
            default=None, description="Subtitle of the competition"
        ),
        overview: Optional[str] = Body(
            default=None, description="Overview of the competition"
        ),
        description: Optional[str] = Body(
            default=None, description="Description of the competition"
        ),
        image_url: Optional[str] = Body(
            default=None, description="Image URL of the competition (s3 key)"
        ),
        constraints: Optional[str] = Body(
            default=None, description="Constraints of the competition"
        ),
        evaluation_criteria_definition: Optional[str] = Body(
            default=None,
            description="Evaluation criteria definition of the competition",
        ),
        submission_file_definition: Optional[str] = Body(
            default=None,
            description="Submission file definition of the competition",
        ),
        other_resources: Optional[str] = Body(
            default=None, description="Other resources of the competition"
        ),
        prize_type: PrizeTypeEnum = Body(
            default=PrizeTypeEnum.NO_CASH,
            description="Prize type of the competition",
        ),
        total_pool_amount: Optional[float] = Body(
            default=0,
            description="Total pool amount of the competition",
        ),
        currency: Optional[str] = Body(
            default=None,
            description="Currency of the competition",
            min_length=1,
            max_length=3,
        ),
        prize_pool_description: Optional[str] = Body(
            default=None,
            description="Prize pool description of the competition",
        ),
        submission_starts_at: Optional[date] = Body(
            default=None,
            description="Submission start time of the competition",
        ),
        submission_ends_at: Optional[date] = Body(
            default=None,
            description="Submission end time of the competition",
        ),
        evaluation_ends_at: Optional[date] = Body(
            default=None,
            description="Evaluation end time of the competition",
        ),
        rules_and_guidelines: Optional[str] = Body(
            default=None,
            description="Rules and guidelines of the competition (s3 key)",
        ),
        dataset_description: Optional[str] = Body(
            default=None,
            description="Dataset description of the competition",
        ),
        data_models: Optional[UpdateDatasetsSchema] = Body(
            default=None,
            description="Data models of the competition",
        ),
        ai_models: Optional[UpdateDatasetsSchema] = Body(
            default=None,
            description="AI models of the competition",
        ),
        additional_assets: Optional[UpdateAttachmetsSchema] = Body(
            default=None,
            description="Additional assets of the competition (s3 key)",
        ),
        publish_schedule: Optional[datetime] = Body(
            default=None,
            description="Publish schedule of the competition",
        ),
    ):
        self.competition_id = competition_id
        self.draft = draft
        self.title = title.strip() if isinstance(title, str) else title
        self.subtitle = subtitle.strip() if isinstance(subtitle, str) else subtitle
        self.overview = overview.strip() if isinstance(overview, str) else overview
        self.description = (
            description.strip() if isinstance(description, str) else description
        )
        self.image_url = image_url
        self.constraints = (
            constraints.strip() if isinstance(constraints, str) else constraints
        )
        self.evaluation_criteria_definition = (
            evaluation_criteria_definition.strip()
            if isinstance(evaluation_criteria_definition, str)
            else evaluation_criteria_definition
        )
        self.submission_file_definition = (
            submission_file_definition.strip()
            if isinstance(submission_file_definition, str)
            else submission_file_definition
        )
        self.other_resources = other_resources
        self.prize_type = prize_type
        self.total_pool_amount = total_pool_amount
        self.currency = currency.strip() if isinstance(currency, str) else currency
        self.prize_pool_description = (
            prize_pool_description.strip()
            if isinstance(prize_pool_description, str)
            else prize_pool_description
        )
        self.submission_starts_at = submission_starts_at
        self.submission_ends_at = submission_ends_at
        self.evaluation_ends_at = evaluation_ends_at
        self.rules_and_guidelines = rules_and_guidelines
        self.dataset_description = dataset_description
        self.data_models = data_models
        if self.data_models:
            if self.data_models.add:
                for dataset in self.data_models.add:
                    dataset["id"] = str(dataset["id"])

        self.ai_models = ai_models
        if self.ai_models:
            if self.ai_models.add:
                for dataset in self.ai_models.add:
                    dataset["id"] = str(dataset["id"])

        self.additional_assets = additional_assets
        self.publish_schedule = publish_schedule


class AdminEvaluateSubmissionParams:
    def __init__(
        self,
        submission_id: uuid.UUID = Path(..., description="ID of the submission"),
        disqualify: bool = Body(
            ..., description="Whether to disqualify the submission"
        ),
        comments: Optional[str] = Body(
            default=None, description="Comments for disqualification"
        ),
        score: Optional[float] = Body(
            default=None,
            description="Score for the submission (optional)",
        ),
        attachments: Optional[UpdateSubmissionAttachmetsSchema] = Body(
            default=None,
            description="Attachments to add to the evaluation (s3 keys)",
        ),
    ):
        self.submission_id = submission_id
        self.disqualify = disqualify
        self.comments = comments
        self.score = score
        self.attachments = attachments
