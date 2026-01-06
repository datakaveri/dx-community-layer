import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path, Query

from ...docs import public_desc
from ...middlewares.logging import logger
from ...configs.db_config import get_challenge_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...schemas.default_schemas import AuthorizationData
from ...schemas.challenge.attachment_responses import (
    GENERATE_PRESIGNED_URL_RESPONSE_MODEL,
    DELETE_ATTACHMENTS_RESPONSE_MODEL,
    DOWNLOAD_PRESIGNED_URL_RESPONSE_MODEL,
)
from ...schemas.challenge.attachment_requests import (
    DownloadSubmissionAttachmentsParams,
    GeneratePresignedURLParams,
    DeleteAttachmentParams,
)
from ...services.challenge.attachment_services import (
    delete_temporary_attachment_handler,
    download_additional_assets_handler,
    download_rules_and_guidelines_handler,
    download_submission_attachments_handler,
    generate_presigned_url_handler,
)
from ...middlewares.authorization import http_bearer_header, http_bearer_header_public


router = APIRouter(prefix="/attachment", tags=["Challenge - Attachment APIs"])


@router.post(
    path="",
    description="Generates a presigned URL for uploading attachments to S3.",
    responses=GENERATE_PRESIGNED_URL_RESPONSE_MODEL,
)
async def generate_presigned_url(
    req_params: GeneratePresignedURLParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
) -> CustomJSONResponse:
    """
    Generates a presigned URL for uploading attachments to S3.

    Args:
        req_params (GeneratePresignedURLParams): The request body containing the presigned URL details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.

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
    description="Deletes temporary attachments from S3 based on the provided object key.",
    responses=DELETE_ATTACHMENTS_RESPONSE_MODEL,
)
async def delete_temporary_attachment(
    req_params: DeleteAttachmentParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
) -> CustomJSONResponse:
    """
    Deletes temporary attachments from S3 based on the provided object key.

    Args:
        req_params (DeleteAttachmentsParams): The request body containing the attachment details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.

    Returns:
        CustomJSONResponse: A JSON response indicating success or failure of the deletion operation.
    """
    logger.info("Delete Attachment API is being called")

    return await delete_temporary_attachment_handler(
        req_params=req_params, authorized_user=authorized_user
    )


@router.get(
    path="/download/rules_and_guidelines/{competition_id}",
    description=public_desc(
        "Generates a presigned URL for downloading rules and guidelines from S3 for a specific competition."
    ),
    responses=DOWNLOAD_PRESIGNED_URL_RESPONSE_MODEL,
)
async def download_rules_and_guidelines(
    competition_id: uuid.UUID = Path(..., description="ID of the competition"),
    authorized_user: AuthorizationData = Depends(http_bearer_header_public),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Generates a presigned URL for downloading rules and guidelines from S3 for a specific competition.

    Args:
        competition_id (str): The ID of the competition for which rules and guidelines are downloaded.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response containing the presigned download URL for rules and guidelines.
    """
    logger.info("Download Rules and Guidelines API is being called")

    return await download_rules_and_guidelines_handler(
        competition_id=competition_id,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/download/additional_assets/{competition_id}",
    responses=DOWNLOAD_PRESIGNED_URL_RESPONSE_MODEL,
    description="Generates a presigned URL for downloading additional assets from S3 for a specific competition.",
)
async def download_additional_assets(
    competition_id: uuid.UUID = Path(..., description="ID of the competition"),
    file_name: str = Query(..., description="Name of the file to download"),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Generates a presigned URL for downloading additional assets from S3 for a specific competition.

    Args:
        competition_id (str): The ID of the competition for which additional assets are downloaded.
        file_name (str): The name of the file to download.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response containing the presigned download URL for additional assets.
    """
    logger.info("Download Additional Assets API is being called")

    return await download_additional_assets_handler(
        competition_id=competition_id,
        file_name=file_name,
        authorized_user=authorized_user,
        db_session=db_session,
    )


@router.get(
    path="/download/submission/{submission_id}/{choice}",
    responses=DOWNLOAD_PRESIGNED_URL_RESPONSE_MODEL,
    description="Generates a presigned URL for downloading submissions from S3",
)
async def download_submission_attachments(
    req_params: DownloadSubmissionAttachmentsParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_challenge_db_session),
) -> CustomJSONResponse:
    """
    Generates a presigned URL for downloading submission attachments from S3.

    Args:
        req_params (DownloadSubmissionAttachmentsParams): The request body containing the presigned URL details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response with the created presigned URL and relevant metadata.
    """
    logger.info("Download Submission Attachments API is being called")

    return await download_submission_attachments_handler(
        req_params=req_params,
        authorized_user=authorized_user,
        db_session=db_session,
    )
