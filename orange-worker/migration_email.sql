
CREATE TABLE users_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  orange_balance INTEGER DEFAULT 0,
  last_sign_in_date TEXT,
  role TEXT DEFAULT 'user',
  github_id TEXT UNIQUE,
  github_username TEXT,
  cpoauth_id TEXT UNIQUE,
  cpoauth_username TEXT
);
INSERT INTO users_new (id, email, username, password, created_at, orange_balance, last_sign_in_date, role, github_id, github_username, cpoauth_id, cpoauth_username)
  SELECT id, email, username, password, created_at, orange_balance, last_sign_in_date, role, github_id, github_username, cpoauth_id, cpoauth_username FROM users;
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

CREATE TABLE checkin_records_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  checkin_date TEXT NOT NULL,
  points INTEGER DEFAULT 5,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, checkin_date)
);
INSERT INTO checkin_records_new (id, user_id, checkin_date, points, created_at)
  SELECT cr.id, u.id, cr.checkin_date, cr.points, cr.created_at
  FROM checkin_records cr JOIN users u ON cr.email = u.email;
DROP TABLE checkin_records;
ALTER TABLE checkin_records_new RENAME TO checkin_records;

CREATE TABLE IF NOT EXISTS invite_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  created_by TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  used_by INTEGER,
  used_at TIMESTAMP,
  status TEXT DEFAULT 'active'
);
