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
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	email varchar(256) NOT NULL,
	"name" varchar(256) NOT NULL,

	name_vector tsvector GENERATED ALWAYS AS (
    to_tsvector(
        'simple'::regconfig, COALESCE(name, ''::character varying)::text
        )
    ) STORED NULL,

	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_users_name_vector
    ON tgdx_dev.users
    USING gin (name_vector);

-- =====================================================
-- TAGS
-- =====================================================
CREATE TABLE tgdx_dev.tags (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(256) NOT NULL,
	name_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple'::regconfig, COALESCE(name, ''::character varying)::text)
    ) STORED NULL,    

	CONSTRAINT tags_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_tags_name_vector
    ON tgdx_dev.tags
    USING gin (name_vector);

-- =====================================================
-- DISCUSSIONS
-- =====================================================
CREATE TABLE tgdx_dev.discussions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id uuid NOT NULL,
	title varchar(256) NOT NULL,
	"type" tgdx_dev."discussions_type_enum" DEFAULT 'PUBLIC'::tgdx_dev.discussions_type_enum NOT NULL,
	category tgdx_dev."discussions_category_enum" DEFAULT 'OTHERS'::tgdx_dev.discussions_category_enum NOT NULL,
	sub_category varchar(256) NOT NULL,
	sub_category_id uuid NULL,
	"content" text NOT NULL,
	status tgdx_dev."discussions_status_enum" DEFAULT 'PENDING'::tgdx_dev.discussions_status_enum NOT NULL,
	is_active bool DEFAULT true NOT NULL,
	zip_s3_key varchar(256) DEFAULT NULL::character varying NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	title_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple'::regconfig, COALESCE(title, ''::character varying)::text)
    ) STORED NULL,
	sub_category_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple'::regconfig, COALESCE(sub_category, ''::character varying)::text)
    ) STORED NULL,

	CONSTRAINT discussions_pkey PRIMARY KEY (id),
	CONSTRAINT discussions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_discussions_title_trgm 
    ON tgdx_dev.discussions
    USING gin (title gin_trgm_ops);
CREATE INDEX idx_discussions_user_id
    ON tgdx_dev.discussions
    USING btree (user_id);
CREATE INDEX idx_discussions_title_vector
    ON tgdx_dev.discussions
    USING gin (title_vector);
CREATE INDEX idx_discussions_sub_category_vector
    ON tgdx_dev.discussions
    USING gin (sub_category_vector);


-- =====================================================
-- PINNED / BOOKMARKED / DELETED DISCUSSIONS
-- =====================================================
CREATE TABLE tgdx_dev.pinned_discussions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	pinned_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT pinned_discussions_pkey PRIMARY KEY (id),
	CONSTRAINT pinned_discussions_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
	CONSTRAINT pinned_discussions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_pinned_discussions_discussion_id
    ON tgdx_dev.pinned_discussions
    USING btree (discussion_id);
CREATE INDEX idx_pinned_discussions_discussion_user
    ON tgdx_dev.pinned_discussions
    USING btree (discussion_id, user_id);
CREATE INDEX idx_pinned_discussions_user_id
    ON tgdx_dev.pinned_discussions
    USING btree (user_id);


CREATE TABLE tgdx_dev.bookmarked_discussions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT bookmarked_discussions_pkey PRIMARY KEY (id),
	CONSTRAINT bookmarked_discussions_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
	CONSTRAINT bookmarked_discussions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_bookmarked_discussions_discussion_id
    ON tgdx_dev.bookmarked_discussions
    USING btree (discussion_id);
CREATE INDEX idx_bookmarked_discussions_discussion_user
    ON tgdx_dev.bookmarked_discussions
    USING btree (discussion_id, user_id);
CREATE INDEX idx_bookmarked_discussions_user_id
    ON tgdx_dev.bookmarked_discussions
    USING btree (user_id);


CREATE TABLE tgdx_dev.deleted_discussions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	deleted_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT deleted_discussions_pkey PRIMARY KEY (id),
	CONSTRAINT deleted_discussions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_deleted_discussions_discussion_id
    ON tgdx_dev.deleted_discussions
    USING btree (discussion_id);
CREATE INDEX idx_deleted_discussions_user_id
    ON tgdx_dev.deleted_discussions
    USING btree (user_id);


