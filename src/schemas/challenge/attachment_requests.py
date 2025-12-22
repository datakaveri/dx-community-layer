import enum
import uuid
from fastapi import Body, Path


class GeneratePresignedURLParams:
    def __init__(
        self,
        batch_id: uuid.UUID = Body(
            ..., description="ID of the batch to generate URL for"
        ),
        file_name: str = Body(..., description="Name of the file to generate URL for"),
    ):
        self.batch_id = batch_id
        self.file_name = file_name


class DeleteAttachmentParams:
    def __init__(
        self,
        batch_id: uuid.UUID = Body(
            ..., description="ID of the batch to delete attachment from"
        ),
        object_key: str = Body(
            ..., description="Object key of the attachment to delete"
        ),
    ):
        self.batch_id = batch_id
        self.object_key = object_key


class SubmissionAttachmentChoice(enum.Enum):
    SOLUTION = "solution"
    EVALUATION = "evaluation"


class DownloadSubmissionAttachmentsParams:
    def __init__(
        self,
        submission_id: uuid.UUID = Path(
            ..., description="ID of the submission to download attachments for"
        ),
        choice: SubmissionAttachmentChoice = Path(
            ..., description="Choice of attachments to download"
        ),
    ):
        self.submission_id = submission_id
        self.choice = choice
