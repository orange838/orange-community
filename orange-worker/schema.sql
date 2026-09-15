CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  orange_balance INTEGER DEFAULT 0,
  last_sign_in_date TEXT,
  role TEXT DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  is_used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS checkin_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  checkin_date TEXT NOT NULL,
  points INTEGER DEFAULT 5,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(email, checkin_date)
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_email TEXT NOT NULL,
  admin_username TEXT,
  target_user_id INTEGER NOT NULL,
  target_email TEXT NOT NULL,
  target_username TEXT,
  old_balance INTEGER NOT NULL,
  new_balance INTEGER NOT NULL,
  old_role TEXT NOT NULL,
  new_role TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_email TEXT,
  actor_username TEXT,
  action TEXT NOT NULL,
  action_detail TEXT NOT NULL,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  status INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS turnstile_verification_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  passed INTEGER NOT NULL,
  hostname TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
