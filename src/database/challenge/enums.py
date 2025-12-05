import enum


class CompetitionStatusEnum(enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    EVALUATION = "EVALUATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PrizeTypeEnum(enum.Enum):
    CASH = "CASH"
    NO_CASH = "NO_CASH"
