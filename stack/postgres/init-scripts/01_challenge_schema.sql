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


CREATE TABLE tgdx_dev.competitions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  title varchar(300) NOT NULL,
  subtitle varchar(500),
  overview text,
  detailed_description text,
  status tgdx_dev.competition_status_enum NOT NULL DEFAULT 'DRAFT',
  created_by uuid NOT NULL,
  updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
  published_at timestamptz,
  scheduled_publish_at timestamptz,
  image_url varchar(300),
  constraints text,
  rules_and_guidelines varchar(300),
  other_resources text,
  results_announced_at timestamptz,

  title_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, ''))
  ) STORED,

  CONSTRAINT competitions_pkey PRIMARY KEY (id),
  CONSTRAINT competitions_created_by_fkey
    FOREIGN KEY (created_by)
    REFERENCES tgdx_dev.users(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competitions_created_by
  ON tgdx_dev.competitions (created_by);

CREATE INDEX idx_competitions_title_trgm
  ON tgdx_dev.competitions
  USING gin (title gin_trgm_ops);


CREATE TABLE tgdx_dev.competition_timelines (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  competition_id uuid NOT NULL,
  submission_starts_at timestamptz NOT NULL,
  submission_ends_at timestamptz NOT NULL,
  evaluation_ends_at timestamptz,

  CONSTRAINT competition_timelines_pkey PRIMARY KEY (id),
  CONSTRAINT competition_timelines_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_timelines_competition_id
  ON tgdx_dev.competition_timelines (competition_id);


CREATE TABLE tgdx_dev.competition_submissions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  competition_id uuid NOT NULL,
  user_id uuid NOT NULL,
  title varchar(300) NOT NULL,
  description text NOT NULL,
  attachments jsonb,
  is_disqualified boolean DEFAULT false,
  score double precision,
  evaluation_comment text,
  submission_count integer DEFAULT 0,
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
  evaluation_attachments jsonb,

  title_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, ''))
  ) STORED,

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
  ON tgdx_dev.competition_submissions (competition_id);

CREATE INDEX idx_competition_submissions_user_id
  ON tgdx_dev.competition_submissions (user_id);

CREATE INDEX idx_competition_submissions_attachments_gin
  ON tgdx_dev.competition_submissions
  USING gin (attachments);


CREATE TABLE tgdx_dev.competition_prize_pools (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  competition_id uuid NOT NULL,
  prize_type tgdx_dev.prize_type_enum NOT NULL DEFAULT 'CASH',
  total_pool_amount double precision DEFAULT 0.00,
  currency varchar(3) DEFAULT 'INR',
  prize_description text,

  CONSTRAINT competition_prize_pools_pkey PRIMARY KEY (id),
  CONSTRAINT competition_prize_pools_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_prize_pools_competition_id
  ON tgdx_dev.competition_prize_pools (competition_id);


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
  ON tgdx_dev.competition_participants (competition_id);

CREATE INDEX idx_competition_participants_user_id
  ON tgdx_dev.competition_participants (user_id);


CREATE TABLE tgdx_dev.bookmarked_competitions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  competition_id uuid NOT NULL,
  user_id uuid NOT NULL,
  is_active boolean DEFAULT true NOT NULL,
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
  ON tgdx_dev.bookmarked_competitions (competition_id);

CREATE INDEX idx_bookmarked_competitions_user_id
  ON tgdx_dev.bookmarked_competitions (user_id);


CREATE TABLE tgdx_dev.competition_evaluations (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  competition_id uuid NOT NULL,
  evaluation_criteria text,
  submission_criteria text,

  CONSTRAINT competition_evaluations_pkey PRIMARY KEY (id),
  CONSTRAINT competition_evaluations_competition_id_fkey
    FOREIGN KEY (competition_id)
    REFERENCES tgdx_dev.competitions(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_competition_evaluations_competition_id
  ON tgdx_dev.competition_evaluations (competition_id);


CREATE TABLE tgdx_dev.competition_datasets (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  competition_id uuid NOT NULL,
  description text,
  datasets jsonb,
  ai_models jsonb,
  additional_assets jsonb,

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
