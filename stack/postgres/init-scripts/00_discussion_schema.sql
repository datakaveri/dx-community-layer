-- =====================================================
-- Schema & Extensions
-- =====================================================
CREATE SCHEMA IF NOT EXISTS tgdx_dev;

CREATE EXTENSION IF NOT EXISTS plpgsql SCHEMA pg_catalog;
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA tgdx_dev;

-- =====================================================
-- ENUM TYPES
-- =====================================================

CREATE TYPE tgdx_dev.discussions_category_enum AS ENUM (
    'DATA_BANKS',
    'AI_MODELS',
    'USECASES',
    'CHALLENGES',
    'OTHERS'
);

CREATE TYPE tgdx_dev.discussions_type_enum AS ENUM (
    'GENERAL',
    'GETTING_STARTED',
    'PRODUCT_FEEDBACK',
    'PRODUCT_ANNOUNCEMENTS',
    'PUBLIC'
);

CREATE TYPE tgdx_dev.discussions_status_enum AS ENUM (
    'PENDING',
    'APPROVED',
    'CHANGES_REQUIRED',
    'REJECTED'
);

CREATE TYPE tgdx_dev.comments_status_enum AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'HIDDEN'
);

CREATE TYPE tgdx_dev.comment_report_status_enum AS ENUM (
    'PENDING',
    'ACCEPTED',
    'IGNORED'
);

CREATE TYPE tgdx_dev.comment_report_reason_enum AS ENUM (
    'DISALLOWED_AI_CONTENT',
    'UNRELATED_CONTENT',
    'HIGH_VOLUME_SPAM',
    'OFFENSIVE',
    'NSFW',
    'UNPROFESSIONAL',
    'JOB_POSTING',
    'LOW_VALUE',
    'WRONG_TOPIC',
    'SIMILAR_CONTENT',
    'PLAGIARISM',
    'SELF_PROMOTION',
    'VOTE_MANIPULATION',
    'OTHER'
);

-- =====================================================
-- USERS
-- =====================================================
CREATE TABLE tgdx_dev.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email varchar(256) NOT NULL UNIQUE,
    name varchar(256) NOT NULL,
    name_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(name, ''))
    ) STORED
);

-- =====================================================
-- TAGS
-- =====================================================
CREATE TABLE tgdx_dev.tags (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(256) NOT NULL,
    name_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(name, ''))
    ) STORED
);

-- =====================================================
-- DISCUSSIONS
-- =====================================================
CREATE TABLE tgdx_dev.discussions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    title varchar(256) NOT NULL,
    type tgdx_dev.discussions_type_enum NOT NULL DEFAULT 'PUBLIC',
    category tgdx_dev.discussions_category_enum NOT NULL DEFAULT 'OTHERS',
    sub_category varchar(256) NOT NULL,
    sub_category_id uuid,
    content text NOT NULL,
    status tgdx_dev.discussions_status_enum NOT NULL DEFAULT 'PENDING',
    is_active boolean NOT NULL DEFAULT true,
    zip_s3_key varchar(256),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(title, ''))
    ) STORED,
    sub_category_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(sub_category, ''))
    ) STORED,
    CONSTRAINT discussions_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

-- =====================================================
-- PINNED / BOOKMARKED / DELETED DISCUSSIONS
-- =====================================================
CREATE TABLE tgdx_dev.pinned_discussions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    pinned_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pinned_discussions_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT pinned_discussions_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.bookmarked_discussions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT bookmarked_discussions_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT bookmarked_discussions_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.deleted_discussions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    deleted_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT deleted_discussions_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT deleted_discussions_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

