-- =====================================================
-- Schema & Extensions
-- =====================================================
CREATE SCHEMA IF NOT EXISTS tgdx_dev;

CREATE EXTENSION IF NOT EXISTS plpgsql SCHEMA pg_catalog;
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA tgdx_dev;

-- =====================================================
-- ENUM TYPES (BASE + EXTENDED)
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

CREATE TYPE tgdx_dev.reactions_vote_enum AS ENUM (
    'UP',
    'DOWN'
);

-- 🔹 NEW ENUMS (ADDED, NOTHING REMOVED)
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
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email varchar(256) NOT NULL,
    name varchar(256) NOT NULL,
    name_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(name, ''))
    ) STORED,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_email_key UNIQUE (email)
);

-- =====================================================
-- TAGS
-- =====================================================
CREATE TABLE tgdx_dev.tags (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name varchar(256) NOT NULL,
    name_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(name, ''))
    ) STORED,
    CONSTRAINT tags_pkey PRIMARY KEY (id)
);

-- =====================================================
-- DISCUSSIONS
-- =====================================================
CREATE TABLE tgdx_dev.discussions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    title varchar(256) NOT NULL,
    type tgdx_dev.discussions_type_enum DEFAULT 'PUBLIC' NOT NULL,
    category tgdx_dev.discussions_category_enum DEFAULT 'OTHERS' NOT NULL,
    sub_category varchar(256) NOT NULL,
    sub_category_id uuid,
    content text NOT NULL,
    status tgdx_dev.discussions_status_enum DEFAULT 'PENDING' NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    zip_s3_key varchar(256),
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    title_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(title, ''))
    ) STORED,
    sub_category_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(sub_category, ''))
    ) STORED,
    CONSTRAINT discussions_pkey PRIMARY KEY (id),
    CONSTRAINT discussions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_discussions_user_id ON tgdx_dev.discussions(user_id);
CREATE INDEX idx_discussions_title_trgm
ON tgdx_dev.discussions USING gin (title gin_trgm_ops);

