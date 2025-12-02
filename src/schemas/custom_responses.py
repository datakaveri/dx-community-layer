from fastapi import HTTPException
from datetime import date, datetime
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def custom_jsonable_encoder(obj: Any) -> Any:
    return jsonable_encoder(
        obj,
        custom_encoder={
            datetime: lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S"),
            date: lambda d: d.strftime("%Y-%m-%d"),
        },
    )


class CustomJSONResponse(JSONResponse):
    def __init__(
        self,
        success: bool,
        status_code: int,
        message: str,
        data: dict | None = None,
        error: dict | None = None,
        meta: dict | None = None,
        **kwargs,
    ):
        """
        Initializes the custom JSON response with the provided parameters.

        # Args:
            `success` (bool): Whether the request was successful or not.
            `status_code` (int): HTTP status code of the response.
            `message` (str): A short message describing the response.
            `data` (dict | None): The actual data payload (optional).
            `error` (dict | None): Error details, if any (optional).
            `meta` (dict | None): Additional metadata, if any (optional).
            `**kwargs`: Additional arguments passed to the parent JSONResponse.

        # Returns:
            `CustomJSONResponse:` A JSON response with a dict and the provided HTTP status code.
        """
        content = {
            "success": success,
            "message": message,
            "data": data,
            "error": error,
            "meta": meta,
        }
        super().__init__(
            content=custom_jsonable_encoder(content), status_code=status_code, **kwargs
        )


class CustomBackendError(JSONResponse):
    def __init__(
        self,
        message: str,
        details: str = "Something went wrong. Please contact developers if the issue persists.",
        meta: Optional[Dict] = None,
        **kwargs,
    ):
        """
        Initializes the custom JSON response with the provided parameters.

        # Args:
            `message` (str): A short message describing the response.
            `details` (str): Details about the error.
            `**kwargs`: Additional arguments passed to the parent JSONResponse.

        # Returns:
            `CustomBackendErrorResponse:` A JSON response with a dict and HTTP status code 500.
        """
        content = {
            "success": False,
            "message": message,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "details": details,
            },
            "meta": meta,
        }
        super().__init__(
            content=custom_jsonable_encoder(content), status_code=500, **kwargs
        )


class CustomHttpException(HTTPException):
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str,
        error_details: str,
        headers: dict = None,
        **kwargs,
    ):
        """
        Initializes the custom HTTP exception with the provided parameters.

        # Args:
            `status_code` (int): HTTP status code of the response.
            `message` (str): A short message describing the response.
            `error_code` (str): A unique error code for the exception.
            `error_details` (str): Details about the error.

        # Returns:
            `CustomHttpException:` An HTTP exception with the provided status code and message.
        """
        self.status_code = status_code
        self.detail = {
            "success": False,
            "message": message,
            "data": None,
            "error": {
                "code": error_code,
                "details": error_details,
            },
            "meta": None,
        }
        self.headers = headers or {}

        super().__init__(
            status_code=status_code,
            detail=custom_jsonable_encoder(self.detail),
            headers=self.headers,
            **kwargs,
        )