-- =====================================================
-- DISCUSSION META
-- =====================================================
CREATE TABLE tgdx_dev.discussion_tags (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    CONSTRAINT discussion_tags_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_tags_tag_fk
        FOREIGN KEY (tag_id)
        REFERENCES tgdx_dev.tags(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.discussion_attachments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    attachment_metadata jsonb NOT NULL,
    s3_key varchar(256) NOT NULL,
    uploaded_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT discussion_attachments_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.discussion_reactions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    emoji_code varchar(256),
    emoji_timestamp timestamptz,
    CONSTRAINT discussion_reactions_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_reactions_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.discussion_votes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    vote_timestamp timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT discussion_votes_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_votes_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_discussion_vote_user
        UNIQUE (discussion_id, user_id)
);

CREATE TABLE tgdx_dev.discussion_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    reviewer_id uuid NOT NULL,
    comment text NOT NULL,
    updated_status tgdx_dev.discussions_status_enum NOT NULL DEFAULT 'PENDING',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT discussion_reviews_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_reviews_reviewer_fk
        FOREIGN KEY (reviewer_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

-- =====================================================
-- COMMENTS
-- =====================================================
CREATE TABLE tgdx_dev.comments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    parent_id uuid,
    replied_to uuid,
    comment text NOT NULL,
    status tgdx_dev.comments_status_enum NOT NULL DEFAULT 'PENDING',
    approved_at timestamptz,
    approved_by uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT comments_discussion_fk
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_parent_fk
        FOREIGN KEY (parent_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_replied_to_fk
        FOREIGN KEY (replied_to)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_approved_by_fk
        FOREIGN KEY (approved_by)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.comment_attachments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id uuid NOT NULL,
    attachment_metadata jsonb NOT NULL,
    s3_key varchar(256) NOT NULL,
    uploaded_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT comment_attachments_comment_fk
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.comment_reactions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    emoji_code varchar(256),
    emoji_timestamp timestamptz,
    CONSTRAINT comment_reactions_comment_fk
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_reactions_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.comment_votes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    vote_timestamp timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT comment_votes_comment_fk
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_votes_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_comment_vote_user
        UNIQUE (comment_id, user_id)
);

CREATE TABLE tgdx_dev.deleted_comments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    deleted_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT deleted_comments_comment_fk
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT deleted_comments_user_fk
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE TABLE tgdx_dev.comment_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id uuid NOT NULL,
    reported_by_user_id uuid NOT NULL,
    reason tgdx_dev.comment_report_reason_enum NOT NULL,
    description text,
    status tgdx_dev.comment_report_status_enum NOT NULL DEFAULT 'PENDING',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at timestamptz,
    reviewed_by_admin_id uuid,
    CONSTRAINT comment_reports_comment_fk
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_reports_reported_by_fk
        FOREIGN KEY (reported_by_user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_reports_reviewed_by_fk
        FOREIGN KEY (reviewed_by_admin_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_comment_reports_comment_user
        UNIQUE (comment_id, reported_by_user_id)
);


-- Indexes
CREATE INDEX idx_discussions_user_id
    ON tgdx_dev.discussions(user_id);

CREATE INDEX idx_discussions_title_trgm
    ON tgdx_dev.discussions
    USING gin (title gin_trgm_ops);

CREATE INDEX idx_discussions_category
    ON tgdx_dev.discussions(category);

CREATE INDEX idx_discussions_status
    ON tgdx_dev.discussions(status);


CREATE INDEX idx_pinned_discussions_user
    ON tgdx_dev.pinned_discussions(user_id);

CREATE INDEX idx_pinned_discussions_discussion_user
    ON tgdx_dev.pinned_discussions(discussion_id, user_id);

CREATE INDEX idx_bookmarked_discussions_user
    ON tgdx_dev.bookmarked_discussions(user_id);

CREATE INDEX idx_bookmarked_discussions_discussion_user
    ON tgdx_dev.bookmarked_discussions(discussion_id, user_id);

CREATE INDEX idx_deleted_discussions_user
    ON tgdx_dev.deleted_discussions(user_id);

CREATE INDEX idx_deleted_discussions_discussion
    ON tgdx_dev.deleted_discussions(discussion_id);


CREATE INDEX idx_discussion_tags_discussion
    ON tgdx_dev.discussion_tags(discussion_id);

CREATE INDEX idx_discussion_tags_tag
    ON tgdx_dev.discussion_tags(tag_id);

CREATE INDEX idx_discussion_attachments_discussion
    ON tgdx_dev.discussion_attachments(discussion_id);

CREATE INDEX idx_discussion_attachments_metadata
    ON tgdx_dev.discussion_attachments
    USING gin (attachment_metadata);

CREATE INDEX idx_discussion_reactions_discussion
    ON tgdx_dev.discussion_reactions(discussion_id);

CREATE INDEX idx_discussion_votes_user
    ON tgdx_dev.discussion_votes(user_id);


CREATE INDEX idx_comments_discussion
    ON tgdx_dev.comments(discussion_id);

CREATE INDEX idx_comments_user
    ON tgdx_dev.comments(user_id);

CREATE INDEX idx_comments_parent
    ON tgdx_dev.comments(parent_id);

CREATE INDEX idx_comments_status
    ON tgdx_dev.comments(status);


CREATE INDEX idx_comment_attachments_comment
    ON tgdx_dev.comment_attachments(comment_id);

CREATE INDEX idx_comment_attachments_metadata
    ON tgdx_dev.comment_attachments
    USING gin (attachment_metadata);

CREATE INDEX idx_comment_reactions_comment
    ON tgdx_dev.comment_reactions(comment_id);

CREATE INDEX idx_comment_votes_user
    ON tgdx_dev.comment_votes(user_id);

CREATE INDEX idx_comment_reports_comment
    ON tgdx_dev.comment_reports(comment_id);

CREATE INDEX idx_comment_reports_status
    ON tgdx_dev.comment_reports(status);