-- =====================================================
-- DISCUSSION META
-- =====================================================
CREATE TABLE tgdx_dev.discussion_tags (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	tag_id uuid NOT NULL,
	discussion_id uuid NOT NULL,

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
    ON tgdx_dev.discussion_tags
    USING btree (discussion_id);
CREATE INDEX idx_discussion_tags_tag_id
    ON tgdx_dev.discussion_tags
    USING btree (tag_id);


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

CREATE INDEX idx_discussion_attachments_attachment_metadata_gin
    ON tgdx_dev.discussion_attachments
    USING gin (attachment_metadata);
CREATE INDEX idx_discussion_attachments_discussion_id
    ON tgdx_dev.discussion_attachments
    USING btree (discussion_id);


CREATE TABLE tgdx_dev.discussion_reactions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	emoji_code varchar(256) DEFAULT NULL::character varying NULL,
	emoji_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT discussion_reactions_pkey PRIMARY KEY (id),
    CONSTRAINT uq_discussion_reaction_user
        UNIQUE (discussion_id, user_id),
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
    ON tgdx_dev.discussion_reactions
    USING btree (discussion_id);
CREATE INDEX idx_discussion_reactions_user_id
    ON tgdx_dev.discussion_reactions
    USING btree (user_id);


CREATE TABLE tgdx_dev.discussion_votes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	vote_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT discussion_votes_pkey PRIMARY KEY (id),
    CONSTRAINT uq_discussion_vote_user
        UNIQUE (discussion_id, user_id),
	CONSTRAINT discussion_votes_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
	CONSTRAINT discussion_votes_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_discussion_votes_discussion_id
    ON tgdx_dev.discussion_votes
    USING btree (discussion_id);
CREATE INDEX idx_discussion_votes_discussion_user
    ON tgdx_dev.discussion_votes
    USING btree (discussion_id, user_id);
CREATE INDEX idx_discussion_votes_user_id
    ON tgdx_dev.discussion_votes
    USING btree (user_id);


CREATE TABLE tgdx_dev.discussion_reviews (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	reviewer_id uuid NOT NULL,
	"comment" text NULL,
	updated_status tgdx_dev."discussions_status_enum" DEFAULT 'PENDING'::tgdx_dev.discussions_status_enum NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT discussion_reviews_pkey PRIMARY KEY (id),
	CONSTRAINT discussion_reviews_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
	CONSTRAINT discussion_reviews_reviewer_id
        FOREIGN KEY (reviewer_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_discussion_reviews_discussion_id
    ON tgdx_dev.discussion_reviews
    USING btree (discussion_id);
CREATE INDEX idx_discussion_reviews_reviewer_id
    ON tgdx_dev.discussion_reviews
    USING btree (reviewer_id);


-- =====================================================
-- COMMENTS
-- =====================================================
CREATE TABLE tgdx_dev."comments" (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	parent_id uuid NULL,
	replied_to uuid NULL,
	"comment" text NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	status tgdx_dev."comments_status_enum" DEFAULT 'PENDING'::tgdx_dev.comments_status_enum NOT NULL,
	approved_at timestamptz NULL,
	approved_by uuid NULL,

	CONSTRAINT comments_pkey PRIMARY KEY (id),
	CONSTRAINT comments_discussion_id_fkey
        FOREIGN KEY (discussion_id)
        REFERENCES tgdx_dev.discussions(id)
        ON DELETE CASCADE,
	CONSTRAINT comments_parent_id_fkey
        FOREIGN KEY (parent_id)
        REFERENCES tgdx_dev."comments"(id)
        ON DELETE CASCADE,
	CONSTRAINT comments_replied_to_fkey
        FOREIGN KEY (replied_to)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
	CONSTRAINT comments_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_comments_approved_by
    ON tgdx_dev.comments
    USING btree (approved_by);
CREATE INDEX idx_comments_discussion_id
    ON tgdx_dev.comments
    USING btree (discussion_id);
CREATE INDEX idx_comments_parent_id
    ON tgdx_dev.comments
    USING btree (parent_id);
CREATE INDEX idx_comments_replied_to
    ON tgdx_dev.comments
    USING btree (replied_to);
CREATE INDEX idx_comments_user_id
    ON tgdx_dev.comments
    USING btree (user_id);


CREATE TABLE tgdx_dev.comment_attachments (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	attachment_metadata jsonb NOT NULL,
	s3_key varchar(256) NOT NULL,
	uploaded_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT comment_attachments_pkey PRIMARY KEY (id),
	CONSTRAINT comment_attachments_discussion_id_fkey
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev."comments"(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_comment_attachments_attachment_metadata_gin 
    ON tgdx_dev.comment_attachments
    USING gin (attachment_metadata);
CREATE INDEX idx_comment_attachments_comment_id 
    ON tgdx_dev.comment_attachments
    USING btree (comment_id);


CREATE TABLE tgdx_dev.comment_reactions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	user_id uuid NOT NULL,
	emoji_code varchar(256) DEFAULT NULL::character varying NULL,
	emoji_timestamp timestamptz NULL,

	CONSTRAINT comment_reactions_pkey PRIMARY KEY (id),
    CONSTRAINT uq_comment_reaction_user
        UNIQUE (comment_id, user_id),
	CONSTRAINT comment_reactions_comment_id_fkey 
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev."comments"(id)
        ON DELETE CASCADE,
	CONSTRAINT comment_reactions_user_id_fkey 
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_comment_reactions_comment_id 
    ON tgdx_dev.comment_reactions
    USING btree (comment_id);
CREATE INDEX idx_comment_reactions_user_id 
    ON tgdx_dev.comment_reactions
    USING btree (user_id);


CREATE TABLE tgdx_dev.comment_votes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	user_id uuid NOT NULL,
	vote_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT comment_votes_pkey PRIMARY KEY (id),
    CONSTRAINT uq_comment_vote_user
        UNIQUE (comment_id, user_id),
	CONSTRAINT comment_votes_comment_id_fkey
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev."comments"(id)
        ON DELETE CASCADE,
	CONSTRAINT comment_votes_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_comment_votes_comment_id
    ON tgdx_dev.comment_votes
    USING btree (comment_id);
CREATE INDEX idx_comment_votes_comment_user
    ON tgdx_dev.comment_votes
    USING btree (comment_id, user_id);
CREATE INDEX idx_comment_votes_user_id
    ON tgdx_dev.comment_votes
    USING btree (user_id);


CREATE TABLE tgdx_dev.deleted_comments (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	user_id uuid NOT NULL,
	deleted_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

	CONSTRAINT deleted_comments_comment_id_pkey PRIMARY KEY (id),
	CONSTRAINT deleted_comments_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_deleted_comments_comment_id
    ON tgdx_dev.deleted_comments
    USING btree (comment_id);
CREATE INDEX idx_deleted_comments_user_id
    ON tgdx_dev.deleted_comments
    USING btree (user_id);


CREATE TABLE tgdx_dev.comment_reports (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	reported_by_user_id uuid NOT NULL,
	reason tgdx_dev."comment_report_reason_enum" NOT NULL,
	description text NULL,
	status tgdx_dev."comment_report_status_enum" DEFAULT 'PENDING'::tgdx_dev.comment_report_status_enum NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	reviewed_at timestamptz NULL,
	reviewed_by_admin_id uuid NULL,

	CONSTRAINT comment_reports_pkey PRIMARY KEY (id),
	CONSTRAINT uq_comment_reports_comment_user
        UNIQUE (comment_id, reported_by_user_id),
	CONSTRAINT fk_comment_reports_comment
        FOREIGN KEY (comment_id)
        REFERENCES tgdx_dev."comments"(id)
        ON DELETE CASCADE,
	CONSTRAINT fk_comment_reports_reported_by_user
        FOREIGN KEY (reported_by_user_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE,
	CONSTRAINT fk_comment_reports_reviewed_by_admin
        FOREIGN KEY (reviewed_by_admin_id)
        REFERENCES tgdx_dev.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_comment_reports_comment_id
    ON tgdx_dev.comment_reports
    USING btree (comment_id);
CREATE INDEX idx_comment_reports_reported_by_user_id
    ON tgdx_dev.comment_reports
    USING btree (reported_by_user_id);
CREATE INDEX idx_comment_reports_status
    ON tgdx_dev.comment_reports
    USING btree (status);
