CREATE TABLE IF NOT EXISTS evidence (
 seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, id TEXT NOT NULL UNIQUE, digest TEXT NOT NULL UNIQUE,
 origin_key TEXT NOT NULL, project TEXT NOT NULL, topic TEXT NOT NULL, purpose TEXT NOT NULL,
 source TEXT NOT NULL, line INTEGER NOT NULL, role TEXT NOT NULL CHECK(role IN ('user','assistant')),
 text TEXT NOT NULL, created TIMESTAMPTZ NOT NULL DEFAULT now(),
 search_document TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple'::regconfig,text)) STORED
);
CREATE INDEX IF NOT EXISTS evidence_scope ON evidence(project,topic,purpose,seq DESC);
CREATE INDEX IF NOT EXISTS evidence_search ON evidence USING GIN(search_document);
CREATE TABLE IF NOT EXISTS retrieval_feedback (
 seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, id TEXT NOT NULL UNIQUE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id), project TEXT NOT NULL, topic TEXT NOT NULL, purpose TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('suppress','correct','unsuppress')), reason TEXT NOT NULL, correction TEXT,
 created TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS retrieval_feedback_scope ON retrieval_feedback(evidence_id,project,topic,purpose,seq DESC);
CREATE TABLE IF NOT EXISTS feedback (
 id TEXT PRIMARY KEY, subject TEXT NOT NULL, rating TEXT NOT NULL CHECK(rating IN ('liked','needs_change','rejected')),
 comment TEXT NOT NULL, project TEXT NOT NULL, topic TEXT NOT NULL, purpose TEXT NOT NULL,
 functionality TEXT NOT NULL DEFAULT 'not_evaluated', created TIMESTAMPTZ NOT NULL DEFAULT now()
);
