import enum
import uuid
from pydantic import BaseModel
from typing import List, Literal, TypedDict, Union


class UserRole(enum.Enum):
    CONSUMER = "consumer"
    ORG_ADMIN = "org_admin"
    COS_ADMIN = "cos_admin"


class AuthorizationData(TypedDict):
    user_id: uuid.UUID
    email: str
    username: str
    user_role: UserRole


class SuccessfulResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: Literal["This is initial route of TGDex-Discussion APIs!"]
    data: None
    error: None
    meta: None


class CreatedResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: Literal["Resource created successfully"]
    data: None
    error: None
    meta: None


class AcceptedResponse(BaseModel):
    success: bool = True
    message: Literal["Resource accepted successfully"]
    data: None
    error: None
    meta: None


class BadRequestError(BaseModel):
    code: Literal["BAD_REQUEST"]
    details: Literal[
        "The request you have made is invalid. Please try again later or contact support if the issue persists."
    ]


class BadRequestErrorResponse(BaseModel):
    success: bool = False
    message: Literal["Bad Request"]
    data: None
    error: BadRequestError
    meta: None


class UnauthorizedError(BaseModel):
    code: Literal["UNAUTHORIZED"]
    details: Union[
        Literal["Missing Authorization header. Please provide a valid Bearer token."],
        Literal["Invalid Authorization header. Please provide a valid Bearer token."],
        Literal["Invalid token. Please provide a valid Bearer token."],
        Literal["Token expired. Please refresh the token or login again."],
        Literal["Invalid token structure. Please provide a valid Bearer token."],
        Literal["Invalid token data. Please provide a valid Bearer token."],
    ]


class UnauthorizedErrorResponse(BaseModel):
    success: bool = False
    status_code: int = 401
    message: Literal["Unauthorized access"]
    data: None
    error: UnauthorizedError
    meta: None


class ForbiddenError(BaseModel):
    code: Literal["FORBIDDEN"]
    details: Literal[
        "You are not authorized to access this resource. Please contact support if required."
    ]


class ForbiddenErrorResponse(BaseModel):
    success: bool = False
    status_code: int = 403
    message: Literal["Forbidden access"]
    data: None
    error: ForbiddenError
    meta: None


class NotFoundError(BaseModel):
    code: Literal["NOT_FOUND"]
    details: Literal[
        "The requested resource could not be found. Please try again later or contact support if the issue persists."
    ]


class NotFoundErrorResponse(BaseModel):
    success: bool = False
    status_code: int = 404
    message: Literal["Resource not found"]
    data: None
    error: NotFoundError
    meta: None


class ConfilctError(BaseModel):
    code: Literal["CONFLICT"]
    details: Literal[
        "The resource you are trying to access is already in use. Please try again later or contact support if the issue persists."
    ]


class ConflictErrorResponse(BaseModel):
    success: bool = False
    status_code: int = 409
    message: Literal["Resource already exists"]
    data: None
    error: ConfilctError
    meta: None


class ValidationErrorDetails(BaseModel):
    field: str
    error: str


class ValidationErrorError(BaseModel):
    code: Literal["UNPROOCESSABLE_ENTITY"]
    details: List[ValidationErrorDetails]


class ValidationErrorResponse(BaseModel):
    success: bool = False
    message: Literal["Unprocessable Entity"]
    data: None = None
    error: ValidationErrorError
    meta: None = None


class TooManyRequestsError(BaseModel):
    code: Literal["TOO_MANY_REQUESTS"]
    details: Literal[
        "You have made too many requests. Please try again after {remaining_time} seconds or contact support if the issue persists."
    ]


class TooManyRequestsErrorResponse(BaseModel):
    success: bool = False
    status_code: int = 429
    message: Literal["Too Many Requests"]
    data: None
    error: TooManyRequestsError
    meta: None


class BackendError(BaseModel):
    code: Literal["INTERNAL_SERVER_ERROR"]
    details: Literal[
        "Something went wrong. Please try again later or contact support if the issue persists."
    ]


class BackendErrorResponse(BaseModel):
    success: bool = False
    status_code: int = 500
    message: Literal["Internal Server Error"]
    data: None
    error: BackendError
    meta: None


HOME_RESPONSE_MODEL = {
    200: {"model": SuccessfulResponse},
    500: {"model": BackendErrorResponse},
}
