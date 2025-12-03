import uuid
from pydantic import BaseModel
from typing import Literal, Optional, Union

from ..default_schemas import (
    BackendErrorResponse,
    BadRequestErrorResponse,
    SuccessfulResponse,
    UnauthorizedErrorResponse,
    ValidationErrorResponse,
)
from .attachment_requests import UploadType


class GeneratePresignedUrlSuccessfulData(BaseModel):
    file_name: str
    public_url: str
    presigned_url: Optional[str]


class GeneratePresignedUrlSuccessfulMeta(BaseModel):
    batch_id: uuid.UUID
    type_of_upload: UploadType
    object_key: str


class GeneratePresignedUrlSuccessfulResponse(SuccessfulResponse):
    message: Literal["Presigned URL generated successfully"]
    data: GeneratePresignedUrlSuccessfulData
    meta: GeneratePresignedUrlSuccessfulMeta


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


class GeneratePresignedUrlBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to generate presigned URL"]
    error: GeneratePresignedUrlBackendError


GENERATE_PRESIGNED_URL_RESPONSE_MODEL = {
    200: {"model": GeneratePresignedUrlSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": GeneratePresignedUrlBackendErrorResponse},
}


class DeleteAttachmentsSuccessfulResponse(SuccessfulResponse):
    message: Literal["Attachments deleted successfully"]


class DeleteAttachmentsForbiddenError(BaseModel):
    code: Literal["FORBIDDEN"]
    details: Literal[
        "You do not have permission to delete this attachment. Please contact support if required."
    ]


class DeleteAttachmentsForbiddenErrorResponse(BackendErrorResponse):
    message: Literal["Forbidden access"]
    error: DeleteAttachmentsForbiddenError


class DeleteAttachmentsNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The attachment you are trying to delete does not exist. Please try again later or contact support if the issue persists."
    ]


class DeleteAttachmentsNotFoundErrorResponse(BackendErrorResponse):
    message: Literal["Attachment not found"]
    error: DeleteAttachmentsNotFoundError


class DeleteAttachmentsBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to delete one or more attachments from S3. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while deleting the attachment. Please contact developers if the issue persists."
        ],
    ]


class DeleteAttachmentsBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to delete attachments"]
    error: DeleteAttachmentsBackendError


DELETE_ATTACHMENTS_RESPONSE_MODEL = {
    200: {"model": DeleteAttachmentsSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": DeleteAttachmentsForbiddenErrorResponse},
    404: {"model": DeleteAttachmentsNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": DeleteAttachmentsBackendErrorResponse},
}


class GenerateDownloadUrlSuccessfulData(BaseModel):
    file_name: str
    download_url: str


class GenerateDownloadUrlSuccessfulResponse(SuccessfulResponse):
    message: Literal["Download URL generated successfully"]
    data: GenerateDownloadUrlSuccessfulData


class GenerateDownloadUrlNotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The attachment you are trying to download does not exist. Please try again later or contact support if the issue persists."
    ]


class GenerateDownloadUrlNotFoundErrorResponse(BackendErrorResponse):
    message: Literal["Attachment not found"]
    error: GenerateDownloadUrlNotFoundError


class GenerateDownloadUrlBackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Union[
        Literal[
            "Failed to authorize user. Please contact developers if the issue persists."
        ],
        Literal[
            "An error occurred while generating the download URL. Please contact developers if the issue persists."
        ],
    ]


class GenerateDownloadUrlBackendErrorResponse(BackendErrorResponse):
    message: Literal["Failed to generate download URL"]
    error: GenerateDownloadUrlBackendError


GENERATE_DOWNLOAD_URL_RESPONSE_MODEL = {
    200: {"model": GenerateDownloadUrlSuccessfulResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    404: {"model": GenerateDownloadUrlNotFoundErrorResponse},
    422: {"model": ValidationErrorResponse},
    500: {"model": GenerateDownloadUrlBackendErrorResponse},
}
