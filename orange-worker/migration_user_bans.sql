-- Run once against an existing D1 database before deploying the Worker changes.
ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN ban_reason TEXT;
ALTER TABLE users ADD COLUMN ban_duration_days INTEGER;
ALTER TABLE users ADD COLUMN banned_until TEXT;
