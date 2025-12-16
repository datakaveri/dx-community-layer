from fastapi import Body
from uuid import UUID


class BookmarkCompetitionParams:
    def __init__(
        self,
        competition_id: UUID = Body(..., description="ID of the challenge to bookmark"),
    ):
        self.competition_id = competition_id


class UnbookmarkCompetitionParams:
    def __init__(
        self,
        competition_id: UUID = Body(..., description="ID of the challenge to unbookmark"),
    ):
        self.competition_id = competition_id

