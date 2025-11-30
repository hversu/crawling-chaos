-- Initialize database tables for news analysis app

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    template_name VARCHAR(255),
    parameters JSONB,
    google_search_query TEXT,
    claude_sys_prompt TEXT,
    claude_user_prompt TEXT,
    gpt_sys_prompt TEXT,
    gpt_user_prompt TEXT,
    frequency_minutes INTEGER,
    depends_on_job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    collection_type VARCHAR(50) NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS claude_analysis (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
    analysis_text TEXT,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gpt_analysis (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
    analysis_text TEXT,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_queries (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    parent_analysis_id INTEGER REFERENCES claude_analysis(id) ON DELETE CASCADE,
    queries JSONB NOT NULL,
    justification TEXT,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_collections_job_collected ON collections(job_id, collected_at DESC);
CREATE INDEX idx_collections_type ON collections(collection_type);
CREATE INDEX idx_claude_job_created ON claude_analysis(job_id, created_at DESC);
CREATE INDEX idx_gpt_job_created ON gpt_analysis(job_id, created_at DESC);
CREATE INDEX idx_search_queries_job ON search_queries(job_id, created_at DESC);
CREATE INDEX idx_jobs_active ON jobs(is_active);
CREATE INDEX idx_jobs_depends_on ON jobs(depends_on_job_id);
