-- SQL Schema for the recruiting app

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(120) UNIQUE NOT NULL,
    hashed_password TEXT,
    provider VARCHAR(50),
    oauth_access_token TEXT,
    oauth_refresh_token TEXT,
    token_expires_at TIMESTAMP,
    is_new_user INTEGER NOT NULL DEFAULT 1,
    is_admin BOOLEAN DEFAULT FALSE,
    has_consented BOOLEAN DEFAULT FALSE,
    has_completed_setup BOOLEAN DEFAULT FALSE,
    name VARCHAR(100),
    organization VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User settings table
CREATE TABLE IF NOT EXISTS user_settings (
    user_id VARCHAR(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    selected_folders VARCHAR,
    fetch_frequency VARCHAR DEFAULT 'manual' NOT NULL,
    batch_process_enabled BOOLEAN DEFAULT FALSE
);

-- Recruits table
CREATE TABLE IF NOT EXISTS recruits (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email_address VARCHAR(120) UNIQUE,
    phone VARCHAR(20),
    grad_year VARCHAR(4),
    state VARCHAR(50),
    gpa VARCHAR(4),
    majors TEXT,
    positions TEXT,
    clubs TEXT,
    coach_name VARCHAR(100),
    coach_phone VARCHAR(20),
    coach_email VARCHAR(120),
    rating VARCHAR(5),
    evaluation TEXT,
    last_evaluation_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for recruits
CREATE INDEX IF NOT EXISTS idx_recruits_user_id ON recruits(user_id);
CREATE INDEX IF NOT EXISTS idx_recruits_email ON recruits(email_address);
CREATE INDEX IF NOT EXISTS idx_recruits_last_name ON recruits(last_name);
CREATE INDEX IF NOT EXISTS idx_recruits_first_name ON recruits(first_name);
CREATE INDEX IF NOT EXISTS idx_recruits_grad_year ON recruits(grad_year);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recruit_id INTEGER REFERENCES recruits(id) ON DELETE CASCADE,
    recruit_email VARCHAR(120),
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    home_participants TEXT,
    away_participants TEXT,
    event_name VARCHAR(255),
    is_master BOOLEAN DEFAULT FALSE,
    source VARCHAR(50) DEFAULT 'manual',
    date VARCHAR(50) NOT NULL,
    time VARCHAR(50),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for schedules
CREATE INDEX IF NOT EXISTS idx_schedules_user_id ON schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_schedules_recruit_id ON schedules(recruit_id);
CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules(date);
CREATE INDEX IF NOT EXISTS idx_schedules_source ON schedules(source);

-- Emails table
CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recruit_email VARCHAR(120),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    date VARCHAR(50),
    subject TEXT,
    summary TEXT,
    highlights TEXT,
    profile TEXT,
    schedule TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    folder_id VARCHAR(255),
    sender VARCHAR(255),
    received_date TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    has_attachments INTEGER DEFAULT 0,
    body TEXT,
    import_date TIMESTAMP,
    processed INTEGER DEFAULT 0,
    processed_date TIMESTAMP
);

-- Create indexes for emails
CREATE INDEX IF NOT EXISTS idx_emails_user_id ON emails(user_id);
CREATE INDEX IF NOT EXISTS idx_emails_email_id ON emails(email_id);
CREATE INDEX IF NOT EXISTS idx_emails_processed ON emails(processed);

-- Email queue table
CREATE TABLE IF NOT EXISTS email_queue (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_id VARCHAR NOT NULL,
    provider VARCHAR(20) NOT NULL,
    folder_id VARCHAR NOT NULL,
    status VARCHAR(20) DEFAULT 'QUEUED',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT
);

-- Create indexes for email_queue
CREATE INDEX IF NOT EXISTS idx_email_queue_user_id ON email_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);

-- Extraction feedback table
CREATE TABLE IF NOT EXISTS extraction_feedback (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_id VARCHAR NOT NULL,
    recruit_id INTEGER NOT NULL REFERENCES recruits(id) ON DELETE CASCADE,
    original_text TEXT,
    original_extraction JSONB NOT NULL,
    corrected_values JSONB NOT NULL,
    notes TEXT,
    used_cache BOOLEAN DEFAULT FALSE,
    model_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for extraction_feedback
CREATE INDEX IF NOT EXISTS idx_extraction_feedback_user_id ON extraction_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_extraction_feedback_email_id ON extraction_feedback(email_id);
CREATE INDEX IF NOT EXISTS idx_extraction_feedback_recruit_id ON extraction_feedback(recruit_id);

-- Extraction patterns table
CREATE TABLE IF NOT EXISTS extraction_patterns (
    id SERIAL PRIMARY KEY,
    field_name VARCHAR(50) NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for extraction_patterns
CREATE INDEX IF NOT EXISTS idx_extraction_patterns_field_name ON extraction_patterns(field_name);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    normalized_name VARCHAR(255) NOT NULL,
    birth_year VARCHAR(4),
    gender VARCHAR(10),
    age_group VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for teams
CREATE INDEX IF NOT EXISTS idx_teams_normalized_name ON teams(normalized_name);

-- Team aliases table
CREATE TABLE IF NOT EXISTS team_aliases (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL UNIQUE,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for team_aliases
CREATE INDEX IF NOT EXISTS idx_team_aliases_team_id ON team_aliases(team_id);
CREATE INDEX IF NOT EXISTS idx_team_aliases_alias ON team_aliases(alias);

-- Scraper configurations table
CREATE TABLE IF NOT EXISTS scraper_configurations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    parameters TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for scraper_configurations
CREATE INDEX IF NOT EXISTS idx_scraper_configurations_source ON scraper_configurations(source);
CREATE INDEX IF NOT EXISTS idx_scraper_configurations_active ON scraper_configurations(active);

-- Scraping logs table
CREATE TABLE IF NOT EXISTS scraping_logs (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES scraper_configurations(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    total_matches INTEGER DEFAULT 0,
    new_matches INTEGER DEFAULT 0,
    results TEXT,
    error TEXT
);

-- Create indexes for scraping_logs
CREATE INDEX IF NOT EXISTS idx_scraping_logs_config_id ON scraping_logs(config_id);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_start_time ON scraping_logs(start_time);

-- GPT cache table
CREATE TABLE IF NOT EXISTS gpt_cache (
    id SERIAL PRIMARY KEY,
    content_hash VARCHAR(32) NOT NULL UNIQUE,
    email VARCHAR(120),
    result_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for gpt_cache
CREATE INDEX IF NOT EXISTS idx_gpt_cache_content_hash ON gpt_cache(content_hash);
CREATE INDEX IF NOT EXISTS idx_gpt_cache_email ON gpt_cache(email);

-- Add triggers to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for each table with updated_at column
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('users', 'recruits', 'schedules', 'emails', 
                          'teams', 'extraction_patterns', 'scraper_configurations',
                          'gpt_cache')
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_modified_%I ON %I;
            CREATE TRIGGER update_modified_%I
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE PROCEDURE update_modified_column();
        ', t, t, t, t);
    END LOOP;
END;
$$ LANGUAGE plpgsql;
