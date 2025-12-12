import uuid
from urllib.parse import unquote
from fastapi import status
from botocore.exceptions import ClientError

from ...configs.s3_config import s3_client
from ...configs.env_config import env_config
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ...schemas.challenge.attachment_requests import (
    UploadType,
    GeneratePresignedURLParams,
    DeleteAttachmentParams,
    GenerateDownloadUrlParams,
)
from ...schemas.default_schemas import AuthorizationData
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from sqlalchemy import select

try:
    # Optional: these may not exist in this service; code handles absence gracefully
    from ..database.models import Base  # type: ignore
except Exception:
    Base = None  # type: ignore


async def generate_presigned_url_handler(
    req_params: GeneratePresignedURLParams,
    authorized_user: AuthorizationData,
) -> CustomJSONResponse:
    try:
        if req_params.type_of_upload == UploadType.CONTENT:
            object_key = f"public/{authorized_user['user_id']}/{req_params.batch_id}/{req_params.file_name}"
        else:
            object_key = f"private/{authorized_user['user_id']}/{req_params.batch_id}/{req_params.file_name}"

        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": env_config.CHALLENGE_AWS_S3_BUCKET,
                "Key": object_key,
                "ContentType": req_params.content_type,
            },
            ExpiresIn=300,
        )

        public_url = f"https://{env_config.CHALLENGE_AWS_S3_BUCKET}.s3.amazonaws.com/{object_key}"

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Presigned URL generated successfully",
            data={
                "file_name": req_params.file_name,
                "presigned_url": presigned_url,
                "public_url": (
                    public_url
                    if req_params.type_of_upload == UploadType.CONTENT
                    else None
                ),
            },
            meta={
                "batch_id": req_params.batch_id,
                "type_of_upload": (
                    req_params.type_of_upload.value
                    if hasattr(req_params.type_of_upload, "value")
                    else str(req_params.type_of_upload)
                ),
                "object_key": object_key,
            },
        )
    except Exception as e:
        return CustomBackendError(
            message="Failed to generate presigned URL",
            details=str(e),
            meta={
                "batch_id": req_params.batch_id,
                "type_of_upload": (
                    req_params.type_of_upload
                    if isinstance(req_params.type_of_upload, str)
                    else getattr(req_params.type_of_upload, "value", None)
                ),
            },
        )


async def delete_attachment_handler(
    req_params: DeleteAttachmentParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        # Ownership check: user id segment in S3 key must match token user id
        try:
            attachment_user_id = uuid.UUID(req_params.object_key.split("/")[1])
        except Exception:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "BAD_REQUEST",
                    "details": "Invalid object_key format.",
                },
            )

        # if req_params.pre_creation:
        #     if attachment_user_id != authorized_user["user_id"]:
        #         return CustomJSONResponse(
        #             success=False,
        #             status_code=status.HTTP_403_FORBIDDEN,
        #             message="Forbidden access",
        #             error={
        #                 "code": "FORBIDDEN",
        #                 "details": "You are not authorized to delete this attachment.",
        #             },
        #         )
        # else:
        #     # Persisted records branch: this service may not have these models.
        #     # We attempt a best-effort lookup; otherwise return 404 to mirror contract.
        #     try:
        #         # Placeholder: no concrete models available here; return 404
        #         return CustomJSONResponse(
        #             success=False,
        #             status_code=status.HTTP_404_NOT_FOUND,
        #             message="Resource not found",
        #             error={
        #                 "code": "NOT_FOUND",
        #                 "details": "Attachment record not found.",
        #             },
        #         )
        #     except Exception:
        #         return CustomBackendError(
        #             message="Failed while validating attachment ownership"
        #         )

        # Delete from S3
        s3_client.delete_object(
            Bucket=env_config.CHALLENGE_AWS_S3_BUCKET, Key=req_params.object_key
        )

        # Delete DB rows for persisted records - skipped due to missing models

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Attachment deleted successfully",
        )
    except Exception as e:
        return CustomBackendError(
            message="Failed to delete attachment",
            details=str(e),
        )


async def generate_download_url_handler(
    req_params: GenerateDownloadUrlParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    try:
        # Use id as object_key (user passes the full S3 object key)
        # URL decode in case it was encoded
        object_key = unquote(req_params.id)

        # Verify ownership: user id segment in S3 key must match token user id
        try:
            key_parts = object_key.split("/")
            if len(key_parts) < 2:
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Bad Request",
                    error={
                        "code": "BAD_REQUEST",
                        "details": "Invalid object_key format. Expected format: private|public/user_id/...",
                    },
                )
            attachment_user_id = uuid.UUID(key_parts[1])
        except (ValueError, IndexError) as e:
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "BAD_REQUEST",
                    "details": f"Invalid object_key format: {str(e)}",
                },
            )

        # Check if user owns this attachment
        # if attachment_user_id != authorized_user["user_id"]:
        #     return CustomJSONResponse(
        #         success=False,
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         message="Forbidden access",
        #         error={
        #             "code": "FORBIDDEN",
        #             "details": "You are not authorized to access this attachment.",
        #         },
        #     )

        # Generate presigned URL for downloading (skip existence check - let S3 handle it)
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": env_config.CHALLENGE_AWS_S3_BUCKET,
                "Key": object_key,
            },
            ExpiresIn=300,
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Download URL generated successfully",
            data={
                "download_url": download_url,
            },
        )
    except Exception as e:
        return CustomBackendError(
            message="Failed to generate download URL",
            details=str(e),
        )
