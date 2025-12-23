from typing import Literal, Union
from pydantic import BaseModel, AnyUrl

from ..default_schemas import (
    BadRequestErrorResponse,
    SuccessfulResponse,
    BackendErrorResponse,
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
)


class GeneratePresignedURLData(BaseModel):
    file_name: str
    presigned_url: AnyUrl


class GeneratePresignedURLMeta(BaseModel):
    batch_id: str
    object_key: str


class GeneratePresignedURLSuccessResponse(SuccessfulResponse):
    message: Literal["Presigned URL generated successfully"]
    data: GeneratePresignedURLData
    meta: GeneratePresignedURLMeta


class GeneratePresignedUrlBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while generating the presigned URL. Please contact developers if the issue persists."
        ],
    ]


class GeneratePresignedURLBackendErrorResponse(BackendErrorResponse):
    message: Literal["Presigned URL generation failed"]
    error: GeneratePresignedUrlBackendError


GENERATE_PRESIGNED_URL_RESPONSE_MODEL = {
    200: {"model": GeneratePresignedURLSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": GeneratePresignedURLBackendErrorResponse},
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
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}
