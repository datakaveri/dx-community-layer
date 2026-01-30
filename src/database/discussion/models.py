import uuid
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    Boolean,
    DateTime,
    func,
    Enum,
)
from sqlalchemy import Computed
from typing import Any, Optional, List
from sqlalchemy.schema import MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ...configs.env_config import env_config
from .enums import (
    DiscussionsTypeEnum,
    DiscussionsCategoryEnum,
    DiscussionsStatusEnum,
    CommentsStatusEnum,
    CommentReportReasonEnum,
    CommentReportStatusEnum
)


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(schema=env_config.DISCUSSION_DB_SCHEMA)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)})>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Full-text search
    name_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', COALESCE(name, ''))", persisted=True),
        nullable=True,
        index=True,
    )

    # Relationships
    discussions: Mapped[List["Discussion"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    pinned_discussions: Mapped[List["PinnedDiscussion"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_votes: Mapped[List["DiscussionVote"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_reactions: Mapped[List["DiscussionReaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_reviews: Mapped[List["DiscussionReview"]] = relationship(
        back_populates="reviewer",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Comment.user_id",
        lazy="raise",
    )
    comment_reactions: Mapped[List["CommentReaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    comment_votes: Mapped[List["CommentVote"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    bookmarked_discussions: Mapped[List["BookmarkedDiscussion"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    deleted_discussions: Mapped[List["DeletedDiscussion"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    deleted_comments: Mapped[List["DeletedComment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    replied_comments: Mapped[List["Comment"]] = relationship(
        back_populates="replied_to_user",
        cascade="all, delete-orphan",
        foreign_keys="Comment.replied_to",
        lazy="raise",
    )
    approved_comments: Mapped[List["Comment"]] = relationship(
        back_populates="approved_by_user",
        cascade="all, delete-orphan",
        foreign_keys="Comment.approved_by",
        lazy="raise",
    )


class Discussion(Base):
    __tablename__ = "discussions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[DiscussionsTypeEnum] = mapped_column(
        Enum(
            DiscussionsTypeEnum,
            name="discussions_type_enum",
            schema=env_config.DISCUSSION_DB_SCHEMA,
        ),
        default=DiscussionsTypeEnum.PUBLIC,
        nullable=False,
    )
    category: Mapped[DiscussionsCategoryEnum] = mapped_column(
        Enum(
            DiscussionsCategoryEnum,
            name="discussions_category_enum",
            schema=env_config.DISCUSSION_DB_SCHEMA,
        ),
        default=DiscussionsCategoryEnum.OTHERS,
        nullable=False,
    )
    sub_category: Mapped[str] = mapped_column(String(255), nullable=False)
    sub_category_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DiscussionsStatusEnum] = mapped_column(
        Enum(
            DiscussionsStatusEnum,
            name="discussions_status_enum",
            schema=env_config.DISCUSSION_DB_SCHEMA,
        ),
        default=DiscussionsStatusEnum.PENDING,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    zip_s3_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Full-text search
    title_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', COALESCE(title, ''))", persisted=True),
        nullable=True,
        index=True,
    )
    sub_category_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', COALESCE(sub_category, ''))", persisted=True),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="discussions",
        foreign_keys=[user_id],
        lazy="raise",
    )
    pinned_discussions: Mapped[List["PinnedDiscussion"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_votes: Mapped[List["DiscussionVote"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_reactions: Mapped[List["DiscussionReaction"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_tags: Mapped[List["DiscussionTag"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_attachments: Mapped[List["DiscussionAttachment"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    discussion_reviews: Mapped[List["DiscussionReview"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    bookmarked_discussions: Mapped[List["BookmarkedDiscussion"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_discussions_user_id", "user_id"),
        Index("idx_discussions_title_trgm", "title", postgresql_using="gin"),
    )


class PinnedDiscussion(Base):
    __tablename__ = "pinned_discussions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pinned_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    discussion: Mapped["Discussion"] = relationship(
        back_populates="pinned_discussions",
        foreign_keys=[discussion_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="pinned_discussions",
        foreign_keys=[user_id],
        lazy="raise",
    )


class DeletedDiscussion(Base):
    __tablename__ = "deleted_discussions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="deleted_discussions",
        foreign_keys=[user_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (Index("idx_deleted_discussions_user_id", "user_id"),)


class DiscussionVote(Base):
    __tablename__ = "discussion_votes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vote_timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    discussion: Mapped["Discussion"] = relationship(
        back_populates="discussion_votes",
        foreign_keys=[discussion_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="discussion_votes",
        foreign_keys=[user_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_discussion_votes_user_id", "user_id"),
        Index("idx_discussion_votes_discussion_id", "discussion_id"),
    )


class DiscussionReaction(Base):
    __tablename__ = "discussion_reactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    emoji_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emoji_timestamp: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    discussion: Mapped["Discussion"] = relationship(
        back_populates="discussion_reactions",
        foreign_keys=[discussion_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="discussion_reactions",
        foreign_keys=[user_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_discussion_reactions_discussion_id", "discussion_id"),
        Index("idx_discussion_reactions_user_id", "user_id"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Full-text search
    name_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', COALESCE(name, ''))", persisted=True),
        nullable=True,
        index=True,
    )

    # Relationships
    discussion_tags: Mapped[List["DiscussionTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class DiscussionTag(Base):
    __tablename__ = "discussion_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    tag: Mapped["Tag"] = relationship(
        back_populates="discussion_tags",
        foreign_keys=[tag_id],
        lazy="raise",
    )
    discussion: Mapped["Discussion"] = relationship(
        back_populates="discussion_tags",
        foreign_keys=[discussion_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_discussion_tags_tag_id", "tag_id"),
        Index("idx_discussion_tags_discussion_id", "discussion_id"),
    )


class DiscussionAttachment(Base):
    __tablename__ = "discussion_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attachment_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, index=True
    )
    s3_key: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    discussion: Mapped["Discussion"] = relationship(
        back_populates="discussion_attachments",
        foreign_keys=[discussion_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_discussion_attachments_discussion_id", "discussion_id"),
        Index(
            "idx_discussion_attachments_attachment_metadata_gin",
            "attachment_metadata",
            postgresql_using="gin",
        ),
    )


class DiscussionReview(Base):
    __tablename__ = "discussion_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    updated_status: Mapped[DiscussionsStatusEnum] = mapped_column(
        Enum(
            DiscussionsStatusEnum,
            name="discussions_status_enum",
            schema=env_config.DISCUSSION_DB_SCHEMA,
        ),
        default=DiscussionsStatusEnum.PENDING,
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    discussion: Mapped["Discussion"] = relationship(
        back_populates="discussion_reviews",
        foreign_keys=[discussion_id],
        lazy="raise",
    )
    reviewer: Mapped["User"] = relationship(
        back_populates="discussion_reviews",
        foreign_keys=[reviewer_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_discussion_reviews_discussion_id", "discussion_id"),
        Index("idx_discussion_reviews_reviewer_id", "reviewer_id"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    replied_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    status: Mapped[CommentsStatusEnum] = mapped_column(
        Enum(
            CommentsStatusEnum,
            name="comments_status_enum",
            schema=env_config.DISCUSSION_DB_SCHEMA,
        ),
        nullable=False,
        server_default=CommentsStatusEnum.PENDING.value,
    )
    approved_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    discussion: Mapped["Discussion"] = relationship(
        back_populates="comments",
        foreign_keys=[discussion_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="comments",
        foreign_keys=[user_id],
        lazy="raise",
    )
    sub_comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="parent_comment",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
        lazy="raise",
    )
    parent_comment: Mapped[Optional["Comment"]] = relationship(
        "Comment",
        back_populates="sub_comments",
        remote_side=[id],
        foreign_keys=[parent_id],
        lazy="raise",
    )
    replied_to_user: Mapped[Optional["User"]] = relationship(
        back_populates="replied_comments",
        foreign_keys=[replied_to],
        lazy="raise",
    )
    approved_by_user: Mapped[Optional["User"]] = relationship(
        back_populates="approved_comments",
        foreign_keys=[approved_by],
        lazy="raise",
    )
    comment_reactions: Mapped[List["CommentReaction"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    comment_votes: Mapped[List["CommentVote"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    comment_attachments: Mapped[List["CommentAttachment"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    deleted_comments: Mapped[List["DeletedComment"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    comment_reports: Mapped[List["CommentReport"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_comments_discussion_id", "discussion_id"),
        Index("idx_comments_user_id", "user_id"),
        Index("idx_comments_parent_id", "parent_id"),
        Index("idx_comments_replied_to", "replied_to"),
        Index("idx_comments_approved_by", "approved_by"),
    )


class DeletedComment(Base):
    __tablename__ = "deleted_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    comment: Mapped["Comment"] = relationship(
        back_populates="deleted_comments",
        foreign_keys=[comment_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="deleted_comments",
        foreign_keys=[user_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_deleted_comments_comment_id", "comment_id"),
        Index("idx_deleted_comments_user_id", "user_id"),
    )


class CommentVote(Base):
    __tablename__ = "comment_votes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vote_timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    comment: Mapped["Comment"] = relationship(
        back_populates="comment_votes",
        foreign_keys=[comment_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="comment_votes",
        foreign_keys=[user_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_comment_votes_user_id", "user_id"),
        Index("idx_comment_votes_comment_id", "comment_id"),
    )


class CommentReaction(Base):
    __tablename__ = "comment_reactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    emoji_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emoji_timestamp: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    comment: Mapped["Comment"] = relationship(
        back_populates="comment_reactions",
        foreign_keys=[comment_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="comment_reactions",
        foreign_keys=[user_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_comment_reactions_comment_id", "comment_id"),
        Index("idx_comment_reactions_user_id", "user_id"),
    )


class CommentAttachment(Base):
    __tablename__ = "comment_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attachment_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, index=True
    )
    s3_key: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    comment: Mapped["Comment"] = relationship(
        back_populates="comment_attachments",
        foreign_keys=[comment_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_comment_attachments_comment_id", "comment_id"),
        Index(
            "idx_comment_attachments_attachment_metadata_gin",
            "attachment_metadata",
            postgresql_using="gin",
        ),
    )


class BookmarkedDiscussion(Base):
    __tablename__ = "bookmarked_discussions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    discussion: Mapped["Discussion"] = relationship(
        back_populates="bookmarked_discussions",
        foreign_keys=[discussion_id],
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="bookmarked_discussions",
        foreign_keys=[user_id],
        lazy="raise",
    )

    # Indexes & Constraints
    __table_args__ = (
        Index("idx_bookmarked_discussions_discussion_id", "discussion_id"),
        Index("idx_bookmarked_discussions_user_id", "user_id"),
    )

class CommentReport(Base):
    __tablename__ = "comment_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reason: Mapped[CommentReportReasonEnum] = mapped_column(
        Enum(CommentReportReasonEnum,
             name="comment_report_reason_enum",
             schema=env_config.DISCUSSION_DB_SCHEMA
             ),
        nullable=False,
    )
    description = Column(Text, nullable=True)

    status: Mapped[CommentReportStatusEnum] = mapped_column(
        Enum(
            CommentReportStatusEnum,
            name="comment_report_status_enum",
            schema=env_config.DISCUSSION_DB_SCHEMA,
        ),
        nullable=False,
        server_default=CommentReportStatusEnum.PENDING.value,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    reviewed_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reviewed_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    comment: Mapped["Comment"] = relationship(
        back_populates="comment_reports",
        foreign_keys=[comment_id],
        lazy="raise",
    )

    reported_by_user: Mapped["User"] = relationship(
        foreign_keys=[reported_by_user_id],
        lazy="raise",
    )

    reviewed_by_admin: Mapped[Optional["User"]] = relationship(
        foreign_keys=[reviewed_by_admin_id],
        lazy="raise",
    )

    __table_args__ = (
        Index("idx_comment_reports_comment_id", "comment_id"),
        Index("idx_comment_reports_reported_by_user_id", "reported_by_user_id"),
        Index("idx_comment_reports_status", "status"),
        Index(
            "uq_comment_reports_comment_user",
            "comment_id",
            "reported_by_user_id",
            unique=True,
        ),
    )
