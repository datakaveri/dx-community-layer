import uuid
from sqlalchemy import (
    JSON,
    Computed,
    ForeignKey,
    Index,
    String,
    Text,
    Boolean,
    DateTime,
    func,
    Enum,
)
from typing import Any, Optional, List
from sqlalchemy.schema import MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ...configs.env_config import env_config
from .enums import CompetitionStatusEnum, PrizeTypeEnum


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(schema=env_config.CHALLENGE_DB_SCHEMA)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)})>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    competitions: Mapped[List["Competition"]] = relationship(
        back_populates="creator", cascade="all, delete-orphan"
    )
    submissions: Mapped[List["CompetitionSubmission"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    participants: Mapped[List["CompetitionParticipant"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    bookmarked_competitions: Mapped[List["BookmarkedCompetition"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detailed_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CompetitionStatusEnum] = mapped_column(
        PGEnum(
            CompetitionStatusEnum,
            name="competition_status_enum",
            schema=env_config.CHALLENGE_DB_SCHEMA,
            create_type=False,
        ),
        nullable=False,
        default=CompetitionStatusEnum.DRAFT,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{env_config.CHALLENGE_DB_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    published_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    scheduled_publish_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True)
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(300))
    constraints: Mapped[Optional[str]] = mapped_column(Text)
    rules_and_guidelines: Mapped[Optional[str]] = mapped_column(String(300))
    other_resources: Mapped[Optional[str]] = mapped_column(Text)

    # Full-text search
    title_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', COALESCE(title, ''))", persisted=True),
        nullable=True,
        index=True,
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="competitions")
    timelines: Mapped["CompetitionTimeline"] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    submissions: Mapped[List["CompetitionSubmission"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    prize_pools: Mapped["CompetitionPrizePool"] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    participants: Mapped[List["CompetitionParticipant"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    evaluations: Mapped[List["CompetitionEvaluation"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    datasets: Mapped[List["CompetitionDataset"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    bookmarked_competitions: Mapped[List["BookmarkedCompetition"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_competitions_created_by", "created_by"),
        Index(
            "idx_competitions_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )


class CompetitionTimeline(Base):
    __tablename__ = "competition_timelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            f"{env_config.CHALLENGE_DB_SCHEMA}.competitions.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    submission_starts_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submission_ends_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    evaluation_ends_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True)
    )

    competition: Mapped["Competition"] = relationship(back_populates="timelines")

    __table_args__ = (
        Index("idx_competition_timelines_competition_id", "competition_id"),
    )


class CompetitionSubmission(Base):
    __tablename__ = "competition_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            f"{env_config.CHALLENGE_DB_SCHEMA}.competitions.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{env_config.CHALLENGE_DB_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_disqualified: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[Optional[float]] = mapped_column()
    evaluation_comment: Mapped[Optional[str]] = mapped_column(Text)
    submission_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
    evaluation_attachments: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    # Full-text search
    title_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', COALESCE(title, ''))", persisted=True),
        nullable=True,
        index=True,
    )

    competition: Mapped["Competition"] = relationship(
        back_populates="submissions", foreign_keys=[competition_id]
    )
    user: Mapped["User"] = relationship(
        back_populates="submissions", foreign_keys=[user_id]
    )

    __table_args__ = (
        Index(
            "idx_competition_submissions_attachments_gin",
            "attachments",
            postgresql_using="gin",
        ),
        Index("idx_competition_submissions_competition_id", "competition_id"),
        Index("idx_competition_submissions_user_id", "user_id"),
    )


class CompetitionPrizePool(Base):
    __tablename__ = "competition_prize_pools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            f"{env_config.CHALLENGE_DB_SCHEMA}.competitions.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    prize_type: Mapped[PrizeTypeEnum] = mapped_column(
        PGEnum(
            PrizeTypeEnum,
            name="prize_type_enum",
            schema=env_config.CHALLENGE_DB_SCHEMA,
            create_type=False,
        ),
        default=PrizeTypeEnum.CASH,
        nullable=False,
    )
    total_pool_amount: Mapped[Optional[float]] = mapped_column(default=0.00)
    currency: Mapped[Optional[str]] = mapped_column(String(3), default="INR")
    prize_description: Mapped[Optional[str]] = mapped_column(Text)

    competition: Mapped["Competition"] = relationship(back_populates="prize_pools")

    __table_args__ = (
        Index("idx_competition_prize_pools_competition_id", "competition_id"),
    )


class CompetitionParticipant(Base):
    __tablename__ = "competition_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            f"{env_config.CHALLENGE_DB_SCHEMA}.competitions.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{env_config.CHALLENGE_DB_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    competition: Mapped["Competition"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship(back_populates="participants")

    __table_args__ = (
        Index("idx_competition_participants_competition_id", "competition_id"),
        Index("idx_competition_participants_user_id", "user_id"),
    )


class BookmarkedCompetition(Base):
    __tablename__ = "bookmarked_competitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            f"{env_config.CHALLENGE_DB_SCHEMA}.competitions.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{env_config.CHALLENGE_DB_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    competition: Mapped["Competition"] = relationship(
        back_populates="bookmarked_competitions"
    )
    user: Mapped["User"] = relationship(back_populates="bookmarked_competitions")

    __table_args__ = (
        Index("idx_bookmarked_competitions_competition_id", "competition_id"),
        Index("idx_bookmarked_competitions_user_id", "user_id"),
    )


class CompetitionEvaluation(Base):
    __tablename__ = "competition_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            f"{env_config.CHALLENGE_DB_SCHEMA}.competitions.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    evaluation_criteria: Mapped[Optional[str]] = mapped_column(Text)
    submission_criteria: Mapped[Optional[str]] = mapped_column(Text)

    competition: Mapped["Competition"] = relationship(back_populates="evaluations")

    __table_args__ = (
        Index("idx_competition_evaluations_competition_id", "competition_id"),
    )


class CompetitionDataset(Base):
    __tablename__ = "competition_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            f"{env_config.CHALLENGE_DB_SCHEMA}.competitions.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    datasets: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    ai_models: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    additional_assets: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    competition: Mapped["Competition"] = relationship(back_populates="datasets")

    __table_args__ = (
        Index(
            "idx_competition_datasets_datasets_gin", "datasets", postgresql_using="gin"
        ),
        Index(
            "idx_competition_datasets_ai_models_gin",
            "ai_models",
            postgresql_using="gin",
        ),
        Index(
            "idx_competition_datasets_additional_assets_gin",
            "additional_assets",
            postgresql_using="gin",
        ),
    )
