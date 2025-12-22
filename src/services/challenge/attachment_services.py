import uuid
from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...middlewares.logging import logger
from ...configs.s3_config import s3_client
from ...configs.env_config import env_config
from ...schemas.default_schemas import AuthorizationData, UserRole
from ...database.challenge.models import Competition, CompetitionSubmission
from ...schemas.custom_responses import CustomJSONResponse, CustomBackendError
from ...schemas.challenge.attachment_requests import (
    DownloadSubmissionAttachmentsParams,
    SubmissionAttachmentChoice,
    GeneratePresignedURLParams,
    DeleteAttachmentParams,
)


async def generate_presigned_url_handler(
    req_params: GeneratePresignedURLParams,
    authorized_user: AuthorizationData,
) -> CustomJSONResponse:
    """
    Generates a presigned URL for uploading attachments to S3.

    Args:
        req_params (GeneratePresignedURLParams): The request body containing the presigned URL details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.

    Returns:
        CustomJSONResponse: A JSON response with the created presigned URL and relevant metadata.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        if req_params.md_attachment:
            object_key = f"public/{authorized_user['user_id']}/{req_params.batch_id}/{req_params.file_name}"
        else:
            object_key = f"temp/{authorized_user['user_id']}/{req_params.batch_id}/{req_params.file_name}"

        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": env_config.CHALLENGE_AWS_S3_BUCKET,
                "Key": object_key,
                "ContentType": "application/octet-stream",
            },
            ExpiresIn=300,
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Presigned URL generated successfully",
            data={
                "file_name": req_params.file_name,
                "presigned_url": presigned_url,
            },
            meta={
                "batch_id": req_params.batch_id,
                "object_key": (
                    f"https://{env_config.CHALLENGE_AWS_S3_BUCKET}.s3.amazonaws.com/{object_key}"
                    if req_params.md_attachment
                    else object_key
                ),
            },
        )
    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")

        return CustomBackendError(
            message="Presigned URL generation failed",
            details=f"An error occurred while generating the presigned URL. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def delete_temporary_attachment_handler(
    req_params: DeleteAttachmentParams,
    authorized_user: AuthorizationData,
) -> CustomJSONResponse:
    """
    Deletes temporary attachments from S3 based on the provided object key.

    Args:
        req_params (DeleteAttachmentsParams): The request body containing the attachment details.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.

    Returns:
        CustomJSONResponse: A JSON response indicating success or failure of the deletion operation.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        flag = req_params.object_key.split("/")[0]
        attachment_user_id = uuid.UUID(req_params.object_key.split("/")[1])

        if flag != "temp":
            logger.error(
                f"{authorized_user['email']} - Invalid object key: {req_params.object_key}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bad Request",
                error={
                    "code": "BAD_REQUEST",
                    "details": "Invalid object key format. Expected format: temp/batch_id/user_id/file_name",
                },
            )

        # Verify ownership: user id segment in S3 key must match token user id
        if attachment_user_id != authorized_user["user_id"]:
            logger.error(
                f"{authorized_user['email']} - Invalid user id in object key: {req_params.object_key}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden",
                error={
                    "code": "FORBIDDEN",
                    "details": "You are not authorized to delete this attachment.",
                },
            )

        # Delete from S3
        s3_client.delete_object(
            Bucket=env_config.CHALLENGE_AWS_S3_BUCKET, Key=req_params.object_key
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Attachment deleted successfully",
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")

        return CustomBackendError(
            message="Attachment deletion failed",
            details=f"An error occurred while deleting the attachment. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def download_rules_and_guidelines_handler(
    competition_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Generates a presigned URL for downloading rules and guidelines for a specific competition from S3.

    Args:
        competition_id (uuid.UUID): The ID of the competition.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response containing the presigned download URL for rules and guidelines.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        competition_stmt = select(Competition).where(Competition.id == competition_id)

        competition = await db_session.scalar(competition_stmt)

        if not competition:
            logger.error(
                f"{authorized_user['email']} - Invalid competition id: {competition_id}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Competition not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Competition not found for the provided id. Please check the id and try again.",
                },
            )

        if not competition.rules_and_guidelines:
            logger.error(
                f"{authorized_user['email']} - Rules and Guidelines not found for competition id: {competition_id}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Rules and Guidelines not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Rules and Guidelines not found for the provided competition id. Please check the id and try again.",
                },
            )

        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": env_config.CHALLENGE_AWS_S3_BUCKET,
                "Key": competition.rules_and_guidelines["s3_key"],
            },
            ExpiresIn=300,
        )

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Rules and Guidelines download URL generated successfully",
            data={"download_url": download_url},
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")

        return CustomBackendError(
            message="Rules and Guidelines download failed",
            details=f"An error occurred while downloading rules and guidelines. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def download_additional_assets_handler(
    competition_id: uuid.UUID,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
) -> CustomJSONResponse:
    """
    Generates a presigned URL for downloading additional assets for a specific competition from S3.

    Args:
        competition_id (uuid.UUID): The ID of the competition.
        authorized_user (AuthorizationData): The authenticated user's data, including their email, name, and ID.
        db_session (AsyncSession): The database session for accessing the primary database.

    Returns:
        CustomJSONResponse: A JSON response containing the presigned download URL for additional assets.
    """
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        competition_stmt = (
            select(Competition)
            .where(Competition.id == competition_id)
            .options(selectinload(Competition.datasets))
        )

        competition = await db_session.scalar(competition_stmt)

        if not competition:
            logger.error(
                f"{authorized_user['email']} - Invalid competition id: {competition_id}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Competition not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Competition does not exist for the provided id. Please check the id and try again.",
                },
            )

        if not competition.datasets.additional_assets:
            logger.error(
                f"{authorized_user['email']} - Additional Assets not found for competition id: {competition_id}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Additional Assets not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Additional Assets not found for the provided competition id. Please check the id and try again.",
                },
            )

        download_urls = []

        for asset in competition.datasets.additional_assets.values():
            object_key = asset["s3_key"]

            download_url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": env_config.CHALLENGE_AWS_S3_BUCKET,
                    "Key": object_key,
                },
                ExpiresIn=300,
            )

            download_urls.append(download_url)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Additional Assets download URL generated successfully",
            data={"download_urls": download_urls},
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")

        return CustomBackendError(
            message="Additional Assets download failed",
            details=f"An error occurred while downloading additional assets. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")


