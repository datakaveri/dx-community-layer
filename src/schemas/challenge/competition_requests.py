import uuid
import enum
from datetime import datetime
from typing import Any, List, Dict, Optional
from fastapi import Body, HTTPException, Path, Query, status

from .submission_requests import SortOrder
from ...database.challenge.enums import PrizeTypeEnum


class CompetitionsSortBy(enum.Enum):
    HOTTEST = "Hottest"
    NEWEST = "Newest"
    OLDEST = "Oldest"


class RetrieveCompetitionChoices(enum.Enum):
    PUBLISHED = "published"
    JOINED = "joined"
    COMPLETED = "completed"


class RetrieveCompetitonsParams:
    def __init__(
        self,
        choice: RetrieveCompetitionChoices = Path(
            ...,
            description="Type of the competition to retrieve",
        ),
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of competitions per page"),
        sort_by: CompetitionsSortBy = Query(
            default=CompetitionsSortBy.NEWEST,
            description="The field to sort by",
        ),
    ):
        self.choice = choice
        self.query = query
        self.page = page
        self.limit = limit
        self.sort_by = sort_by


class RetrieveCompetitionLeaderboardSortByEnum(str, enum.Enum):
    PARTICIPANT_NAME = "participant_name"
    SUBMISSION_TITLE = "submission_title"
    SCORE = "score"
    SUBMITTED_AT = "submitted_at"


class RetrieveCompetitionLeaderboardParams:
    def __init__(
        self,
        competition_id: uuid.UUID = Path(..., description="ID of the competition"),
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of submissions per page"),
        sort_by: Optional[RetrieveCompetitionLeaderboardSortByEnum] = Query(
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


class RetrieveParticipatedCompetitionsSortByEnum(str, enum.Enum):
    TITLE = "title"
    TOTAL_POOL_AMOUNT = "total_pool_amount"
    SUBMISSION_STARTS_AT = "submission_starts_at"
    SUBMISSION_ENDS_AT = "submission_ends_at"


class RetrieveParticipatedCompetitionsParams:
    def __init__(
        self,
        query: Optional[str] = Query(default=None, description="Query to search for"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of competitions per page"),
        sort_by: Optional[RetrieveParticipatedCompetitionsSortByEnum] = Query(
            default=None,
            description="The field to sort by",
        ),
        sort_order: Optional[SortOrder] = Query(
            default=None,
            description="The order to sort by",
        ),
    ):
        self.query = query
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order


class CreateCompetitionParams:
    def __init__(
        self,
        title: str = Body(..., description="Competition title"),
        is_drafted: bool = Body(..., description="Whether the competition is a draft"),
        subtitle: Optional[str] = Body(
            None, description="Short subtitle for the competition"
        ),
        overview: Optional[str] = Body(
            None, description="High-level overview for the competition"
        ),
        description: Optional[str] = Body(
            None, description="Detailed description (required if not draft)"
        ),
        comp_image_url: Optional[str] = Body(
            None, description="Public image URL for the competition"
        ),
        constraints: Optional[str] = Body(None, description="Constraints"),
        prize_type: Optional[PrizeTypeEnum] = Body(
            None, description="Prize type (required if not draft)"
        ),
        total_pool_amount: Optional[float] = Body(
            None, description="Total prize pool amount (required if not draft)"
        ),
        currency: Optional[str] = Body(
            None, description="Currency code (e.g. INR, USD) (required if not draft)"
        ),
        prize_pool_description: Optional[str] = Body(
            None, description="Prize pool description"
        ),
        submission_starts_at: Optional[datetime] = Body(
            None, description="Submission start time (required if not draft)"
        ),
        submission_ends_at: Optional[datetime] = Body(
            None, description="Submission end time (required if not draft)"
        ),
        evaluation_ends_at: Optional[datetime] = Body(
            None, description="Evaluation end time"
        ),
        evaluation_criteria_definition: Optional[str] = Body(
            None, description="Evaluation criteria definition"
        ),
        submission_file_definition: Optional[str] = Body(
            None, description="Submission file definition"
        ),
        other_resources: Optional[str] = Body(
            None, description="Other resources (string)"
        ),
        dataset_description: Optional[str] = Body(
            None, description="Dataset description"
        ),
        data_models: Optional[List[Dict[str, Any]]] = Body(
            default=None, description="List of data models {name, id}"
        ),
        ai_models: Optional[List[Dict[str, Any]]] = Body(
            default=None, description="List of AI models {name, id}"
        ),
        additional_assets: Optional[List[str]] = Body(
            default=None, description="List of additional assets as dictionaries"
        ),
        rules_and_guidelines: Optional[str] = Body(
            None, description="Rules and guidelines (S3 key)"
        ),
        publish_schedule: Optional[datetime] = Body(
            default=None,
            description="If not drafted, when to publish. If absent, publish immediately.",
        ),
    ):
        # Validate required fields if not draft
        if not is_drafted:
            if not description:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="description is required when is_drafted is false",
                )
            if prize_type is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="prize_type is required when is_drafted is false",
                )
            if total_pool_amount is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="total_pool_amount is required when is_drafted is false",
                )
            if not currency:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="currency is required when is_drafted is false",
                )
            if submission_starts_at is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="submission_starts_at is required when is_drafted is false",
                )
            if submission_ends_at is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="submission_ends_at is required when is_drafted is false",
                )

        # Validate and normalize currency
        if currency:
            currency = currency.strip().upper()
            if len(currency) > 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Currency code must be at most 3 characters. Received: '{currency}' ({len(currency)} characters)",
                )
            if len(currency) == 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Currency code cannot be empty",
                )

        self.title = title
        self.subtitle = subtitle
        self.overview = overview
        self.description = description
        self.comp_image_url = comp_image_url
        self.constraints = constraints
        self.prize_type = prize_type
        self.total_pool_amount = total_pool_amount
        self.currency = currency
        self.prize_pool_description = prize_pool_description
        self.submission_starts_at = submission_starts_at
        self.submission_ends_at = submission_ends_at
        self.evaluation_ends_at = evaluation_ends_at
        self.evaluation_criteria_definition = evaluation_criteria_definition
        self.submission_file_definition = submission_file_definition
        self.other_resources = other_resources
        self.dataset_description = dataset_description
        self.data_models = data_models
        self.ai_models = ai_models
        self.additional_assets = additional_assets
        self.rules_and_guidelines = rules_and_guidelines
        self.is_drafted = is_drafted
        self.publish_schedule = publish_schedule


