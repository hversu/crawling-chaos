-- Initialize database tables for news analysis app

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    google_search_query TEXT NOT NULL,
    claude_sys_prompt TEXT,
    claude_user_prompt TEXT,
    gpt_sys_prompt TEXT,
    gpt_user_prompt TEXT,
    frequency_minutes INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_results (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    publish_date TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data JSONB
);

CREATE TABLE IF NOT EXISTS claude_analysis (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    news_result_id INTEGER REFERENCES news_results(id) ON DELETE CASCADE,
    analysis_text TEXT,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gpt_analysis (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    news_result_id INTEGER REFERENCES news_results(id) ON DELETE CASCADE,
    analysis_text TEXT,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_news_job_collected ON news_results(job_id, collected_at DESC);
CREATE INDEX idx_claude_job_created ON claude_analysis(job_id, created_at DESC);
CREATE INDEX idx_gpt_job_created ON gpt_analysis(job_id, created_at DESC);
CREATE INDEX idx_jobs_active ON jobs(is_active);
