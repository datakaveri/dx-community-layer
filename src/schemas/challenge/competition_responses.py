from pydantic import BaseModel

from ..default_schemas import (
    BackendErrorResponse,
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
    BadRequestErrorResponse,
)


class CreateCompetitionData(BaseModel):
    competition_id: str
    status: str


class CreateCompetitionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: str = "Resource created successfully"
    data: CreateCompetitionData
    error: None = None
    meta: None = None


CREATE_COMPETITION_RESPONSE_MODEL = {
    201: {"model": CreateCompetitionSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}


class CreateCompetitionData(BaseModel):
    competition_id: str
    status: str


class CreateCompetitionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: str = "Resource created successfully"
    data: CreateCompetitionData
    error: None = None
    meta: None = None


CREATE_COMPETITION_RESPONSE_MODEL = {
    201: {"model": CreateCompetitionSuccessResponse},
    400: {"model": BadRequestErrorResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    500: {"model": BackendErrorResponse},
}