async def download_submission_attachments_handler(
    req_params: DownloadSubmissionAttachmentsParams,
    authorized_user: AuthorizationData,
    db_session: AsyncSession,
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
    logger.info(f"{authorized_user['email']} - Execution started")

    try:
        submission_stmt = select(CompetitionSubmission).where(
            CompetitionSubmission.id == req_params.submission_id
        )

        submission = await db_session.scalar(submission_stmt)

        if not submission:
            logger.error(
                f"{authorized_user['email']} - Invalid submission id: {req_params.submission_id}"
            )

            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Submission not found",
                error={
                    "code": "NOT_FOUND",
                    "details": "Submission not found for the provided id. Please check the id and try again.",
                },
            )

        if (
            authorized_user["user_role"] != UserRole.COS_ADMIN
            and authorized_user["user_id"] != submission.user_id
        ):
            return CustomJSONResponse(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Forbidden access",
                error={
                    "code": "FORBIDDEN",
                    "details": "You are not authorized to access this resource.",
                },
            )

        download_urls = []

        if req_params.choice == SubmissionAttachmentChoice.SOLUTION:
            if not submission.attachments:
                logger.error(
                    f"{authorized_user['email']} - Attachments not found for submission id: {req_params.submission_id}"
                )

                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Attachments not found",
                    error={
                        "code": "NOT_FOUND",
                        "details": "Attachments not found for the provided submission id. Please check the id and try again.",
                    },
                )
            attachments = submission.attachments
        else:
            if not submission.evaluation_attachments:
                logger.error(
                    f"{authorized_user['email']} - Evaluation Attachments not found for submission id: {req_params.submission_id}"
                )

                return CustomJSONResponse(
                    success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Evaluation Attachments not found",
                    error={
                        "code": "NOT_FOUND",
                        "details": "Evaluation Attachments not found for the provided submission id. Please check the id and try again.",
                    },
                )
            attachments = submission.evaluation_attachments

        for asset in attachments.values():
            object_key = asset["s3_key"]

            download_url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": env_config.CHALLENGE_AWS_S3_BUCKET,
                    "Key": object_key,
                },
                ExpiresIn=300,
            )

            download_urls.append(download_url)

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Submission Attachments download URL generated successfully",
            data={"download_urls": download_urls},
        )

    except Exception as e:
        logger.error(f"{authorized_user['email']} - Error: {str(e)}")

        return CustomBackendError(
            message="Submission Attachments download failed",
            details=f"An error occurred while downloading submission attachments. Please contact developers if the issue persists.",
        )

    finally:
        logger.info(f"{authorized_user['email']} - Execution completed")
