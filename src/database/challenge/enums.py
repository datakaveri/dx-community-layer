import enum


class CompetitionStatusEnum(enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    EVALUATION = "EVALUATION"
    PUBLISHED = "PUBLISHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PrizeTypeEnum(enum.Enum):
    CASH = "CASH"
    NO_CASH = "NO_CASH"
