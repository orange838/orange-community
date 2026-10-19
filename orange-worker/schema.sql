CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  orange_balance INTEGER DEFAULT 0,
  last_sign_in_date TEXT,
  role TEXT DEFAULT 'user',
  is_banned INTEGER NOT NULL DEFAULT 0,
  ban_reason TEXT,
  ban_duration_days INTEGER,
  banned_until TEXT,
  github_id TEXT UNIQUE,
  github_username TEXT,
  cpoauth_id TEXT UNIQUE,
  cpoauth_username TEXT
);

CREATE TABLE IF NOT EXISTS codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  is_used INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  attempts INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS checkin_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  checkin_date TEXT NOT NULL,
  points INTEGER DEFAULT 5,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, checkin_date)
);

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

CREATE TABLE IF NOT EXISTS referral_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  owner_user_id INTEGER NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referral_attributions (
  invitee_user_id INTEGER PRIMARY KEY,
  inviter_user_id INTEGER NOT NULL,
  referral_code_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_referral_attributions_inviter
  ON referral_attributions(inviter_user_id);

CREATE TABLE IF NOT EXISTS orange_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  balance_after INTEGER,
  transaction_type TEXT NOT NULL,
  description TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orange_transactions_user
  ON orange_transactions(user_id, id DESC);

CREATE TABLE IF NOT EXISTS referral_rewards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invitee_user_id INTEGER NOT NULL,
  inviter_user_id INTEGER NOT NULL,
  reward_type TEXT NOT NULL,
  reward_date TEXT NOT NULL DEFAULT '',
  amount INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(invitee_user_id, reward_type, reward_date)
);

CREATE INDEX IF NOT EXISTS idx_referral_rewards_inviter
  ON referral_rewards(inviter_user_id);

CREATE TRIGGER IF NOT EXISTS apply_referral_reward
AFTER INSERT ON referral_rewards
BEGIN
  UPDATE users
  SET orange_balance = COALESCE(orange_balance, 0) + NEW.amount
  WHERE id = NEW.inviter_user_id;
  INSERT INTO orange_transactions
    (user_id, amount, balance_after, transaction_type, description)
  SELECT NEW.inviter_user_id, NEW.amount, orange_balance, NEW.reward_type,
    CASE NEW.reward_type
      WHEN 'registration' THEN '好友注册奖励：' ||
        (SELECT username FROM users WHERE id = NEW.invitee_user_id)
      WHEN 'daily_checkin' THEN '好友签到奖励：' ||
        (SELECT username FROM users WHERE id = NEW.invitee_user_id)
      ELSE '邀请奖励'
    END
  FROM users
  WHERE id = NEW.inviter_user_id;
END;

INSERT OR IGNORE INTO referral_rewards
  (invitee_user_id, inviter_user_id, reward_type, reward_date, amount)
SELECT invitee_user_id, inviter_user_id, 'registration', '', 10
FROM referral_attributions;

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
CREATE TABLE IF NOT EXISTS user_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  content TEXT NOT NULL,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

-- 帖子广场：用户发帖
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  username TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
