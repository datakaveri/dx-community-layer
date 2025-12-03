import uuid
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ...configs.db_config import get_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...schemas.default_schemas import AuthorizationData
from ...middlewares.authorization import http_bearer_header
from ...schemas.attachment_requests import (
    DeleteAttachmentParams,
    GenerateDownloadUrlParams,
    GeneratePresignedURLParams,
)
from ...services.attachment_services import (
    generate_download_url_handler,
    generate_presigned_url_handler,
    delete_attachment_handler,
)
from ...schemas.attachment_responses import (
    GENERATE_DOWNLOAD_URL_RESPONSE_MODEL,
    GENERATE_PRESIGNED_URL_RESPONSE_MODEL,
    DELETE_ATTACHMENTS_RESPONSE_MODEL,
)

router = APIRouter(prefix="/attachment")


@router.post(
    path="/generate_presigned_url/{batch_id}",
    description="Generates a presigned URL for uploading attachments to S3.",
    responses=GENERATE_PRESIGNED_URL_RESPONSE_MODEL,
)
async def generate_presigned_url(
    req_params: GeneratePresignedURLParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
) -> CustomJSONResponse:
    """
    Generates a public presigned URL as per the type of upload.

    Args:
        req_params (GeneratePresignedURLParams): The request body containing the presigned URL details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (Session): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created presigned URL and relevant metadata.
    """
    logger.info("Generate Presigned URL API is being called")

    return await generate_presigned_url_handler(
        req_params=req_params,
        authorized_user=authorized_user,
    )


@router.delete(
    path="",
    description="Deletes attachments from S3 based on the provided object key and type.",
    responses=DELETE_ATTACHMENTS_RESPONSE_MODEL,
)
async def delete_attachment(
    req_params: DeleteAttachmentParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_db_session),
) -> CustomJSONResponse:
    """
        Deletes attachments from S3 based on the provided object key and type.
    rem
        Args:
            req_params (DeleteAttachmentsParams): The request body containing the attachment details.
            authorized_user (AuthorizationData): The authenticated user's data.
            db_session (AsyncSession): The database session for accessing the primary database.

        Returns:
            CustomJSONResponse: A JSON response indicating success or failure of the deletion operation.
    """
    logger.info("Delete Attachment API is being called")

    return await delete_attachment_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/generate_download_url/{id}",
    description="Generates a presigned URL for downloading attachments from S3.",
    responses=GENERATE_DOWNLOAD_URL_RESPONSE_MODEL,
)
async def generate_download_url(
    req_params: GenerateDownloadUrlParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_db_session),
) -> CustomJSONResponse:
    """
    Generates a presigned URL for downloading attachments from S3.

    Args:
        attachment_id (UUID): The ID of the attachment to download.
        authorized_user (AuthorizationData): The authenticated user's data.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: JSON response containing the presigned download URL.
    """
    logger.info(f"Download Attachment API is being called")

    return await generate_download_url_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )
