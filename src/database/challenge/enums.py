import uuid
import enum
from pydantic import Field
from typing import TypedDict


class CompetitionStatusEnum(enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    EVALUATION = "EVALUATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PrizeTypeEnum(enum.Enum):
    CASH = "CASH"
    NO_CASH = "NO_CASH"


class Datasets(TypedDict):
    id: uuid.UUID = Field(..., description="Id of the dataset")
    name: str = Field(..., description="Name of the dataset")


class AttachmentMetadata(TypedDict):
    content_type: str = Field(
        ..., description="Content type of the file attached to the submission"
    )
    content_length_bytes: int = Field(
        ...,
        description="Content length of the file attached to the submission in bytes",
    )
    size_in_kb: float = Field(
        ..., description="Size of the file attached to the submission in KB"
    )


class RulesAndGuidelinesSchema(TypedDict):
    s3_key: str = Field(..., description="S3 key of the asset")
    metadata: AttachmentMetadata = Field(
        ..., description="Metadata of the file attached to the submission"
    )
    uploaded_at: str = Field(
        ..., description="Date and time when the file was uploaded"
    )


class AdditionalAttachmentSchema(TypedDict):
    s3_key: str = Field(..., description="S3 key of the asset")
    metadata: AttachmentMetadata = Field(
        ..., description="Metadata of the file attached to the submission"
    )
    description: str = Field(
        ..., description="Description of the file attached to the submission"
    )
    uploaded_at: str = Field(
        ..., description="Date and time when the file was uploaded"
    )


class SubmissionAttachmentSchema(TypedDict):
    s3_key: str = Field(..., description="S3 key of the asset")
    metadata: AttachmentMetadata = Field(
        ..., description="Metadata of the file attached to the submission"
    )
    uploaded_at: str = Field(
        ..., description="Date and time when the file was uploaded"
    )
