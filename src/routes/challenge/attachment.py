from fastapi import APIRouter, Depends, status

from ...middlewares.logging import logger
from ...middlewares.authorization import http_bearer_header
from ...configs.db_config import get_db_session
from ...schemas.custom_responses import CustomJSONResponse
from ...schemas.default_schemas import AuthorizationData
from ...schemas.challenge.attachment_responses import (
    GENERATE_PRESIGNED_URL_RESPONSE_MODEL,
    DELETE_ATTACHMENTS_RESPONSE_MODEL,
    GENERATE_DOWNLOAD_URL_RESPONSE_MODEL,
)
from ...schemas.challenge.attachment_requests import (
    GeneratePresignedURLParams,
    DeleteAttachmentParams,
    GenerateDownloadUrlParams,
)
from ...services.challenge.attachment_services import (
    generate_presigned_url_handler,
    delete_attachment_handler,
    generate_download_url_handler,
)
from sqlalchemy.ext.asyncio import AsyncSession


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
    logger.info("Delete Attachment API is being called")
    return await delete_attachment_handler(
        req_params=req_params, authorized_user=authorized_user, db_session=db_session
    )


@router.get(
    path="/generate_download_url",
    description="Generates a presigned URL for downloading attachments from S3.",
    responses=GENERATE_DOWNLOAD_URL_RESPONSE_MODEL,
)
async def generate_download_url(
    req_params: GenerateDownloadUrlParams = Depends(),
    authorized_user: AuthorizationData = Depends(http_bearer_header),
    db_session: AsyncSession = Depends(get_db_session),
) -> CustomJSONResponse:
    logger.info("Generate Download URL API is being called")
    return await generate_download_url_handler(
        req_params=req_params, authorized_user=authorized_user, db_session=db_session
    )

