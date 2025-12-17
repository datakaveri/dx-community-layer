-- Create schema first
CREATE SCHEMA IF NOT EXISTS tgdx_dev;

-- Extensions
CREATE EXTENSION IF NOT EXISTS plpgsql
	SCHEMA "pg_catalog";

CREATE EXTENSION IF NOT EXISTS pg_trgm
	SCHEMA "public";

CREATE EXTENSION IF NOT EXISTS pgcrypto
 SCHEMA "tgdx_dev";


-- Base ENUM types
CREATE TYPE tgdx_dev."discussions_category_enum" AS ENUM (
	'DATA_BANKS',
	'AI_MODELS',
	'USECASES',
	'CHALLENGES',
	'OTHERS');


CREATE TYPE tgdx_dev."discussions_type_enum" AS ENUM (
	'GENERAL',
	'GETTING_STARTED',
	'PRODUCT_FEEDBACK',
	'PRODUCT_ANNOUNCEMENTS',
	'PUBLIC');


CREATE TYPE tgdx_dev."discussions_status_enum" AS ENUM (
	'PENDING',
	'APPROVED',
	'CHANGES_REQUIRED');


CREATE TYPE tgdx_dev."reactions_vote_enum" AS ENUM (
	'UP',
	'DOWN');


-- Array types based on ENUMs - Use PostgreSQL's automatic array type creation
-- The proper way to create array types of enums is just to use the [] notation
-- These types are automatically available when the base enum types exist


-- Base tables (no dependencies)
CREATE TABLE tgdx_dev.users (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	email varchar(256) NOT NULL,
	"name" varchar(256) NOT NULL,
	name_vector tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, COALESCE(name, ''::character varying)::text)) STORED NULL,
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (id)
);


CREATE TABLE tgdx_dev.tags (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(256) NOT NULL,
	name_vector tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, COALESCE(name, ''::character varying)::text)) STORED NULL,
	CONSTRAINT tags_pkey PRIMARY KEY (id)
);


-- Tables dependent on users
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
	title_vector tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, COALESCE(title, ''::character varying)::text)) STORED NULL,
	sub_category_vector tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, COALESCE(sub_category, ''::character varying)::text)) STORED NULL,
	CONSTRAINT discussions_pkey PRIMARY KEY (id),
	CONSTRAINT discussions_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_discussions_title_trgm ON tgdx_dev.discussions USING gin (title gin_trgm_ops);
CREATE INDEX idx_discussions_user_id ON tgdx_dev.discussions USING btree (user_id);


-- Tables dependent on discussions and/or tags
CREATE TABLE tgdx_dev.discussion_tags (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	tag_id uuid NOT NULL,
	discussion_id uuid NOT NULL,
	CONSTRAINT discussion_tags_pkey PRIMARY KEY (id),
	CONSTRAINT discussion_tags_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE,
	CONSTRAINT discussion_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES tgdx_dev.tags(id) ON DELETE CASCADE
);
CREATE INDEX idx_discussion_tags_discussion_id ON tgdx_dev.discussion_tags USING btree (discussion_id);
CREATE INDEX idx_discussion_tags_tag_id ON tgdx_dev.discussion_tags USING btree (tag_id);


CREATE TABLE tgdx_dev.discussion_attachments (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	attachment_metadata jsonb NOT NULL,
	s3_key varchar(256) NOT NULL,
	uploaded_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT discussion_attachments_pkey PRIMARY KEY (id),
	CONSTRAINT discussion_attachments_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE
);
CREATE INDEX idx_discussion_attachments_attachment_metadata_gin ON tgdx_dev.discussion_attachments USING gin (attachment_metadata);
CREATE INDEX idx_discussion_attachments_discussion_id ON tgdx_dev.discussion_attachments USING btree (discussion_id);


CREATE TABLE tgdx_dev.discussion_reactions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	emoji_code varchar(256) DEFAULT NULL::character varying NULL,
	emoji_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT discussion_reactions_pkey PRIMARY KEY (id),
	CONSTRAINT discussion_reactions_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE,
	CONSTRAINT discussion_reactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_discussion_reactions_discussion_id ON tgdx_dev.discussion_reactions USING btree (discussion_id);
CREATE INDEX idx_discussion_reactions_user_id ON tgdx_dev.discussion_reactions USING btree (user_id);


CREATE TABLE tgdx_dev.discussion_votes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	vote_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT discussion_votes_pkey PRIMARY KEY (id),
	CONSTRAINT discussion_votes_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE,
	CONSTRAINT discussion_votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_discussion_votes_discussion_id ON tgdx_dev.discussion_votes USING btree (discussion_id);
CREATE INDEX idx_discussion_votes_discussion_user ON tgdx_dev.discussion_votes USING btree (discussion_id, user_id);
CREATE INDEX idx_discussion_votes_user_id ON tgdx_dev.discussion_votes USING btree (user_id);


