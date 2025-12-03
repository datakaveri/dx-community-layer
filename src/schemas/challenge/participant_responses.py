from typing import Literal

from pydantic import BaseModel

from ..default_schemas import (
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
    ConflictErrorResponse,
    NotFoundErrorResponse,
    BackendErrorResponse,
)


class JoinCompetitionData(BaseModel):
    participant_id: str
    competition_id: str
    user_id: str
    joined_at: str


class JoinCompetitionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: Literal["Successfully joined the competition"]
    data: JoinCompetitionData
    error: None = None
    meta: None = None


JOIN_COMPETITION_RESPONSE_MODEL = {
    201: {"model": JoinCompetitionSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    409: {"model": ConflictErrorResponse},
    500: {"model": BackendErrorResponse},
}


