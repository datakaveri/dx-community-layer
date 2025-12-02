from sqlalchemy import text
from fastapi.requests import Request
from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse


from ..middlewares.logging import logger
from ..configs.s3_config import s3_client
from ..configs.db_config import db_session
from ..configs.env_config import env_config
from ..schemas.custom_responses import CustomJSONResponse
from ..schemas.default_schemas import HOME_RESPONSE_MODEL

router = APIRouter(tags=["Utility APIs"])


@router.get(
    "/",
    description="<b>Default endpoint that serves as the entry point for the API.<b>",
    responses=HOME_RESPONSE_MODEL,
)
async def default(request: Request) -> CustomJSONResponse:
    """
    Default entry point for the TGDex-Discussion APIs.

    This is a public health check or informational endpoint to confirm that the
    Project microservice is running and accessible.

    Args:
        request (Request): The incoming HTTP request object.

    Returns:
        CustomJSONResponse: A simple success response indicating that the service is live.
    """
    logger.info(
        "%s - %s - %s",
        request.method,
        "public",
        "Default API is being called",
    )
    return CustomJSONResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="This is initial route of TGDex-Discussion APIs!",
    )


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    This endpoint is used to serve the favicon.ico file.
    """
    return RedirectResponse(url="https://fastapi.tiangolo.com/img/favicon.png")


@router.get(path="/healthz", include_in_schema=False)
async def healthz() -> CustomJSONResponse:
    """
    Health check endpoint to verify the service is running.

    Returns:
        CustomJSONResponse: A response indicating the service is healthy.
    """
    logger.info("Execution started")
    status_report = {
        "PostgreSQL DB": False,
        "AWS S3": False,
    }

    # Check PostgreSQL DB
    try:
        db_session.execute(text("SELECT 1"))
        status_report["PostgreSQL DB"] = True
    except Exception as e:
        logger.error(f"PostgreSQL DB check failed: {e}")
        status_report["PostgreSQL DB"] = False

    # Check AWS S3
    try:
        s3_client.head_bucket(Bucket=env_config.AWS_S3_BUCKET)
        status_report["AWS S3"] = True
    except Exception as e:
        logger.error(f"AWS S3 check failed: {e}")
        status_report["AWS S3"] = False

    if all(checks for checks in status_report.values()):
        logger.info("All services are healthy")

        return CustomJSONResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Service is healthy",
            data=status_report,
        )
    else:
        logger.warning("One or more services are not healthy")

        return CustomJSONResponse(
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Service is not healthy",
            error={
                "code": "INTERNAL_SERVER_ERROR",
                "details": "One or more services are not healthy. Please contact developers if issue persists.",
            },
            data=status_report,
        )
