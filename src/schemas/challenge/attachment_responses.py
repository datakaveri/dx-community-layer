from typing import Literal, Optional
from pydantic import BaseModel, AnyUrl

from ..default_schemas import (
    BackendErrorResponse,
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
)


class GeneratePresignedURLData(BaseModel):
    file_name: str
    presigned_url: AnyUrl | str
    public_url: Optional[AnyUrl | str] = None


class GeneratePresignedURLMeta(BaseModel):
    batch_id: str
    type_of_upload: Literal["content", "attachment"]
    object_key: str


class GeneratePresignedURLSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: Literal["Presigned URL generated successfully"]
    data: GeneratePresignedURLData
    error: None = None
    meta: GeneratePresignedURLMeta


GENERATE_PRESIGNED_URL_RESPONSE_MODEL = {
    200: {"model": GeneratePresignedURLSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}


class DeleteAttachmentSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: Literal["Attachment deleted successfully"]
    data: None = None
    error: None = None
    meta: None = None


DELETE_ATTACHMENTS_RESPONSE_MODEL = {
    200: {"model": DeleteAttachmentSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}


class GenerateDownloadURLData(BaseModel):
    file_name: str
    download_url: AnyUrl | str


class GenerateDownloadURLSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: Literal["Download URL generated successfully"]
    data: GenerateDownloadURLData
    error: None = None
    meta: None = None


GENERATE_DOWNLOAD_URL_RESPONSE_MODEL = {
    200: {"model": GenerateDownloadURLSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}

