import uuid
from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from ..middlewares.logging import logger
from ..configs.s3_config import s3_client
from ..configs.env_config import env_config
from ..database.models import CommentAttachment, DiscussionAttachment
from ..schemas.attachment_requests import (
    DeleteAttachmentParams,
    GenerateDownloadUrlParams,
    GeneratePresignedURLParams,
    UploadType,
)

from ..schemas.default_schemas import AuthorizationData
from ..schemas.custom_responses import CustomJSONResponse, CustomBackendError


async def generate_presigned_url_handler(
    req_params: GeneratePresignedURLParams,
    authorized_user: AuthorizationData,
) -> CustomJSONResponse:
    """
    Generates a public presigned URL for a file as per the type of upload.

    Args:
        req_params (GeneratePresignedURLParams): The request body containing the presigned URL details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.

    Returns:
        CustomJSONResponse: A JSON response with the created discussion details and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        if req_params.type_of_upload == UploadType.CONTENT:
            object_key = f"public/{authorized_user['user_id']}/{req_params.batch_id}/{req_params.file_name}"
        else:
            object_key = f"private/{authorized_user['user_id']}/{req_params.batch_id}/{req_params.file_name}"

        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": env_config.AWS_S3_BUCKET,
                "Key": object_key,
                "ContentType": "application/octet-stream",
            },
            ExpiresIn=300,
        )

        public_url = f"https://{env_config.AWS_S3_BUCKET}.s3.amazonaws.com/{object_key}"

        logger.info(
            f"{authorized_user['email']} - Presigned URL generated successfully for file: {req_params.file_name} and type of upload: {req_params.type_of_upload}"
        )
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
                "type_of_upload": req_params.type_of_upload,
                "object_key": object_key,
            },
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to generate presigned URL",
            details="An error occurred while generating the presigned URL. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def delete_attachment_handler(
    req_params: DeleteAttachmentParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
):
    """
    Deletes a discussion attachment from S3 and DB for the authenticated user.

    Args:
        req_params (DeleteAttachmentParams): The request body containing the attachment details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response indicating success or failure of the deletion operation.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        comment_attachment = None
        discussion_attachment = None
        attachment_user_id = uuid.UUID(req_params.object_key.split("/")[1])

        if req_params.pre_creation:
            if attachment_user_id != authorized_user["user_id"]:
                logger.error(f"{authorized_user['email']} - Forbidden access")
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="Forbidden access",
                    error={
                        "code": "FORBIDDEN",
                        "message": "You do not have permission to delete this attachment. Please contact support if required.",
                    },
                )

        else:
            if req_params.type == UploadType.ATTACHMENT:
                stmt = (
                    select(DiscussionAttachment)
                    .filter(DiscussionAttachment.s3_key == req_params.object_key)
                    .options(selectinload(DiscussionAttachment.discussion))
                )
                result = await db_session.execute(stmt)
                discussion_attachment = result.scalar_one_or_none()

                if not discussion_attachment:
                    logger.error(f"{authorized_user['email']} - Attachment not found")
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_404_NOT_FOUND,
                        message="Attachment not found",
                        error={
                            "code": "NOT_FOUND",
                            "message": "The attachment you are trying to delete does not exist. Please try again later or contact support if the issue persists.",
                        },
                    )

                # Check ownership
                if (
                    discussion_attachment.discussion.user_id
                    != authorized_user["user_id"]
                ):
                    logger.error(f"{authorized_user['email']} - Forbidden access")
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_403_FORBIDDEN,
                        message="Forbidden access",
                        error={
                            "code": "FORBIDDEN",
                            "message": "You do not have permission to delete this attachment. Please contact support if required.",
                        },
                    )

            elif req_params.type == UploadType.COMMENT:
                stmt = (
                    select(CommentAttachment)
                    .filter(CommentAttachment.s3_key == req_params.object_key)
                    .options(selectinload(CommentAttachment.comment))
                )
                result = await db_session.execute(stmt)
                comment_attachment = result.scalar_one_or_none()

                if not comment_attachment:
                    logger.error(f"{authorized_user['email']} - Attachment not found")
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_404_NOT_FOUND,
                        message="Attachment not found",
                        error={
                            "code": "NOT_FOUND",
                            "message": "The attachment you are trying to delete does not exist. Please try again later or contact support if the issue persists.",
                        },
                    )

                # Check ownership
                if comment_attachment.comment.user_id != authorized_user["user_id"]:
                    logger.error(f"{authorized_user['email']} - Forbidden access")
                    return CustomJSONResponse(
                        success=False,
                        status_code=status.HTTP_403_FORBIDDEN,
                        message="Forbidden access",
                        error={
                            "code": "FORBIDDEN",
                            "message": "You do not have permission to delete this attachment. Please contact support if required.",
                        },
                    )

        # Delete from S3
        try:
            s3_client.delete_object(
                Bucket=env_config.AWS_S3_BUCKET,
                Key=req_params.object_key,
            )
        except ClientError as e:
            logger.error(f"{authorized_user['email']} - Error: {str(e)}")
            return CustomBackendError(
                message="Failed to delete attachment",
                details="An error occurred while deleting the attachment. Please contact developers if the issue persists.",
            )

        # Delete from DB
        if not req_params.pre_creation:
            if req_params.type == UploadType.COMMENT and comment_attachment:
                await db_session.delete(comment_attachment)
                await db_session.commit()
            elif req_params.type == UploadType.ATTACHMENT and discussion_attachment:
                await db_session.delete(discussion_attachment)
                await db_session.commit()

        logger.info(f"{authorized_user['email']} - Attachment deleted successfully")
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Attachment deleted successfully",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to delete attachment",
            details="An error occurred while deleting the attachment. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def generate_download_url_handler(
    req_params: GenerateDownloadUrlParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Generates a presigned download URL for a discussion attachment.

    Args:
        attachment_id (str): The S3 key or attachment ID in DiscussionAttachment.
        authorized_user (AuthorizationData): The authenticated user details.
        db_session (AsyncSession): DB session for any validations (optional).

    Returns:
        CustomJSONResponse: JSON response containing the presigned download URL.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        s3_key = None
        file_name = None

        if req_params.type == UploadType.ATTACHMENT:
            stmt = (
                select(DiscussionAttachment)
                .filter(DiscussionAttachment.id == req_params.id)
                .options(selectinload(DiscussionAttachment.discussion))
            )
            result = await db_session.execute(stmt)
            discussion_attachment = result.scalar_one_or_none()

            if not discussion_attachment:
                logger.error(f"{authorized_user['email']} - Attachment not found")
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Attachment not found",
                    error={
                        "code": "NOT_FOUND",
                        "message": "The attachment you are trying to download does not exist. Please try again later or contact support if the issue persists.",
                    },
                )

            s3_key = discussion_attachment.s3_key
            file_name = discussion_attachment.attachment_metadata["file_name"]

        elif req_params.type == UploadType.COMMENT:
            stmt = (
                select(CommentAttachment)
                .filter(CommentAttachment.id == req_params.id)
                .options(selectinload(CommentAttachment.comment))
            )
            result = await db_session.execute(stmt)
            comment_attachment = result.scalar_one_or_none()

            if not comment_attachment:
                logger.error(f"{authorized_user['email']} - Attachment not found")
                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Attachment not found",
                    error={
                        "code": "NOT_FOUND",
                        "message": "The attachment you are trying to download does not exist. Please try again later or contact support if the issue persists.",
                    },
                )

            s3_key = comment_attachment.s3_key
            file_name = comment_attachment.attachment_metadata["file_name"]

        if not s3_client.head_object(
            Bucket=env_config.AWS_S3_BUCKET,
            Key=s3_key,
        ):
            logger.error(f"{authorized_user['email']} - Attachment not found in S3")
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Attachment not found",
                error={
                    "code": "NOT_FOUND",
                    "message": "The attachment you are trying to download does not exist. Please try again later or contact support if the issue persists.",
                },
            )

        # Generate presigned download URL
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": env_config.AWS_S3_BUCKET,
                "Key": s3_key,
            },
            ExpiresIn=300,
        )

        logger.info(
            f"{authorized_user['email']} - Download URL generated successfully for {file_name}"
        )
        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Download URL generated successfully",
            data={
                "file_name": file_name,
                "download_url": download_url,
            },
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")
        return CustomBackendError(
            message="Failed to generate download URL",
            details="An error occurred while generating the download URL. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
