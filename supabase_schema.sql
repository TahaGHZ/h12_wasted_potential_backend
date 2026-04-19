-- Run these commands in your Supabase SQL Editor to create the necessary tables

-- 1. Signals Table
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    raw_payload JSONB,
    enriched_payload JSONB
);

-- 2. Cases Table
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    assigned_to TEXT,
    status TEXT,
    priority_score NUMERIC,
    domain TEXT,
    event_type TEXT,
    location TEXT,
    embedding JSONB, -- Stored as JSONB here unless you use pgvector
    embedding_count INTEGER DEFAULT 0,
    signals_count INTEGER DEFAULT 0,
    payload JSONB
);

-- 3. Briefs Table
CREATE TABLE IF NOT EXISTS briefs (
    case_id TEXT PRIMARY KEY REFERENCES cases(case_id) ON DELETE CASCADE,
    title TEXT,
    summary TEXT,
    priority_score NUMERIC,
    payload JSONB
);

-- 4. Plans Table
CREATE TABLE IF NOT EXISTS plans (
    case_id TEXT REFERENCES cases(case_id) ON DELETE CASCADE,
    plan_id TEXT PRIMARY KEY,
    title TEXT,
    confidence NUMERIC,
    payload JSONB
);