-- =====================================================
-- DISCUSSION TAGS
-- =====================================================
CREATE TABLE tgdx_dev.discussion_tags (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    discussion_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    CONSTRAINT discussion_tags_pkey PRIMARY KEY (id),
    CONSTRAINT discussion_tags_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_tags_tag_id_fkey
        FOREIGN KEY (tag_id)
        REFERENCES tgdx_dev.tags(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_discussion_tags_discussion_id
ON tgdx_dev.discussion_tags(discussion_id);
CREATE INDEX idx_discussion_tags_tag_id
ON tgdx_dev.discussion_tags(tag_id);

-- =====================================================
-- DISCUSSION ATTACHMENTS
-- =====================================================
CREATE TABLE tgdx_dev.discussion_attachments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    discussion_id uuid NOT NULL,
    attachment_metadata jsonb NOT NULL,
    s3_key varchar(256) NOT NULL,
    uploaded_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT discussion_attachments_pkey PRIMARY KEY (id),
    CONSTRAINT discussion_attachments_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_discussion_attachments_discussion_id
ON tgdx_dev.discussion_attachments(discussion_id);
CREATE INDEX idx_discussion_attachments_attachment_metadata_gin
ON tgdx_dev.discussion_attachments USING gin (attachment_metadata);

-- =====================================================
-- DISCUSSION REACTIONS
-- =====================================================
CREATE TABLE tgdx_dev.discussion_reactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    emoji_code varchar(256),
    emoji_timestamp timestamptz,
    CONSTRAINT discussion_reactions_pkey PRIMARY KEY (id),
    CONSTRAINT discussion_reactions_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_reactions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_discussion_reactions_discussion_id
ON tgdx_dev.discussion_reactions(discussion_id);
CREATE INDEX idx_discussion_reactions_user_id
ON tgdx_dev.discussion_reactions(user_id);

-- =====================================================
-- DISCUSSION VOTES
-- =====================================================
CREATE TABLE tgdx_dev.discussion_votes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    vote_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT discussion_votes_pkey PRIMARY KEY (id),
    CONSTRAINT discussion_votes_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_votes_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_discussion_vote_user
        UNIQUE (discussion_id, user_id)
);

-- =====================================================
-- DISCUSSION REVIEWS
-- =====================================================
CREATE TABLE tgdx_dev.discussion_reviews (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    discussion_id uuid NOT NULL,
    reviewer_id uuid NOT NULL,
    comment text NOT NULL,
    updated_status tgdx_dev.discussions_status_enum DEFAULT 'PENDING' NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT discussion_reviews_pkey PRIMARY KEY (id),
    CONSTRAINT discussion_reviews_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT discussion_reviews_reviewer_id_fkey
        FOREIGN KEY (reviewer_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

-- =====================================================
-- COMMENTS
-- =====================================================
CREATE TABLE tgdx_dev.comments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    discussion_id uuid NOT NULL,
    user_id uuid NOT NULL,
    parent_id uuid,
    replied_to uuid,
    comment text NOT NULL,
    status tgdx_dev.comments_status_enum DEFAULT 'PENDING' NOT NULL,
    approved_at timestamptz,
    approved_by uuid,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT comments_pkey PRIMARY KEY (id),
    CONSTRAINT comments_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_parent_id_fkey
        FOREIGN KEY (parent_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_replied_to_fkey
        FOREIGN KEY (replied_to)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT comments_approved_by_fkey
        FOREIGN KEY (approved_by)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

-- =====================================================
-- COMMENT ATTACHMENTS
-- =====================================================
CREATE TABLE tgdx_dev.comment_attachments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comment_id uuid NOT NULL,
    attachment_metadata jsonb NOT NULL,
    s3_key varchar(256) NOT NULL,
    uploaded_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT comment_attachments_pkey PRIMARY KEY (id),
    CONSTRAINT comment_attachments_comment_id_fkey
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_comment_attachments_comment_id
ON tgdx_dev.comment_attachments(comment_id);
CREATE INDEX idx_comment_attachments_attachment_metadata_gin
ON tgdx_dev.comment_attachments USING gin (attachment_metadata);

-- =====================================================
-- COMMENT REACTIONS
-- =====================================================
CREATE TABLE tgdx_dev.comment_reactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    emoji_code varchar(256),
    emoji_timestamp timestamptz,
    CONSTRAINT comment_reactions_pkey PRIMARY KEY (id),
    CONSTRAINT comment_reactions_comment_id_fkey
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_reactions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

-- =====================================================
-- COMMENT VOTES
-- =====================================================
CREATE TABLE tgdx_dev.comment_votes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    vote_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT comment_votes_pkey PRIMARY KEY (id),
    CONSTRAINT comment_votes_comment_id_fkey
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_votes_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_comment_vote_user
        UNIQUE (comment_id, user_id)
);

-- =====================================================
-- DELETED COMMENTS
-- =====================================================
CREATE TABLE tgdx_dev.deleted_comments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    deleted_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT deleted_comments_pkey PRIMARY KEY (id),
    CONSTRAINT deleted_comments_comment_id_fkey
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT deleted_comments_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

-- =====================================================
-- COMMENT REPORTS
-- =====================================================
CREATE TABLE tgdx_dev.comment_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comment_id uuid NOT NULL,
    reported_by_user_id uuid NOT NULL,
    reason tgdx_dev.comment_report_reason_enum NOT NULL,
    description TEXT,
    status tgdx_dev.comment_report_status_enum DEFAULT 'PENDING' NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reviewed_at timestamptz,
    reviewed_by_admin_id uuid,
    CONSTRAINT comment_reports_pkey PRIMARY KEY (id),
    CONSTRAINT comment_reports_comment_id_fkey
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev.comments(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_reports_reported_by_user_id_fkey
        FOREIGN KEY (reported_by_user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT comment_reports_reviewed_by_admin_id_fkey
        FOREIGN KEY (reviewed_by_admin_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_comment_reports_comment_user
        UNIQUE (comment_id, reported_by_user_id)
);