class UpdateCompetitionParams:
    def __init__(
        self,
        title: Optional[str] = Body(None, description="Competition title"),
        subtitle: Optional[str] = Body(
            None, description="Short subtitle for the competition"
        ),
        overview: Optional[str] = Body(
            None, description="High-level overview for the competition"
        ),
        description: Optional[str] = Body(None, description="Detailed description"),
        comp_image_url: Optional[str] = Body(
            None, description="Public image URL for the competition"
        ),
        constraints: Optional[str] = Body(None, description="Constraints"),
        prize_type: Optional[PrizeTypeEnum] = Body(None, description="Prize type"),
        total_pool_amount: Optional[float] = Body(
            None, description="Total prize pool amount"
        ),
        currency: Optional[str] = Body(
            None, description="Currency code (e.g. INR, USD)"
        ),
        prize_pool_description: Optional[str] = Body(
            None, description="Prize pool description"
        ),
        submission_starts_at: Optional[datetime] = Body(
            None, description="Submission start time"
        ),
        submission_ends_at: Optional[datetime] = Body(
            None, description="Submission end time"
        ),
        evaluation_ends_at: Optional[datetime] = Body(
            None, description="Evaluation end time"
        ),
        evaluation_criteria_definition: Optional[str] = Body(
            None, description="Evaluation criteria definition"
        ),
        submission_file_definition: Optional[str] = Body(
            None, description="Submission file definition"
        ),
        other_resources: Optional[str] = Body(
            None, description="Other resources (string)"
        ),
        dataset_description: Optional[str] = Body(
            None, description="Dataset description"
        ),
        data_models: Optional[List[Dict[str, Any]]] = Body(
            default=None, description="List of data models {name, id}"
        ),
        ai_models: Optional[List[Dict[str, Any]]] = Body(
            default=None, description="List of AI models {name, id}"
        ),
        additional_assets: Optional[List[Dict[str, Any]]] = Body(
            default=None, description="List of additional assets as dictionaries"
        ),
        rules_and_guidelines: Optional[str] = Body(
            None, description="Rules and guidelines (S3 key)"
        ),
        is_drafted: Optional[bool] = Body(
            None,
            description="Whether the competition is a draft. Set to false to publish.",
        ),
        publish_schedule: Optional[datetime] = Body(
            default=None,
            description="If is_drafted is false, when to publish. If absent, publish immediately.",
        ),
    ):
        # Validate and normalize currency if provided
        if currency:
            currency = currency.strip().upper()
            if len(currency) > 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Currency code must be at most 3 characters. Received: '{currency}' ({len(currency)} characters)",
                )
            if len(currency) == 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Currency code cannot be empty",
                )

        self.title = title
        self.subtitle = subtitle
        self.overview = overview
        self.description = description
        self.comp_image_url = comp_image_url
        self.constraints = constraints
        self.prize_type = prize_type
        self.total_pool_amount = total_pool_amount
        self.currency = currency
        self.prize_pool_description = prize_pool_description
        self.submission_starts_at = submission_starts_at
        self.submission_ends_at = submission_ends_at
        self.evaluation_ends_at = evaluation_ends_at
        self.evaluation_criteria_definition = evaluation_criteria_definition
        self.submission_file_definition = submission_file_definition
        self.other_resources = other_resources
        self.dataset_description = dataset_description
        self.data_models = data_models
        self.ai_models = ai_models
        self.additional_assets = additional_assets
        self.rules_and_guidelines = rules_and_guidelines
        self.is_drafted = is_drafted
        self.publish_schedule = publish_schedule
