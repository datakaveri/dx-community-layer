CREATE SCHEMA IF NOT EXISTS tgdx_dev;

CREATE EXTENSION IF NOT EXISTS plpgsql
  SCHEMA "pg_catalog";

CREATE EXTENSION IF NOT EXISTS pg_trgm
  SCHEMA "public";

CREATE EXTENSION IF NOT EXISTS pgcrypto
  SCHEMA "tgdx_dev";


DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'competition_status_enum'
      AND n.nspname = 'tgdx_dev'
  ) THEN
    CREATE TYPE tgdx_dev.competition_status_enum AS ENUM (
      'DRAFT',
      'SCHEDULED',
      'PUBLISHED',
      'EVALUATION',
      'COMPLETED',
      'CANCELLED'
    );
  END IF;
END $$;


DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'prize_type_enum'
      AND n.nspname = 'tgdx_dev'
  ) THEN
    CREATE TYPE tgdx_dev.prize_type_enum AS ENUM (
      'CASH',
      'NO_CASH'
    );
  END IF;
END $$;


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


CREATE TABLE tgdx_dev.competitions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	title varchar(300) NOT NULL,
  subtitle varchar(500) NULL,
  overview text NULL,
	detailed_description text NULL,
	status tgdx_dev."competition_status_enum" DEFAULT 'DRAFT'::tgdx_dev.competition_status_enum NOT NULL,
	created_by uuid NOT NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	published_at timestamptz NULL,
	scheduled_publish_at timestamptz NULL,
	image_url varchar(300) DEFAULT NULL::character varying NULL,
	"constraints" text NULL,
	rules_and_guidelines jsonb NULL,
	other_resources text NULL,
	results_announced_at timestamptz NULL,
	title_vector tsvector GENERATED ALWAYS AS (
    to_tsvector(
      'simple'::regconfig, COALESCE(title, ''::character varying)::text
      )
    ) STORED NULL,

  CONSTRAINT competitions_pkey PRIMARY KEY (id),
  CONSTRAINT competitions_created_by_fkey
    FOREIGN KEY (created_by)
    REFERENCES tgdx_dev.users(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competitions_created_by
  ON tgdx_dev.competitions USING btree (created_by);

CREATE INDEX idx_competitions_title_trgm
  ON tgdx_dev.competitions
  USING gin (title gin_trgm_ops);


CREATE TABLE tgdx_dev.competition_timelines (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	competition_id uuid NOT NULL,
	submission_starts_at date NULL,
	submission_ends_at date NULL,
	evaluation_ends_at date NULL,

  CONSTRAINT competition_timelines_pkey PRIMARY KEY (id),
  CONSTRAINT competition_timelines_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_timelines_competition_id
  ON tgdx_dev.competition_timelines USING btree (competition_id);


CREATE TABLE tgdx_dev.competition_submissions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	competition_id uuid NOT NULL,
	user_id uuid NOT NULL,
	title varchar(300) NOT NULL,
	description text NOT NULL,
	attachments jsonb NULL,
	is_disqualified bool DEFAULT false,
	score float8 NULL,
	evaluation_comment text NULL,
	submission_count int4 DEFAULT 0,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	evaluation_attachments jsonb NULL,

	title_vector tsvector GENERATED ALWAYS AS (
    to_tsvector(
      'english'::regconfig, COALESCE(title, ''::character varying)::text
      )
    ) STORED NULL,

  CONSTRAINT competition_submissions_pkey PRIMARY KEY (id),
  CONSTRAINT competition_submissions_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE,
  CONSTRAINT competition_submissions_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES tgdx_dev.users(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_submissions_competition_id
  ON tgdx_dev.competition_submissions USING btree (competition_id);

CREATE INDEX idx_competition_submissions_user_id
  ON tgdx_dev.competition_submissions USING btree (user_id);

CREATE INDEX idx_competition_submissions_attachments_gin
  ON tgdx_dev.competition_submissions
  USING gin (attachments);


CREATE TABLE tgdx_dev.competition_prize_pools (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	competition_id uuid NOT NULL,
	prize_type tgdx_dev."prize_type_enum" DEFAULT 'NO_CASH'::tgdx_dev.prize_type_enum NOT NULL,
	total_pool_amount numeric(15, 2) DEFAULT 0.00,
	currency varchar(3) DEFAULT 'INR'::character varying NULL,
	prize_description text NULL,

  CONSTRAINT competition_prize_pools_pkey PRIMARY KEY (id),
  CONSTRAINT competition_prize_pools_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_prize_pools_competition_id
  ON tgdx_dev.competition_prize_pools USING btree (competition_id);


CREATE TABLE tgdx_dev.competition_participants (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	competition_id uuid NOT NULL,
	user_id uuid NOT NULL,
	joined_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

  CONSTRAINT competition_participants_pkey PRIMARY KEY (id),
  CONSTRAINT competition_participants_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE,
  CONSTRAINT competition_participants_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES tgdx_dev.users(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_participants_competition_id
  ON tgdx_dev.competition_participants USING btree (competition_id);

CREATE INDEX idx_competition_participants_user_id
  ON tgdx_dev.competition_participants USING btree (user_id);


CREATE TABLE tgdx_dev.bookmarked_competitions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	competition_id uuid NOT NULL,
	user_id uuid NOT NULL,
	is_active bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

  CONSTRAINT bookmarked_competitions_pkey PRIMARY KEY (id),
  CONSTRAINT bookmarked_competitions_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE,
  CONSTRAINT bookmarked_competitions_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES tgdx_dev.users(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_bookmarked_competitions_competition_id
  ON tgdx_dev.bookmarked_competitions USING btree (competition_id);

CREATE INDEX idx_bookmarked_competitions_user_id
  ON tgdx_dev.bookmarked_competitions USING btree (user_id);

CREATE INDEX idx_bookmarked_competitions_discussion_user
  ON tgdx_dev.bookmarked_competitions USING btree (competition_id, user_id);


CREATE TABLE tgdx_dev.competition_evaluations (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	competition_id uuid NOT NULL,
	evaluation_criteria text NULL,
	submission_criteria text NULL,

  CONSTRAINT competition_evaluations_pkey PRIMARY KEY (id),
  CONSTRAINT competition_evaluations_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_evaluations_competition_id
  ON tgdx_dev.competition_evaluations USING btree (competition_id);


CREATE TABLE tgdx_dev.competition_datasets (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
	competition_id uuid NOT NULL,
	description text NULL,
	datasets jsonb NULL,
	ai_models jsonb NULL,
	additional_assets jsonb NULL,

  CONSTRAINT competition_datasets_pkey PRIMARY KEY (id),
  CONSTRAINT competition_datasets_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_datasets_datasets_gin
  ON tgdx_dev.competition_datasets
  USING gin (datasets);

CREATE INDEX idx_competition_datasets_ai_models_gin
  ON tgdx_dev.competition_datasets
  USING gin (ai_models);

CREATE INDEX idx_competition_datasets_additional_assets_gin
  ON tgdx_dev.competition_datasets
  USING gin (additional_assets);
