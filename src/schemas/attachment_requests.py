import enum
import uuid
from fastapi import Body, Path, Query


class UploadType(enum.Enum):
    CONTENT = "content"
    ATTACHMENT = "attachment"
    COMMENT = "comment"


class GeneratePresignedURLParams:
    def __init__(
        self,
        batch_id: uuid.UUID = Path(
            ..., description="ID of the batch to generate URL for"
        ),
        type_of_upload: UploadType = Body(
            ..., description="Type of upload to generate URL for"
        ),
        file_name: str = Body(..., description="Name of the file to generate URL for"),
    ):
        self.batch_id = batch_id
        self.type_of_upload = type_of_upload
        self.file_name = file_name


class DeleteAttachmentParams:
    def __init__(
        self,
        object_key: str = Body(
            ..., description="Object key of the attachment to delete"
        ),
        type: UploadType = Body(..., description="Type of the attachment to delete"),
        pre_creation: bool = Body(
            ...,
            description="Whether the attachment is added before the entity creation",
        ),
    ):
        self.object_key = object_key
        self.type = type
        self.pre_creation = pre_creation


class GenerateDownloadUrlParams:
    def __init__(
        self,
        id: str = Path(..., description="Object key of the attachment to download"),
        type: UploadType = Query(..., description="Type of the attachment to download"),
    ):
        self.id = id
        self.type = type