CREATE TABLE tgdx_dev.discussion_reviews (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	reviewer_id uuid NOT NULL,
	"comment" text NULL,
	updated_status tgdx_dev."discussions_status_enum" DEFAULT 'PENDING'::tgdx_dev.discussions_status_enum NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT discussion_reviews_pkey PRIMARY KEY (id),
	CONSTRAINT discussion_reviews_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE,
	CONSTRAINT discussion_reviews_reviewer_id FOREIGN KEY (reviewer_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_discussion_reviews_discussion_id ON tgdx_dev.discussion_reviews USING btree (discussion_id);
CREATE INDEX idx_discussion_reviews_reviewer_id ON tgdx_dev.discussion_reviews USING btree (reviewer_id);


CREATE TABLE tgdx_dev.bookmarked_discussions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT bookmarked_discussions_pkey PRIMARY KEY (id),
	CONSTRAINT bookmarked_discussions_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE,
	CONSTRAINT bookmarked_discussions_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_bookmarked_discussions_discussion_id ON tgdx_dev.bookmarked_discussions USING btree (discussion_id);
CREATE INDEX idx_bookmarked_discussions_discussion_user ON tgdx_dev.bookmarked_discussions USING btree (discussion_id, user_id);
CREATE INDEX idx_bookmarked_discussions_user_id ON tgdx_dev.bookmarked_discussions USING btree (user_id);


CREATE TABLE tgdx_dev.pinned_discussions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	pinned_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT pinned_discussions_pkey PRIMARY KEY (id),
	CONSTRAINT pinned_discussions_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE,
	CONSTRAINT pinned_discussions_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_pinned_discussions_discussion_id ON tgdx_dev.pinned_discussions USING btree (discussion_id);
CREATE INDEX idx_pinned_discussions_discussion_user ON tgdx_dev.pinned_discussions USING btree (discussion_id, user_id);
CREATE INDEX idx_pinned_discussions_user_id ON tgdx_dev.pinned_discussions USING btree (user_id);


CREATE TABLE tgdx_dev.deleted_discussions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	deleted_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT deleted_discussions_pkey PRIMARY KEY (id),
	CONSTRAINT deleted_discussions_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_deleted_discussions_discussion_id ON tgdx_dev.deleted_discussions USING btree (discussion_id);
CREATE INDEX idx_deleted_discussions_user_id ON tgdx_dev.deleted_discussions USING btree (user_id);


-- Comments table (depends on discussions and users)
CREATE TABLE tgdx_dev."comments" (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	discussion_id uuid NOT NULL,
	user_id uuid NOT NULL,
	parent_id uuid NULL,
	replied_to uuid NULL,
	"comment" text NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT comments_pkey PRIMARY KEY (id),
	CONSTRAINT comments_discussion_id_fkey FOREIGN KEY (discussion_id) REFERENCES tgdx_dev.discussions(id) ON DELETE CASCADE,
	CONSTRAINT comments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES tgdx_dev."comments"(id) ON DELETE CASCADE,
	CONSTRAINT comments_replied_to_fkey FOREIGN KEY (replied_to) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE,
	CONSTRAINT comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_comments_discussion_id ON tgdx_dev.comments USING btree (discussion_id);
CREATE INDEX idx_comments_parent_id ON tgdx_dev.comments USING btree (parent_id);
CREATE INDEX idx_comments_replied_to ON tgdx_dev.comments USING btree (replied_to);
CREATE INDEX idx_comments_user_id ON tgdx_dev.comments USING btree (user_id);


-- Tables dependent on comments
CREATE TABLE tgdx_dev.comment_attachments (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	attachment_metadata jsonb NOT NULL,
	s3_key varchar(256) NOT NULL,
	uploaded_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT comment_attachments_pkey PRIMARY KEY (id),
	CONSTRAINT comment_attachments_discussion_id_fkey FOREIGN KEY (comment_id) REFERENCES tgdx_dev."comments"(id) ON DELETE CASCADE
);
CREATE INDEX idx_comment_attachments_attachment_metadata_gin ON tgdx_dev.comment_attachments USING gin (attachment_metadata);
CREATE INDEX idx_comment_attachments_comment_id ON tgdx_dev.comment_attachments USING btree (comment_id);


CREATE TABLE tgdx_dev.comment_reactions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	user_id uuid NOT NULL,
	emoji_code varchar(256) DEFAULT NULL::character varying NULL,
	emoji_timestamp timestamptz NULL,
	CONSTRAINT comment_reactions_pkey PRIMARY KEY (id),
	CONSTRAINT comment_reactions_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES tgdx_dev."comments"(id) ON DELETE CASCADE,
	CONSTRAINT comment_reactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_comment_reactions_comment_id ON tgdx_dev.comment_reactions USING btree (comment_id);
CREATE INDEX idx_comment_reactions_user_id ON tgdx_dev.comment_reactions USING btree (user_id);


CREATE TABLE tgdx_dev.comment_votes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	user_id uuid NOT NULL,
	vote_timestamp timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT comment_votes_pkey PRIMARY KEY (id),
	CONSTRAINT comment_votes_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES tgdx_dev."comments"(id) ON DELETE CASCADE,
	CONSTRAINT comment_votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_comment_votes_comment_id ON tgdx_dev.comment_votes USING btree (comment_id);
CREATE INDEX idx_comment_votes_comment_user ON tgdx_dev.comment_votes USING btree (comment_id, user_id);
CREATE INDEX idx_comment_votes_user_id ON tgdx_dev.comment_votes USING btree (user_id);


CREATE TABLE tgdx_dev.deleted_comments (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	comment_id uuid NOT NULL,
	user_id uuid NOT NULL,
	deleted_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT deleted_comments_comment_id_pkey PRIMARY KEY (id),
	CONSTRAINT delted_comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES tgdx_dev.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_deleted_comments_comment_id ON tgdx_dev.deleted_comments USING btree (comment_id);
CREATE INDEX idx_deleted_comments_user_id ON tgdx_dev.deleted_comments USING btree (user_id);
