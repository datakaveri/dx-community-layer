from typing import List, Literal, Optional

from pydantic import BaseModel

from ..default_schemas import (
    UnauthorizedErrorResponse,
    ForbiddenErrorResponse,
    NotFoundErrorResponse,
    ConflictErrorResponse,
    BackendErrorResponse,
)


class PrizePoolData(BaseModel):
    total_pool_amount: float
    currency: str
    prize_type: Optional[str] = None


class BookmarkedCompetitionItem(BaseModel):
    bookmark_id: str
    competition_id: str
    competition_title: Optional[str] = None
    competition_subtitle: Optional[str] = None
    competition_image_url: Optional[str] = None
    competition_status: Optional[str] = None
    bookmarked_at: str
    prize_pool: PrizePoolData
    days_left: Optional[int] = None
    participants_count: int


class BookmarkedCompetitionsData(BaseModel):
    bookmarked_competitions: List[BookmarkedCompetitionItem]


class BookmarkedCompetitionsMeta(BaseModel):
    total_bookmarks: int
    total_pages: int
    current_page: int
    limit: int


class BookmarkedCompetitionsSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: Literal["Bookmarked challenges retrieved successfully"]
    data: BookmarkedCompetitionsData
    error: None = None
    meta: BookmarkedCompetitionsMeta


class BookmarkCompetitionData(BaseModel):
    bookmark_id: str
    competition_id: str
    user_id: str
    is_active: bool
    created_at: str


class BookmarkCompetitionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 201
    message: Literal["Challenge bookmarked successfully"]
    data: BookmarkCompetitionData
    error: None = None
    meta: None = None


BOOKMARK_COMPETITION_RESPONSE_MODEL = {
    201: {"model": BookmarkCompetitionSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    409: {"model": ConflictErrorResponse},
    500: {"model": BackendErrorResponse},
}


class UnbookmarkCompetitionSuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: Literal["Challenge unbookmarked successfully"]
    data: None = None
    error: None = None
    meta: None = None


UNBOOKMARK_COMPETITION_RESPONSE_MODEL = {
    200: {"model": UnbookmarkCompetitionSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}


BOOKMARKED_COMPETITIONS_RESPONSE_MODEL = {
    200: {"model": BookmarkedCompetitionsSuccessResponse},
    401: {"model": UnauthorizedErrorResponse},
    403: {"model": ForbiddenErrorResponse},
    404: {"model": NotFoundErrorResponse},
    500: {"model": BackendErrorResponse},
}

