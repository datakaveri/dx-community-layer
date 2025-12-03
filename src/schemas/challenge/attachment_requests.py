import enum
import uuid
from fastapi import Body, Path
from fastapi import Query


class UploadType(enum.Enum):
    CONTENT = "content"
    ATTACHMENT = "attachment"


class GeneratePresignedURLParams:
    def __init__(
        self,
        batch_id: uuid.UUID = Path(...),
        type_of_upload: UploadType = Body(...),
        file_name: str = Body(...),
        content_type: str = Body(default="application/octet-stream", description="Content type of the file"),
    ):
        self.batch_id = batch_id
        self.type_of_upload = type_of_upload
        self.file_name = file_name
        self.content_type = content_type


class DeleteAttachmentParams:
    def __init__(
        self,
        object_key: str = Body(..., description="Object key of the attachment to delete"),
        type: UploadType = Body(..., description="Type of the attachment to delete"),
        pre_creation: bool = Body(
            ..., description="Whether the attachment is added before the entity creation"
        ),
    ):
        self.object_key = object_key
        self.type = type
        self.pre_creation = pre_creation


class GenerateDownloadUrlParams:
    def __init__(
        self,
        object_key: str = Query(..., description="S3 object key of the attachment to download"),
        type: UploadType = Query(..., description="Type of the attachment to download"),
    ):
        self.id = object_key  # Keep id for backward compatibility with handler
        self.object_key = object_key
        self.type = type

