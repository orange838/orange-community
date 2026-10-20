import asyncio
import os
import base64
import hashlib
import hmac
import json
import random
import re
import secrets
import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from urllib.parse import quote, urlsplit
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
from werkzeug.security import check_password_hash

# ============================================================
# 环境变量
#   SECRET_KEY=你的应用密钥（用于 JWT 签名）
#   CF_TURNSTILE_SECRET_KEY=Cloudflare Turnstile 长密钥
#   RESEND_API_KEY=Resend 邮件服务 API 密钥
# ============================================================
load_dotenv()

app = FastAPI()

# CORS：白名单（与线上 worker 的 allowedOrigins 保持一致），使用 Bearer Token 故不开 credentials
ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cslblog.dpdns.org",
    "https://www.cslblog.dpdns.org",
    "https://orange-community.pages.dev",
    "https://aeb.cslblog.dpdns.org",
    "https://dash.cslblog.dpdns.org",
    "https://orange-community-monitor.pages.dev",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
CF_SECRET_KEY = os.getenv("CF_TURNSTILE_SECRET_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = "http://127.0.0.1:8000/api/auth/github/callback"
CPOAUTH_CLIENT_ID = os.getenv("CPOAUTH_CLIENT_ID", "")
CPOAUTH_CLIENT_SECRET = os.getenv("CPOAUTH_CLIENT_SECRET", "")
CPOAUTH_REDIRECT_URI = "http://127.0.0.1:8000/api/auth/cpoauth/callback"
DATABASE = "orange_community.db"

# 签到日期统一按东八区计算（与线上 worker 对齐，避免 UTC 日期错位）
CN_TZ = timezone(timedelta(hours=8))
CODE_TTL_MINUTES = 5
SEND_CODE_COOLDOWN_SECONDS = 60
CODE_MAX_ATTEMPTS = 5
TOKEN_TTL_HOURS = 24 * 7
WEAK_PASSWORD_REMINDER = (
    "你的密码不符合当前安全规则（至少 8 位，且同时包含大写字母、小写字母和数字）。"
    "建议尽快重置密码。此提醒不会限制账号使用。"
)
REFERRAL_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
DASHBOARD_DOMAINS = (
    "orange-community.pages.dev",
    "cslblog.dpdns.org",
    "www.cslblog.dpdns.org",
    "orange-community-monitor.pages.dev",
    "dash.cslblog.dpdns.org",
)
ALLOWED_TURNSTILE_HOSTNAMES = {
    "cslblog.dpdns.org",
    "www.cslblog.dpdns.org",
    "orange-community.pages.dev",
    "localhost",
    "127.0.0.1",
}

# ============================================================
# 密码哈希：与线上 worker 完全一致 pbkdf2:sha256:100000$saltHex$keyHex
# ============================================================
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, dklen=32)
    return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"

def verify_password(stored: str, password: str) -> bool:
    if not stored:
        return False
    # 新格式：pbkdf2:sha256:100000$saltHex$keyHex
    if stored.startswith("pbkdf2:sha256:"):
        try:
            parts = stored.split("$")
            if len(parts) != 3:
                return False
            params, salt_hex, expected = parts
            iterations = int(params.split(":")[2])
            key = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), iterations, dklen=32)
            return hmac.compare_digest(key.hex(), expected)
        except Exception:
            return False
    # 兼容旧 werkzeug 哈希（scrypt / pbkdf2:sha256 base64）
    try:
        return check_password_hash(stored, password)
    except (ValueError, TypeError):
        return False

# ============================================================
# JWT（HS256，无状态），与线上 worker 算法一致
# ============================================================
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def create_token(email: str, username: str, role: str, ttl_hours: int = TOKEN_TTL_HOURS) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "email": email,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + ttl_hours * 3600,
    }
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    )
    sig = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(sig)}"

def verify_token(token: str):
    """校验 JWT，返回 payload（含 email/username/role），无效返回 None"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        signing_input = f"{parts[0]}.{parts[1]}"
        sig = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(sig), parts[2]):
            return None
        payload = json.loads(_b64url_decode(parts[1]))
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return None
        return payload
    except Exception:
        return None

def get_auth_user(request: Request):
    """从 Authorization: Bearer 中解析并校验 token，返回 payload 或 None"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return verify_token(auth[7:].strip())


def _user_by_payload(payload):
    """优先按 email，email 为空（邀请注册的无邮箱用户）则按 username。返回用户行或 None。"""
    email = (payload or {}).get("email") or ""
    conn = sqlite3.connect(DATABASE)
    try:
        if email:
            return conn.execute(
                "SELECT id, email, username, password, orange_balance, last_sign_in_date, role, github_username, cpoauth_username FROM users WHERE email=?",
                (email,),
            ).fetchone()
        return conn.execute(
            "SELECT id, email, username, password, orange_balance, last_sign_in_date, role, github_username, cpoauth_username FROM users WHERE username=?",
            ((payload or {}).get("username", ""),),
        ).fetchone()
    finally:
        conn.close()

# ============================================================
# 数据库初始化（与线上 schema.sql 对齐，含 activity_logs / turnstile 日志）
# ============================================================
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT UNIQUE, "
        "username TEXT NOT NULL, "
        "password TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "orange_balance INTEGER DEFAULT 0, "
        "last_sign_in_date TEXT, "
        "role TEXT DEFAULT 'user', "
        "github_id TEXT UNIQUE, "
        "github_username TEXT, "
        "cpoauth_id TEXT UNIQUE, "
        "cpoauth_username TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS codes "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT NOT NULL, "
        "code TEXT NOT NULL, "
        "expires_at TEXT NOT NULL, "
        "created_at TEXT, "
        "attempts INTEGER DEFAULT 0, "
        "is_used INTEGER DEFAULT 0)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS checkin_records "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER NOT NULL, "
        "checkin_date TEXT NOT NULL, "
        "points INTEGER DEFAULT 5, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS invite_codes "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "code TEXT UNIQUE NOT NULL, "
        "created_by TEXT, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "expires_at TIMESTAMP, "
        "used_by INTEGER, "
        "used_at TIMESTAMP, "
        "status TEXT DEFAULT 'active')"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS admin_audit_logs "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "admin_email TEXT NOT NULL, "
        "admin_username TEXT, "
        "target_user_id INTEGER NOT NULL, "
        "target_email TEXT NOT NULL, "
        "target_username TEXT, "
        "old_balance INTEGER NOT NULL, "
        "new_balance INTEGER NOT NULL, "
        "old_role TEXT NOT NULL, "
        "new_role TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS activity_logs "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "actor_email TEXT, "
        "actor_username TEXT, "
        "action TEXT NOT NULL, "
        "action_detail TEXT NOT NULL, "
        "method TEXT NOT NULL, "
        "path TEXT NOT NULL, "
        "status INTEGER NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS turnstile_verification_logs "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "action TEXT NOT NULL, "
        "passed INTEGER NOT NULL, "
        "hostname TEXT, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS posts "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER NOT NULL, "
        "username TEXT NOT NULL, "
        "title TEXT NOT NULL, "
        "content TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS user_messages "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER NOT NULL, "
        "content TEXT NOT NULL, "
        "is_read INTEGER NOT NULL DEFAULT 0, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS referral_codes "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "code TEXT UNIQUE NOT NULL, "
        "owner_user_id INTEGER NOT NULL UNIQUE, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS referral_attributions "
        "(invitee_user_id INTEGER PRIMARY KEY, "
        "inviter_user_id INTEGER NOT NULL, "
        "referral_code_id INTEGER NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS orange_transactions "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER NOT NULL, "
        "amount INTEGER NOT NULL, "
        "balance_after INTEGER, "
        "transaction_type TEXT NOT NULL, "
        "description TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS referral_rewards "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "invitee_user_id INTEGER NOT NULL, "
        "inviter_user_id INTEGER NOT NULL, "
        "reward_type TEXT NOT NULL, "
        "reward_date TEXT NOT NULL DEFAULT '', "
        "amount INTEGER NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "UNIQUE(invitee_user_id, reward_type, reward_date))"
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_referral_attributions_inviter ON referral_attributions(inviter_user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_orange_transactions_user ON orange_transactions(user_id, id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_referral_rewards_inviter ON referral_rewards(inviter_user_id)")
    c.execute("DROP TABLE IF EXISTS referral_code_aliases")

    # 旧库列迁移
    user_cols = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]
    for col_name, default_value in [("orange_balance", "0"), ("last_sign_in_date", None), ("role", "'user'")]:
        if col_name not in user_cols:
            if default_value is None:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} TEXT")
            else:
                c.execute(
                    f"ALTER TABLE users ADD COLUMN {col_name} INTEGER DEFAULT {default_value}"
                    if col_name == "orange_balance"
                    else f"ALTER TABLE users ADD COLUMN {col_name} TEXT DEFAULT {default_value}"
                )
    for col_name, sql_type in [
        ("is_banned", "INTEGER DEFAULT 0"),
        ("ban_reason", "TEXT"),
        ("ban_duration_days", "INTEGER"),
        ("banned_until", "TEXT"),
    ]:
        if col_name not in user_cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {sql_type}")

    code_cols = [row[1] for row in c.execute("PRAGMA table_info(codes)").fetchall()]
    if "attempts" not in code_cols:
        c.execute("ALTER TABLE codes ADD COLUMN attempts INTEGER DEFAULT 0")
    if "created_at" not in code_cols:
        c.execute("ALTER TABLE codes ADD COLUMN created_at TEXT")

    # 签到唯一约束（与线上 schema.sql 的 UNIQUE(email, checkin_date) 对齐，防并发刷分）
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_checkin_user_date ON checkin_records(user_id, checkin_date)")
    except sqlite3.OperationalError:
        pass
    c.execute(
        "CREATE TRIGGER IF NOT EXISTS apply_referral_reward "
        "AFTER INSERT ON referral_rewards BEGIN "
        "UPDATE users SET orange_balance = COALESCE(orange_balance, 0) + NEW.amount "
        "WHERE id = NEW.inviter_user_id; "
        "INSERT INTO orange_transactions "
        "(user_id, amount, balance_after, transaction_type, description) "
        "SELECT NEW.inviter_user_id, NEW.amount, orange_balance, NEW.reward_type, "
        "CASE NEW.reward_type "
        "WHEN 'registration' THEN '好友注册奖励：' || "
        "(SELECT username FROM users WHERE id = NEW.invitee_user_id) "
        "WHEN 'daily_checkin' THEN '好友签到奖励：' || "
        "(SELECT username FROM users WHERE id = NEW.invitee_user_id) "
        "ELSE '邀请奖励' END "
        "FROM users WHERE id = NEW.inviter_user_id; END"
    )
    c.execute(
        "INSERT OR IGNORE INTO referral_rewards "
        "(invitee_user_id, inviter_user_id, reward_type, reward_date, amount) "
        "SELECT invitee_user_id, inviter_user_id, 'registration', '', 10 FROM referral_attributions"
    )

    conn.commit()
    conn.close()

# ============================================================
# 时间工具（统一 UTC 字符串存储，签到日期用东八区）
# ============================================================
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def utc_timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()

def today_cn() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d")

def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password) is not None
        and re.search(r"[a-z]", password) is not None
        and re.search(r"\d", password) is not None
    )

def validate_registration_input(username: str, password: str):
    if not username:
        return "用户名不能为空"
    if len(username) > 20:
        return "用户名不能超过 20 个字符"
    if not is_strong_password(password):
        return "密码至少 8 位，并同时包含大写字母、小写字母和数字"
    return None

def is_valid_referral_code(code: str) -> bool:
    return len(code) == 6 and re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{6}", code) is not None

def generate_referral_code() -> str:
    while True:
        code = "".join(secrets.choice(REFERRAL_CODE_CHARS) for _ in range(6))
        if is_valid_referral_code(code):
            return code

def find_referral_by_code(conn: sqlite3.Connection, code: str):
    return conn.execute(
        "SELECT rc.id, rc.owner_user_id, u.email, u.username "
        "FROM referral_codes rc JOIN users u ON u.id = rc.owner_user_id WHERE rc.code = ?",
        (code,),
    ).fetchone()

def validate_code(conn: sqlite3.Connection, email: str, code: str):
    row = conn.execute(
        "SELECT id, code, attempts FROM codes WHERE email=? AND is_used=0 AND expires_at>? "
        "ORDER BY id DESC LIMIT 1",
        (email, utc_now()),
    ).fetchone()
    if not row or int(row[2] or 0) >= CODE_MAX_ATTEMPTS:
        return None
    if row[1] != code:
        conn.execute(
            "UPDATE codes SET attempts=COALESCE(attempts, 0)+1 "
            "WHERE id=? AND is_used=0 AND expires_at>? AND COALESCE(attempts, 0) < ?",
            (row[0], utc_now(), CODE_MAX_ATTEMPTS),
        )
        conn.commit()
        return None
    return row

def is_user_banned(is_banned, banned_until) -> bool:
    if int(is_banned or 0) != 1:
        return False
    if not banned_until:
        return True
    try:
        expiry = datetime.fromisoformat(str(banned_until).replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry.timestamp() > datetime.now(timezone.utc).timestamp()
    except (TypeError, ValueError, OverflowError):
        return True

def format_beijing_datetime(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(CN_TZ).strftime("%Y-%m-%d %H:%M")

PROFANITY_WORDS = (
    "fuck", "shit", "bitch", "asshole", "bastard", "motherfucker",
    "sb", "cnm", "cnmb", "nmd", "tmd", "wqnmlgb", "草泥马", "尼玛",
    "牛批", "牛b", "王八蛋", "去你妈的", "狗日的", "色情", "约炮", "md", "jb", "滚犊子",
    "废物", "白痴", "智障", "蠢货", "傻狗", "舔狗", "婊子", "贱人",
    "贱货", "畜生", "杂种", "狗东西", "绿帽", "他妈的", "奶奶的",
    "操你", "日你", "渣男", "人渣",
)
LEET_CHARACTER_CLASSES = {
    "a": "a4@",
    "e": "e3",
    "i": "i1!|",
    "o": "o0",
    "s": "s5$",
    "t": "t7+",
}

def filter_profanity(text: str):
    filtered = unicodedata.normalize("NFKC", text)
    found = []
    for word in sorted(PROFANITY_WORDS, key=len, reverse=True):
        if word == "fuck":
            expression = r"(?<![A-Za-z])f[\W_]*u?[\W_]*c[\W_]*k(?![A-Za-z])"
        elif word.isascii():
            chars = [f"[{re.escape(LEET_CHARACTER_CLASSES.get(char, char))}]" for char in word]
            expression = r"(?<![A-Za-z])" + r"[\W_]*".join(chars) + r"(?![A-Za-z])"
        else:
            expression = re.escape(word)
        pattern = re.compile(expression, re.IGNORECASE)
        if pattern.search(filtered):
            found.append(word)
            filtered = pattern.sub("***", filtered)
    return {"safe": not found, "filteredText": filtered, "profaneWords": found}

# ============================================================
# Cloudflare Turnstile 人机验证
# ============================================================
async def verify_turnstile(token, expected_action: str = None, request: Request = None):
    """向 Cloudflare 发送 token 进行人机验证，并记录日志"""
    log_result = lambda passed, hostname=None: _log_turnstile(expected_action, passed, hostname)

    if not token:
        await log_result(False)
        return False, "未提供验证令牌"
    if not CF_SECRET_KEY:
        await log_result(False)
        return False, "服务器配置错误：缺少 CF_TURNSTILE_SECRET_KEY"

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {"secret": CF_SECRET_KEY, "response": token}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload, timeout=10.0)
            result = resp.json()
            hostname = result.get("hostname")
            origin = request.headers.get("Origin") if request else None
            expected_hostname = urlsplit(origin).hostname if origin else ""
            ok = (
                result.get("success") is True
                and result.get("action") == expected_action
                and hostname in ALLOWED_TURNSTILE_HOSTNAMES
                and hostname == expected_hostname
            )
            await log_result(ok, hostname)
            return (True, "验证通过") if ok else (False, "人机验证失败，请重试")
    except Exception as e:
        await log_result(False)
        return False, f"验证服务异常: {str(e)}"

def _log_turnstile(action, passed, hostname=None):
    try:
        conn = sqlite3.connect(DATABASE)
        conn.execute(
            "INSERT INTO turnstile_verification_logs (action, passed, hostname) VALUES (?, ?, ?)",
            (action, 1 if passed else 0, hostname),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as error:
        print(f"[turnstile] 写入验证日志失败：{error}")

# ============================================================
# 操作日志（对齐线上 activity_logs，供前端后台日志展示）
# ============================================================
def _body_json(request: Request):
    try:
        raw = request._cached_body
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

def record_activity(request: Request, response: JSONResponse):
    url_path = request.url.path
    if request.method == "OPTIONS" or not url_path.startswith("/api/") or url_path == "/api/health":
        return

    body = _body_json(request)
    token_payload = get_auth_user(request)
    identifier = (
        token_payload and token_payload.get("email")
    ) or body.get("email") or body.get("admin_email") or body.get("account") or request.query_params.get("email") or ""

    actor = None
    if identifier:
        conn = sqlite3.connect(DATABASE)
        try:
            actor = conn.execute(
                "SELECT email, username FROM users WHERE email = ? OR username = ?",
                (identifier, identifier),
            ).fetchone()
        finally:
            conn.close()

    action_detail = f"{request.method} {url_path}"
    if url_path == "/api/login":
        action_detail = "使用邮箱验证码登录" if body.get("method") == "code" else "使用账号密码登录"
    elif url_path == "/api/send-code":
        action_detail = "发送登录验证码" if body.get("type") == "login" else "发送注册验证码"
    elif url_path == "/api/register":
        action_detail = f"注册账号 {body.get('username') or body.get('email') or '新用户'}"
    elif url_path == "/api/checkin":
        action_detail = "签到成功，获得 5 个橙子" if response.status_code == 200 else "尝试签到"
    elif url_path == "/api/profile":
        action_detail = "查看个人信息和签到数据"
    elif url_path == "/api/user/referral-code":
        action_detail = "创建拉新邀请码" if response.status_code == 201 else "获取拉新邀请码"
    elif url_path == "/api/user/orange-transactions":
        action_detail = "查看橙子收支记录"
    elif url_path == "/api/posts":
        action_detail = {
            "GET": "查看帖子列表",
            "POST": "发布帖子",
            "DELETE": "删除帖子",
        }.get(request.method, "访问帖子接口")
    elif url_path in {"/api/admin/users/ban", "/api/admin/users/unban"}:
        action_detail = "封禁用户" if url_path.endswith("/ban") else "解除用户封禁"
    elif url_path == "/api/admin/users":
        action_detail = "查看用户列表"
    elif url_path == "/api/admin/logs":
        action_detail = "查看最近 100 条操作日志"
    elif url_path == "/api/admin/users/update":
        action_detail = f"提交用户修改：橙子数量 {body.get('orange_balance', '未提供')}，角色 {body.get('role', '')}"
    elif url_path == "/api/register/invite":
        action_detail = f"邀请注册账号 {body.get('username') or '新用户'}"
    elif url_path == "/api/user/bind-email":
        action_detail = f"绑定邮箱 {body.get('email') or ''}" if response.status_code == 200 else "尝试绑定邮箱"
    elif url_path == "/api/admin/invites":
        action_detail = "生成邀请码" if request.method == "POST" else "查看邀请码列表"

    action_name = {
        "/api/profile": "查看个人信息",
        "/api/send-code": "发送验证码",
        "/api/register": "注册账号",
        "/api/login": "登录账号",
        "/api/checkin": "签到",
        "/api/user/referral-code": "管理拉新邀请码",
        "/api/user/orange-transactions": "查看橙子日志",
        "/api/posts": "帖子管理",
        "/api/register/invite": "邀请注册",
        "/api/user/bind-email": "绑定邮箱",
        "/api/admin/users": "查看用户管理",
        "/api/admin/users/update": "修改用户信息",
        "/api/admin/users/ban": "封禁用户",
        "/api/admin/users/unban": "解除用户封禁",
        "/api/admin/logs": "查看操作日志",
        "/api/admin/invites": "管理邀请码",
    }.get(url_path, "访问接口")

    try:
        conn = sqlite3.connect(DATABASE)
        conn.execute(
            "INSERT INTO activity_logs "
            "(actor_email, actor_username, action, action_detail, method, path, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (actor[0] if actor else None) or identifier or None,
                actor[1] if actor else None,
                action_name,
                action_detail,
                request.method,
                url_path,
                response.status_code,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[log] 写入 activity_logs 失败: {e}")

@app.middleware("http")
async def activity_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            request._cached_body = await request.body()
        except Exception:
            request._cached_body = b""
    response = await call_next(request)
    try:
        record_activity(request, response)
    except Exception as e:
        print(f"[log] {e}")
    return response

# ============================================================
# 发送验证码（带发送冷却 + 验证码尝试次数上限）
# ============================================================
# ============================================================
# 重置密码（Turnstile -> 邮箱验证码 -> 更新密码）
# ============================================================
@app.post("/api/reset-password")
async def reset_password(request: Request):
    data = await request.json()
    is_human, msg = await verify_turnstile(data.get("cf_token"), "reset", request)
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)

    email = str(data.get("email") or "").strip()
    code = str(data.get("code") or "").strip()
    new_password = str(data.get("new_password") or "")
    if not email or not code or not new_password:
        return JSONResponse({"error": "参数不完整"}, status_code=400)
    if not is_strong_password(new_password):
        return JSONResponse({"error": "密码至少 8 位，并同时包含大写字母、小写字母和数字"}, status_code=400)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    user = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        return JSONResponse({"error": "该邮箱尚未注册"}, status_code=404)

    row = validate_code(c, email, code)
    if not row:
        conn.close()
        return JSONResponse({"error": "验证码错误或已过期"}, status_code=400)

    c.execute("UPDATE codes SET is_used=1 WHERE id=?", (row[0],))
    c.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_password), user[0]))
    conn.commit()
    conn.close()
    return JSONResponse({"message": "密码已重置，请使用新密码登录"})

@app.post("/api/send-code")
async def send_code(request: Request):
    data = await request.json()
    email = str(data.get("email") or "").strip()
    code_type = data.get("type", "register")
    if not email:
        return JSONResponse({"error": "没邮箱"}, status_code=400)
    if not RESEND_API_KEY:
        return JSONResponse({"error": "服务器配置错误：缺少 RESEND_API_KEY"}, status_code=500)

    if code_type == "login":
        _conn = sqlite3.connect(DATABASE)
        _exists = _conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        _conn.close()
        if not _exists:
            return JSONResponse({"error": "该邮箱尚未注册"}, status_code=404)

    # 重置密码：邮箱必须已注册
    if code_type == "reset":
        _conn = sqlite3.connect(DATABASE)
        _exists = _conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        _conn.close()
        if not _exists:
            return JSONResponse({"error": "该邮箱尚未注册"}, status_code=404)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # 发送冷却：同一邮箱 60 秒内只能发一次
    last = c.execute(
        "SELECT created_at FROM codes WHERE email=? ORDER BY id DESC LIMIT 1", (email,)
    ).fetchone()
    if last and last[0]:
        try:
            last_ts = datetime.strptime(last[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
            if utc_timestamp() - last_ts < SEND_CODE_COOLDOWN_SECONDS:
                conn.close()
                return JSONResponse(
                    {"error": f"发送过于频繁，请 {SEND_CODE_COOLDOWN_SECONDS} 秒后再试"},
                    status_code=429,
                )
        except ValueError:
            pass

    code = str(random.randint(100000, 999999))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    now = utc_now()
    # 使旧码失效
    c.execute("UPDATE codes SET is_used=1 WHERE email=?", (email,))
    c.execute(
        "INSERT INTO codes (email, code, expires_at, created_at, attempts) VALUES (?, ?, ?, ?, 0)",
        (email, code, expires_at, now),
    )
    conn.commit()
    conn.close()

    subject = (
        "Orange Community 登录验证码" if code_type == "login"
        else "Orange Community 重置密码验证码" if code_type == "reset"
        else "Orange Community 注册验证码"
    )
    text = f"您的验证码是：{code}，有效期 {CODE_TTL_MINUTES} 分钟。请勿将验证码透露给他人。"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                json={
                    "from": "Orange Community <onboarding@cslblog.dpdns.org>",
                    "to": [email],
                    "subject": subject,
                    "text": text,
                },
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        if response.status_code != 200:
            raise Exception(f"Resend API Error: {response.text}")
        return JSONResponse({"message": "已发送"}, status_code=200)
    except Exception as e:
        print(f"发送失败详情: {e}")
        return JSONResponse({"error": "发送失败"}, status_code=500)

# ============================================================
# 注册（Turnstile -> 验证码 -> 建号 -> 签发 token）
# ============================================================
@app.post("/api/register")
async def register(request: Request):
    data = await request.json()
    is_human, msg = await verify_turnstile(data.get("cf_token"), "register", request)
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)

    email = str(data.get("email") or "").strip()
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    code = str(data.get("code") or "").strip()
    referral_code = (data.get("referral_code") or "").strip()
    if not all([email, password, code]):
        return JSONResponse({"error": "缺参数"}, status_code=400)
    input_error = validate_registration_input(username, password)
    if input_error:
        return JSONResponse({"error": input_error}, status_code=400)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        row = validate_code(cursor, email, code)
        if not row:
            return JSONResponse({"error": "码不对或过期"}, status_code=400)

        referral = None
        if referral_code:
            if not is_valid_referral_code(referral_code):
                return JSONResponse({"error": "拉新邀请码无效"}, status_code=400)
            referral = find_referral_by_code(conn, referral_code)
            if not referral:
                return JSONResponse({"error": "拉新邀请码无效"}, status_code=400)
            if (
                (referral[2] and referral[2].lower() == email.lower())
                or referral[3].lower() == username.lower()
            ):
                return JSONResponse({"error": "不能使用自己的拉新邀请码注册"}, status_code=400)

        code_id = row[0]
        cursor.execute("UPDATE codes SET is_used=1 WHERE id=?", (code_id,))
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (email, username, password) VALUES (?, ?, ?)",
            (email, username, hashed),
        )
        new_user_id = cursor.lastrowid
        if referral:
            cursor.execute(
                "INSERT INTO referral_attributions (invitee_user_id, inviter_user_id, referral_code_id) VALUES (?, ?, ?)",
                (new_user_id, referral[1], referral[0]),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO referral_rewards "
                "(invitee_user_id, inviter_user_id, reward_type, reward_date, amount) "
                "VALUES (?, ?, 'registration', '', 10)",
                (new_user_id, referral[1]),
            )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return JSONResponse({"error": "该邮箱或用户名已注册"}, status_code=400)
    except Exception:
        conn.rollback()
        return JSONResponse({"error": "注册失败"}, status_code=500)
    finally:
        conn.close()

    token = create_token(email, username, "user")
    return JSONResponse({"message": "注册成功", "token": token, "user": {
        "email": email,
        "username": username,
        "orange_balance": 0,
        "role": "user",
    }}, status_code=201)

# ============================================================
# 登录（密码 / 验证码，成功后签发 token）
# ============================================================
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    is_human, msg = await verify_turnstile(data.get("cf_token"), "login", request)
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)

    login_method = data.get("method", "password")
    if login_method not in ("password", "code"):
        return JSONResponse({"error": "不支持的登录方式"}, status_code=400)

    user = None
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if login_method == "password":
        account = str(data.get("account") or "")
        password = str(data.get("password") or "")
        if not account or not password:
            conn.close()
            return JSONResponse({"error": "账号和密码不能为空"}, status_code=400)
        # email 优先，其次 username，避免 OR 查询歧义
        user = cursor.execute(
            "SELECT id, email, username, password, role, orange_balance FROM users WHERE email=?",
            (account,),
        ).fetchone()
        if not user:
            user = cursor.execute(
                "SELECT id, email, username, password, role, orange_balance FROM users WHERE username=?",
                (account,),
            ).fetchone()
        if not user:
            conn.close()
            return JSONResponse({"error": "用户不存在"}, status_code=401)
        if not verify_password(user[3], password):
            conn.close()
            return JSONResponse({"error": "密码错误"}, status_code=401)
    else:  # code
        email = str(data.get("email") or "")
        code = str(data.get("code") or "")
        if not email or not code:
            conn.close()
            return JSONResponse({"error": "邮箱和验证码不能为空"}, status_code=400)
        user = cursor.execute(
            "SELECT id, email, username, password, role, orange_balance FROM users WHERE email=?",
            (email,),
        ).fetchone()
        if not user:
            conn.close()
            return JSONResponse({"error": "该邮箱未注册"}, status_code=404)
        code_row = validate_code(cursor, email, code)
        if not code_row:
            conn.close()
            return JSONResponse({"error": "验证码错误或已过期"}, status_code=400)
        cursor.execute("UPDATE codes SET is_used=1 WHERE id=?", (code_row[0],))
        conn.commit()
    conn.close()

    uid = user[0]
    email = user[1]
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sign_in_count = c.execute("SELECT COUNT(*) FROM checkin_records WHERE user_id=?", (uid,)).fetchone()[0]
    balance = c.execute("SELECT orange_balance FROM users WHERE id=?", (uid,)).fetchone()[0]
    conn.close()

    role = user[4] if len(user) > 4 else "user"
    password_update_reminder = login_method == "password" and not is_strong_password(password)
    if password_update_reminder:
        conn = sqlite3.connect(DATABASE)
        try:
            conn.execute(
                "INSERT INTO user_messages (user_id, content, is_read, created_at) "
                "SELECT ?, ?, 0, ? WHERE NOT EXISTS "
                "(SELECT 1 FROM user_messages WHERE user_id=? AND content=? AND is_read=0)",
                (uid, WEAK_PASSWORD_REMINDER, datetime.now(timezone.utc).isoformat(), uid, WEAK_PASSWORD_REMINDER),
            )
            conn.commit()
        except sqlite3.Error as error:
            print(f"[password reminder] 写入系统消息失败：{error}")
        finally:
            conn.close()
    token = create_token(email, user[2], role)
    response = {
        "message": f"欢迎回来，{user[2]}！",
        "token": token,
        "user": {
            "email": email or None,
            "has_email": bool(email),
            "username": user[2],
            "orange_balance": int(balance or 0),
            "sign_in_count": int(sign_in_count or 0),
            "role": role,
        },
    }
    if login_method == "password":
        response["password_update_reminder"] = password_update_reminder
    return JSONResponse(response, status_code=200)

# ============================================================
# 用户信息（Bearer token）
# ============================================================
@app.get("/api/profile")
async def get_profile(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    uid, email_value, username, _pw, balance, last_sign_in_date, role, github_username, cpoauth_username = user
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sign_in_count = c.execute("SELECT COUNT(*) FROM checkin_records WHERE user_id=?", (uid,)).fetchone()[0]
    referral = c.execute("SELECT code FROM referral_codes WHERE owner_user_id=?", (uid,)).fetchone()
    conn.close()

    return JSONResponse({
        "email": email_value,
        "has_email": bool(email_value),
        "username": username,
        "orange_balance": int(balance or 0),
        "last_sign_in_date": last_sign_in_date,
        "sign_in_count": int(sign_in_count or 0),
        "has_checked_in_today": bool(last_sign_in_date == today_cn()),
        "role": role,
        "github_username": github_username,
        "cpoauth_username": cpoauth_username,
        "referral_code": referral[0] if referral else None,
    }, status_code=200)

@app.post("/api/user/referral-code")
async def create_referral_code(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    existing = c.execute("SELECT id, code FROM referral_codes WHERE owner_user_id=?", (user[0],)).fetchone()
    if existing and is_valid_referral_code(existing[1]):
        conn.close()
        return JSONResponse({"code": existing[1]}, status_code=200)
    try:
        for _ in range(10):
            code = generate_referral_code()
            try:
                if existing:
                    c.execute("UPDATE referral_codes SET code=? WHERE owner_user_id=?", (code, user[0]))
                else:
                    c.execute("INSERT INTO referral_codes (code, owner_user_id) VALUES (?, ?)", (code, user[0]))
                conn.commit()
                return JSONResponse({"code": code}, status_code=201)
            except sqlite3.IntegrityError:
                conn.rollback()
                existing = c.execute("SELECT id FROM referral_codes WHERE owner_user_id=?", (user[0],)).fetchone()
        return JSONResponse({"error": "邀请码创建失败，请稍后重试"}, status_code=500)
    finally:
        conn.close()

@app.post("/api/referral-code/validate")
async def validate_referral_code(request: Request):
    data = await request.json()
    code = str(data.get("referral_code") or "").strip()
    if not is_valid_referral_code(code):
        return JSONResponse({"valid": False})
    conn = sqlite3.connect(DATABASE)
    valid = find_referral_by_code(conn, code) is not None
    conn.close()
    return JSONResponse({"valid": valid})

@app.get("/api/user/orange-transactions")
async def orange_transactions(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, amount, balance_after, transaction_type, description, created_at "
        "FROM orange_transactions WHERE user_id=? ORDER BY id DESC LIMIT 100",
        (user[0],),
    ).fetchall()
    conn.close()
    return JSONResponse({"transactions": [dict(row) for row in rows]})

@app.get("/api/user/messages")
async def user_messages(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    conn = sqlite3.connect(DATABASE)
    rows = conn.execute(
        "SELECT id, content, created_at FROM user_messages "
        "WHERE user_id=? AND is_read=0 ORDER BY id DESC LIMIT 10",
        (user[0],),
    ).fetchall()
    conn.close()
    return JSONResponse({"messages": [
        {"id": row[0], "content": row[1], "created_at": row[2]} for row in rows
    ]})

@app.get("/api/user/ban-status")
async def user_ban_status(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    conn = sqlite3.connect(DATABASE)
    row = conn.execute(
        "SELECT is_banned, ban_reason, ban_duration_days, banned_until FROM users WHERE id=?",
        (user[0],),
    ).fetchone()
    conn.close()
    banned = is_user_banned(row[0], row[3])
    return JSONResponse({
        "is_banned": banned,
        "reason": row[1] if banned else None,
        "duration_days": row[2] if banned else None,
        "banned_until": row[3] if banned else None,
    })

@app.post("/api/user/messages/read")
async def mark_user_messages_read(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    conn = sqlite3.connect(DATABASE)
    conn.execute("UPDATE user_messages SET is_read=1 WHERE user_id=? AND is_read=0", (user[0],))
    conn.commit()
    conn.close()
    return JSONResponse({"message": "已读"})

# ============================================================
# GitHub OAuth（与线上 worker 对齐）
# ============================================================
def _github_state(payload: dict, ttl_seconds: int = 600) -> str:
    exp = int(datetime.now(timezone.utc).timestamp()) + ttl_seconds
    data = {**payload, "exp": exp}
    signing = f"{_b64url(json.dumps(data, separators=(',', ':')).encode())}"
    sig = hmac.new(SECRET_KEY.encode(), signing.encode(), hashlib.sha256).digest()
    return f"{signing}.{_b64url(sig)}"

def _verify_github_state(state: str):
    try:
        parts = state.split(".")
        if len(parts) != 2:
            return None
        sig = hmac.new(SECRET_KEY.encode(), parts[0].encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(sig), parts[1]):
            return None
        payload = json.loads(_b64url_decode(parts[0]))
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return None
        return payload
    except Exception:
        return None

@app.get("/api/auth/github")
async def github_login(request: Request):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return JSONResponse({"error": "GitHub 登录未配置"}, status_code=500)
    mode = request.query_params.get("mode", "login")
    if mode != "bind":
        mode = "login"
    bind_email = request.query_params.get("bindEmail", "") or ""
    if mode == "bind":
        payload = get_auth_user(request)
        if not payload:
            return JSONResponse({"error": "未登录"}, status_code=401)
        bind_user = _user_by_payload(payload)
        if not bind_user:
            return JSONResponse({"error": "未登录"}, status_code=401)
        state = _github_state({"mode": mode, "bindEmail": payload.get("email", bind_email), "bindUserId": bind_user[0]})
        authorize_url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={quote(GITHUB_CLIENT_ID)}"
            f"&redirect_uri={quote(GITHUB_REDIRECT_URI, safe='')}"
            f"&scope={quote('read:user user:email')}"
            f"&state={state}"
        )
        return JSONResponse({"authorize_url": authorize_url})
    state = _github_state({"mode": mode, "bindEmail": bind_email})
    authorize_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={quote(GITHUB_CLIENT_ID)}"
        f"&redirect_uri={quote(GITHUB_REDIRECT_URI, safe='')}"
        f"&scope={quote('read:user user:email')}"
        f"&state={state}"
    )
    return RedirectResponse(authorize_url, status_code=302)

@app.get("/api/auth/github/callback")
async def github_callback(code: str = "", state: str = ""):
    front_base = "http://127.0.0.1:5173"

    def _redirect(hash_path: str):
        return RedirectResponse(f"{front_base}/#{hash_path}", status_code=302)

    if not code or not state:
        return _redirect("/oauth-callback?error=missing_params")
    parsed = _verify_github_state(state)
    if not parsed:
        return _redirect("/oauth-callback?error=invalid_state")
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return _redirect("/oauth-callback?error=not_configured")
    try:
        async with httpx.AsyncClient() as client:
            tok_res = await client.post(
                "https://github.com/login/oauth/access_token",
                json={"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET,
                      "code": code, "redirect_uri": GITHUB_REDIRECT_URI},
                headers={"Accept": "application/json"},
            )
            tok = tok_res.json()
            access_token = tok.get("access_token")
            if not access_token:
                return _redirect("/oauth-callback?error=github_error")
            gh_res = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}",
                         "Accept": "application/vnd.github+json", "User-Agent": "orange-community"},
            )
            gh = gh_res.json()
        gid = str(gh.get("id", ""))
        gh_login = gh.get("login", "")

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        def _success(u):
            email_v, username, balance, role = u[1], u[2], u[3], u[4]
            token = create_token(email_v, username, role)
            user_json = quote(json.dumps({"email": email_v, "username": username,
                                          "orange_balance": int(balance or 0), "role": role,
                                          "github_username": gh_login}))
            return _redirect(f"/oauth-callback?token={quote(token)}&user={user_json}")

        row = c.execute("SELECT id, email, username, orange_balance, role FROM users WHERE github_id=?",
                        (gid,)).fetchone()
        if row:
            conn.close()
            return _success(row)
        if parsed.get("mode") == "bind":
            owner = (c.execute("SELECT id, email, username, orange_balance, role FROM users WHERE id=?",
                              (parsed.get("bindUserId"),)).fetchone() if parsed.get("bindUserId") else None)
            if not owner:
                conn.close()
                return _redirect("/oauth-callback?error=bind_email_not_found")
            c.execute("UPDATE users SET github_id=?, github_username=? WHERE id=?", (gid, gh_login, owner[0]))
            conn.commit()
            conn.close()
            return _success(owner)
        conn.close()
        return _redirect("/oauth-callback?error=unbound")
    except Exception:
        return _redirect("/oauth-callback?error=github_error")

@app.post("/api/auth/github/unbind")
async def github_unbind(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET github_id=NULL, github_username=NULL WHERE id=?", (user[0],))
    conn.commit()
    conn.close()
    return JSONResponse({"message": "已解绑 GitHub"}, status_code=200)

# ============================================================
# CP OAuth（与线上 worker 对齐）
# ============================================================
@app.get("/api/auth/cpoauth")
async def cpoauth_login(request: Request):
    if not CPOAUTH_CLIENT_ID or not CPOAUTH_CLIENT_SECRET:
        return JSONResponse({"error": "CP OAuth 登录未配置"}, status_code=500)
    mode = request.query_params.get("mode", "login")
    if mode != "bind":
        mode = "login"
    bind_email = request.query_params.get("bindEmail", "") or ""
    if mode == "bind":
        payload = get_auth_user(request)
        if not payload:
            return JSONResponse({"error": "未登录"}, status_code=401)
        bind_user = _user_by_payload(payload)
        if not bind_user:
            return JSONResponse({"error": "未登录"}, status_code=401)
        state = _github_state({"mode": mode, "bindEmail": payload.get("email", bind_email), "bindUserId": bind_user[0]})
        authorize_url = (
            "https://www.cpoauth.com/oauth/authorize"
            f"?response_type=code&client_id={quote(CPOAUTH_CLIENT_ID)}"
            f"&redirect_uri={quote(CPOAUTH_REDIRECT_URI, safe='')}"
            f"&scope={quote('openid profile')}"
            f"&state={state}"
        )
        return JSONResponse({"authorize_url": authorize_url})
    state = _github_state({"mode": mode, "bindEmail": bind_email})
    authorize_url = (
        "https://www.cpoauth.com/oauth/authorize"
        f"?response_type=code&client_id={quote(CPOAUTH_CLIENT_ID)}"
        f"&redirect_uri={quote(CPOAUTH_REDIRECT_URI, safe='')}"
        f"&scope={quote('openid profile')}"
        f"&state={state}"
    )
    return RedirectResponse(authorize_url, status_code=302)

@app.get("/api/auth/cpoauth/callback")
async def cpoauth_callback(code: str = "", state: str = ""):
    front_base = "http://127.0.0.1:5173"

    def _redirect(hash_path: str):
        return RedirectResponse(f"{front_base}/#{hash_path}", status_code=302)

    if not code or not state:
        return _redirect("/oauth-callback?error=missing_params")
    parsed = _verify_github_state(state)
    if not parsed:
        return _redirect("/oauth-callback?error=invalid_state")
    if not CPOAUTH_CLIENT_ID or not CPOAUTH_CLIENT_SECRET:
        return _redirect("/oauth-callback?error=not_configured")
    try:
        async with httpx.AsyncClient() as client:
            tok_res = await client.post(
                "https://www.cpoauth.com/api/oauth/token",
                json={"grant_type": "authorization_code", "code": code,
                      "redirect_uri": CPOAUTH_REDIRECT_URI,
                      "client_id": CPOAUTH_CLIENT_ID, "client_secret": CPOAUTH_CLIENT_SECRET},
                headers={"Accept": "application/json"},
            )
            tok = tok_res.json()
            access_token = tok.get("access_token")
            if not access_token:
                return _redirect("/oauth-callback?error=github_error")
            ui_res = await client.get(
                "https://www.cpoauth.com/api/oauth/userinfo",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            cp = ui_res.json()
        cid = str(cp.get("sub") or cp.get("username") or "")
        if not cid:
            return _redirect("/oauth-callback?error=github_error")
        cp_name = cp.get("username") or cp.get("display_name") or cid

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        def _success(u):
            email_v, username, balance, role = u[1], u[2], u[3], u[4]
            token = create_token(email_v, username, role)
            user_json = quote(json.dumps({"email": email_v, "username": username,
                                          "orange_balance": int(balance or 0), "role": role,
                                          "github_username": u[5] if len(u) > 5 else None,
                                          "cpoauth_username": cp_name}))
            return _redirect(f"/oauth-callback?token={quote(token)}&user={user_json}")

        row = c.execute("SELECT id, email, username, orange_balance, role, github_username FROM users WHERE cpoauth_id=?",
                        (cid,)).fetchone()
        if row:
            conn.close()
            return _success(row)
        if parsed.get("mode") == "bind":
            owner = (c.execute("SELECT id, email, username, orange_balance, role, github_username FROM users WHERE id=?",
                              (parsed.get("bindUserId"),)).fetchone() if parsed.get("bindUserId") else None)
            if not owner:
                conn.close()
                return _redirect("/oauth-callback?error=bind_email_not_found")
            c.execute("UPDATE users SET cpoauth_id=?, cpoauth_username=? WHERE id=?", (cid, cp_name, owner[0]))
            conn.commit()
            conn.close()
            return _success(owner)
        conn.close()
        return _redirect("/oauth-callback?error=unbound")
    except Exception:
        return _redirect("/oauth-callback?error=github_error")

@app.post("/api/auth/cpoauth/unbind")
async def cpoauth_unbind(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET cpoauth_id=NULL, cpoauth_username=NULL WHERE id=?", (user[0],))
    conn.commit()
    conn.close()
    return JSONResponse({"message": "已解绑 CP OAuth"}, status_code=200)

# ============================================================
# 签到（Bearer token + 东八区日期 + 唯一约束）
# ============================================================
@app.post("/api/checkin")
async def checkin(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "请先登录后再签到"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    uid, email, username, balance, last_sign_in_date = user[0], user[1], user[2], user[4], user[5]

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    today = today_cn()
    if last_sign_in_date == today:
        sign_in_count = c.execute(
            "SELECT COUNT(*) FROM checkin_records WHERE user_id=? AND checkin_date=?", (uid, today)
        ).fetchone()[0]
        conn.close()
        return JSONResponse(
            {"error": "今日已签到", "sign_in_count": int(sign_in_count or 0), "orange_balance": int(balance or 0)},
            status_code=409,
        )

    reward = 5
    new_balance = int(balance or 0) + reward
    try:
        c.execute("INSERT INTO checkin_records (user_id, checkin_date, points) VALUES (?, ?, ?)", (uid, today, reward))
    except sqlite3.IntegrityError:
        conn.close()
        return JSONResponse({"error": "今日已签到"}, status_code=409)
    c.execute("UPDATE users SET orange_balance=?, last_sign_in_date=? WHERE id=?", (new_balance, today, uid))
    c.execute(
        "INSERT INTO orange_transactions "
        "(user_id, amount, balance_after, transaction_type, description) "
        "VALUES (?, ?, ?, 'checkin', '每日签到奖励')",
        (uid, reward, new_balance),
    )
    c.execute(
        "INSERT OR IGNORE INTO referral_rewards "
        "(invitee_user_id, inviter_user_id, reward_type, reward_date, amount) "
        "SELECT invitee_user_id, inviter_user_id, 'daily_checkin', ?, 2 "
        "FROM referral_attributions WHERE invitee_user_id = ?",
        (today, uid),
    )
    conn.commit()
    sign_in_count = c.execute("SELECT COUNT(*) FROM checkin_records WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()

    return JSONResponse({
        "message": "签到成功",
        "points": reward,
        "orange_balance": new_balance,
        "last_sign_in_date": today,
        "sign_in_count": int(sign_in_count or 0),
        "has_checked_in_today": True,
    }, status_code=200)

# ============================================================
# 管理员：用户列表（Bearer token + admin 角色）
# ============================================================
def _admin_or_none(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return None, "未登录"
    if payload.get("role") not in {"admin", "super_admin"}:
        return None, "无权限"
    admin = _user_by_payload(payload)
    if not admin or admin[6] not in {"admin", "super_admin"}:
        return None, "无权限"
    return admin, None

def is_protected_user(email, username) -> bool:
    protected_emails = set(PROTECTED_ADMIN_EMAILS)
    configured_email = os.getenv("ORANGE_PROTECTED_ADMIN_EMAIL")
    if configured_email:
        protected_emails.add(configured_email)
    protected_usernames = set(PROTECTED_ADMIN_USERNAMES)
    configured_username = os.getenv("ORANGE_PROTECTED_ADMIN_USERNAME")
    if configured_username:
        protected_usernames.add(configured_username)
    return email in protected_emails or username in protected_usernames

def role_label(role: str) -> str:
    return {"user": "普通用户", "admin": "管理员", "super_admin": "超级管理员"}.get(role, role)

@app.get("/api/admin/users")
async def admin_list_users(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    rows = c.execute(
        "SELECT id, email, username, orange_balance, role, is_banned, ban_reason, ban_duration_days, banned_until "
        "FROM users ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return JSONResponse({"users": [
        {
            "id": r[0], "email": r[1], "username": r[2],
            "orange_balance": int(r[3] or 0), "role": r[4] or "user",
            "is_banned": is_user_banned(r[5], r[8]),
            "ban_reason": r[6], "ban_duration_days": r[7], "banned_until": r[8],
            "is_protected": is_protected_user(r[1], r[2]),
        }
        for r in rows
    ], "can_manage_super_admins": is_protected_user(admin[1], admin[2])}, status_code=200)

# ============================================================
# 管理员：更新用户（Bearer token + 非负余额 + 保护账号）
# ============================================================
PROTECTED_ADMIN_EMAILS = {"[REDACTED]"}
PROTECTED_ADMIN_USERNAMES = {"orange"}

@app.post("/api/admin/users/update")
async def admin_update_user(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    data = await request.json()
    user_id = data.get("id")
    new_balance = data.get("orange_balance")
    new_role = data.get("role")
    if user_id is None or new_balance is None or not new_role:
        return JSONResponse({"error": "参数不完整"}, status_code=400)

    try:
        balance = int(new_balance)
    except (TypeError, ValueError):
        return JSONResponse({"error": "橙子数量必须为整数"}, status_code=400)
    if isinstance(new_balance, float) and not new_balance.is_integer():
        return JSONResponse({"error": "橙子数量必须为整数"}, status_code=400)
    if balance < 0:
        return JSONResponse({"error": "橙子数量不能为负数"}, status_code=400)

    normalized_role = str(new_role).strip().lower()
    if normalized_role not in {"admin", "super_admin", "user"}:
        return JSONResponse({"error": "角色值无效"}, status_code=400)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    target = c.execute(
        "SELECT id, email, username, orange_balance, role, is_banned, banned_until "
        "FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not target:
        conn.close()
        return JSONResponse({"error": "用户不存在"}, status_code=404)

    target_email, target_username = target[1], target[2]
    target_protected = is_protected_user(target_email, target_username)
    admin_protected = is_protected_user(admin[1], admin[2])
    target_role = target[4] or "user"
    if target_protected and (target_role != "super_admin" or normalized_role != target_role):
        conn.close()
        return JSONResponse({"error": "orange 账号的超级管理员角色不可修改"}, status_code=403)
    if normalized_role == "super_admin" and is_user_banned(target[5], target[6]):
        conn.close()
        return JSONResponse({"error": "请先解除该账号的封禁，再授予超级管理员权限"}, status_code=400)
    if target[0] == admin[0] and normalized_role != target_role:
        conn.close()
        return JSONResponse({"error": "管理员不能修改自己的角色"}, status_code=403)
    if normalized_role != target_role and (normalized_role == "super_admin" or target_role == "super_admin") and not admin_protected:
        conn.close()
        return JSONResponse({"error": "只有 orange 账号可以授予或撤销超级管理员权限"}, status_code=403)

    old_balance = int(target[3] or 0)
    c.execute("UPDATE users SET orange_balance=?, role=? WHERE id=?", (balance, normalized_role, user_id))
    if old_balance != balance:
        c.execute(
            "INSERT INTO orange_transactions "
            "(user_id, amount, balance_after, transaction_type, description) "
            "VALUES (?, ?, ?, 'admin_adjustment', '管理员调整橙子余额')",
            (user_id, balance - old_balance, balance),
        )
    c.execute(
        "INSERT INTO admin_audit_logs "
        "(admin_email, admin_username, target_user_id, target_email, target_username, "
        "old_balance, new_balance, old_role, new_role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            admin[1] or "", admin[2], target[0], target[1] or "", target[2],
            old_balance, balance, target_role, normalized_role,
        ),
    )
    c.execute(
        "INSERT INTO user_messages (user_id, content, is_read, created_at) VALUES (?, ?, 0, ?)",
        (
            user_id,
            f"管理员修改了你的账号信息\n橙子数量：{old_balance} → {balance}\n角色：{role_label(target_role)} → {role_label(normalized_role)}",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return JSONResponse({"message": "更新成功", "id": user_id, "orange_balance": balance, "role": normalized_role}, status_code=200)

# ============================================================
# 管理员：操作日志（Bearer token + activity_logs，对齐线上）
# ============================================================
@app.get("/api/posts")
async def list_posts(request: Request):
    try:
        limit = int(request.query_params.get("limit", "50"))
    except ValueError:
        limit = 50
    limit = min(max(limit, 1), 100)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, user_id, username, title, content, created_at FROM posts ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return JSONResponse({"posts": [dict(row) for row in rows]})

@app.post("/api/posts")
async def create_post(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    conn = sqlite3.connect(DATABASE)
    moderation = conn.execute(
        "SELECT is_banned, ban_reason, banned_until FROM users WHERE id=?",
        (user[0],),
    ).fetchone()
    if is_user_banned(moderation[0], moderation[2]):
        conn.close()
        return JSONResponse({
            "error": "你的账号已被封禁，暂时不能发帖",
            "reason": moderation[1] or "",
            "banned_until": moderation[2],
        }, status_code=403)
    data = await request.json()
    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or "").strip()
    if not title:
        conn.close()
        return JSONResponse({"error": "标题不能为空"}, status_code=400)
    if len(title) > 80:
        conn.close()
        return JSONResponse({"error": "标题最长 80 字"}, status_code=400)
    if not content:
        conn.close()
        return JSONResponse({"error": "内容不能为空"}, status_code=400)
    if len(content) > 5000:
        conn.close()
        return JSONResponse({"error": "内容最长 5000 字"}, status_code=400)
    filtered_title = filter_profanity(title)
    filtered_content = filter_profanity(content)
    created_at = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO posts (user_id, username, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (user[0], user[2], filtered_title["filteredText"], filtered_content["filteredText"], created_at),
    )
    post = {
        "id": cursor.lastrowid,
        "user_id": user[0],
        "username": user[2],
        "title": filtered_title["filteredText"],
        "content": filtered_content["filteredText"],
        "created_at": created_at,
    }
    conn.commit()
    conn.close()
    profane_words = list(dict.fromkeys(filtered_title["profaneWords"] + filtered_content["profaneWords"]))
    return JSONResponse({
        "safe": not profane_words,
        "filteredTitle": filtered_title["filteredText"],
        "filteredContent": filtered_content["filteredText"],
        "profaneWords": profane_words,
        "post": post,
    })

@app.delete("/api/posts")
async def delete_post(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    try:
        post_id = int(request.query_params.get("id", ""))
    except ValueError:
        post_id = 0
    if not post_id:
        return JSONResponse({"error": "缺少帖子 id"}, status_code=400)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    post = c.execute("SELECT id, user_id, title FROM posts WHERE id=?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return JSONResponse({"error": "帖子不存在"}, status_code=404)
    if post[1] != user[0] and user[6] not in {"admin", "super_admin"}:
        conn.close()
        return JSONResponse({"error": "无权删除该帖子"}, status_code=403)
    c.execute("DELETE FROM posts WHERE id=?", (post_id,))
    if user[6] in {"admin", "super_admin"} and post[1] != user[0]:
        c.execute(
            "INSERT INTO user_messages (user_id, content, is_read, created_at) VALUES (?, ?, 0, ?)",
            (post[1], f"管理员删除了你的帖子《{post[2]}》", datetime.now(timezone.utc).isoformat()),
        )
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "id": post_id})

@app.post("/api/admin/users/ban")
async def admin_ban_user(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    data = await request.json()
    try:
        user_id = int(data.get("id"))
    except (TypeError, ValueError):
        return JSONResponse({"error": "用户编号无效"}, status_code=400)
    reason = str(data.get("reason") or "").strip()
    raw_duration = data.get("duration_days")
    try:
        duration_days = None if raw_duration in (None, "") else int(raw_duration)
    except (TypeError, ValueError):
        return JSONResponse({"error": "临时封禁天数必须为正整数"}, status_code=400)
    if isinstance(raw_duration, float) and not raw_duration.is_integer():
        return JSONResponse({"error": "临时封禁天数必须为正整数"}, status_code=400)
    if user_id <= 0:
        return JSONResponse({"error": "用户编号无效"}, status_code=400)
    if not reason:
        return JSONResponse({"error": "封禁原因必填"}, status_code=400)
    if len(reason) > 500:
        return JSONResponse({"error": "封禁原因不能超过 500 字"}, status_code=400)
    if duration_days is not None and duration_days <= 0:
        return JSONResponse({"error": "临时封禁天数必须为正整数"}, status_code=400)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    target = c.execute("SELECT id, email, username, role FROM users WHERE id=?", (user_id,)).fetchone()
    if not target:
        conn.close()
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    if target[0] == admin[0]:
        conn.close()
        return JSONResponse({"error": "不能封禁自己的账号"}, status_code=403)
    if is_protected_user(target[1], target[2]):
        conn.close()
        return JSONResponse({"error": "orange 账号不能被封禁"}, status_code=403)
    if target[3] == "super_admin":
        conn.close()
        return JSONResponse({"error": "超级管理员不能被封禁"}, status_code=403)

    banned_until = None
    if duration_days is not None:
        try:
            expiry = datetime.now(timezone.utc) + timedelta(days=duration_days)
        except OverflowError:
            conn.close()
            return JSONResponse({"error": "临时封禁期限超出有效范围"}, status_code=400)
        if expiry.year > 9998:
            conn.close()
            return JSONResponse({"error": "临时封禁期限超出有效范围"}, status_code=400)
        banned_until = expiry.isoformat()
        message = (
            f"你的账号已被临时封禁并禁言 {duration_days} 天，"
            f"至 {format_beijing_datetime(banned_until)}。原因：{reason}"
        )
    else:
        message = f"你的账号已被永久封禁并禁言。原因：{reason}"
    c.execute(
        "UPDATE users SET is_banned=1, ban_reason=?, ban_duration_days=?, banned_until=? WHERE id=?",
        (reason, duration_days, banned_until, user_id),
    )
    c.execute(
        "INSERT INTO user_messages (user_id, content, is_read, created_at) VALUES (?, ?, 0, ?)",
        (user_id, message, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return JSONResponse({"message": "账号已封禁", "is_banned": True, "banned_until": banned_until})

@app.post("/api/admin/users/unban")
async def admin_unban_user(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    data = await request.json()
    try:
        user_id = int(data.get("id"))
    except (TypeError, ValueError):
        return JSONResponse({"error": "用户编号无效"}, status_code=400)
    if user_id <= 0:
        return JSONResponse({"error": "用户编号无效"}, status_code=400)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    target = c.execute(
        "SELECT id, email, username, role, is_banned, banned_until FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not target:
        conn.close()
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    if target[0] == admin[0]:
        conn.close()
        return JSONResponse({"error": "不能操作自己的封禁状态"}, status_code=403)
    if is_protected_user(target[1], target[2]):
        conn.close()
        return JSONResponse({"error": "orange 账号不能被封禁"}, status_code=403)
    if target[3] == "super_admin":
        conn.close()
        return JSONResponse({"error": "超级管理员不能被封禁"}, status_code=403)
    if not is_user_banned(target[4], target[5]):
        conn.close()
        return JSONResponse({"error": "该账号当前未被封禁"}, status_code=400)
    c.execute(
        "UPDATE users SET is_banned=0, ban_reason=NULL, ban_duration_days=NULL, banned_until=NULL WHERE id=?",
        (user_id,),
    )
    c.execute(
        "INSERT INTO user_messages (user_id, content, is_read, created_at) VALUES (?, ?, 0, ?)",
        (user_id, "你的账号封禁已解除，现已恢复发帖权限。", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return JSONResponse({"message": "已解除账号封禁", "is_banned": False})

@app.get("/api/admin/logs")
async def admin_logs(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    rows = c.execute(
        "SELECT id, actor_email, actor_username, action, action_detail, method, path, status, created_at "
        "FROM activity_logs ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return JSONResponse({"logs": [
        {
            "id": r[0], "actor_email": r[1], "actor_username": r[2],
            "action": r[3], "action_detail": r[4], "method": r[5],
            "path": r[6], "status": r[7], "created_at": r[8],
        }
        for r in rows
    ]}, status_code=200)

# ============================================================
# 管理员：邀请码（仅管理员，一次性）
# ============================================================
@app.get("/api/admin/invites")
async def admin_list_invites(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    rows = c.execute(
        "SELECT ic.id, ic.code, ic.created_by, ic.created_at, ic.expires_at, ic.status, "
        "ic.used_by, ic.used_at, u.username "
        "FROM invite_codes ic LEFT JOIN users u ON u.id = ic.used_by "
        "ORDER BY ic.id DESC LIMIT 100"
    ).fetchall()
    conn.close()

    def _parse_ts(value):
        if not value:
            return None
        s = str(value).strip()
        try:
            if s.endswith("Z") or s.endswith("+00:00"):
                return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            try:
                return datetime.fromisoformat(s).timestamp()
            except Exception:
                return None

    now_ts = datetime.now(timezone.utc).timestamp()
    invites = []
    for r in rows:
        status = r[5]
        if status == "active":
            ts = _parse_ts(r[4])
            if ts is not None and ts < now_ts:
                status = "expired"
        invites.append({
            "id": r[0], "code": r[1], "created_by": r[2], "created_at": r[3],
            "expires_at": r[4], "status": status, "used_by": r[6], "used_at": r[7],
            "used_by_name": r[8],
        })
    return JSONResponse({"invites": invites}, status_code=200)


@app.post("/api/admin/invites")
async def admin_create_invite(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    data = await request.json()
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    code = "".join(random.choice(chars) for _ in range(8))
    try:
        days = int(data.get("expires_in_days", 7))
    except (TypeError, ValueError):
        return JSONResponse({"error": "有效期天数请填写大于 0 的整数"}, status_code=400)
    if days <= 0:
        return JSONResponse({"error": "有效期天数请填写大于 0 的整数"}, status_code=400)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DATABASE)
    conn.execute("INSERT INTO invite_codes (code, created_by, expires_at) VALUES (?, ?, ?)",
                 (code, admin[2] or admin[1], expires_at))
    conn.commit()
    conn.close()
    return JSONResponse({"message": "邀请码已生成", "code": code, "expires_at": expires_at}, status_code=201)


# ============================================================
# 邀请注册（无邮箱用户以用户名记录，email 允许为空）
# ============================================================
@app.post("/api/register/invite")
async def register_invite(request: Request):
    data = await request.json()
    is_human, msg = await verify_turnstile(data.get("cf_token"), "register", request)
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)
    invite = str(data.get("invite") or "").strip()
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    email = str(data.get("email") or "").strip()
    referral_code = (data.get("referral_code") or "").strip()
    if not invite or not username or not password:
        return JSONResponse({"error": "请填写邀请码、用户名和密码"}, status_code=400)
    input_error = validate_registration_input(username, password)
    if input_error:
        return JSONResponse({"error": input_error}, status_code=400)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    inv = c.execute("SELECT id, status, expires_at FROM invite_codes WHERE code=?", (invite,)).fetchone()
    if not inv:
        conn.close()
        return JSONResponse({"error": "邀请码不存在"}, status_code=400)
    if inv[1] != "active":
        conn.close()
        return JSONResponse({"error": "邀请码已失效"}, status_code=400)
    if inv[2] and datetime.strptime(inv[2], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() < utc_timestamp():
        conn.close()
        return JSONResponse({"error": "邀请码已过期"}, status_code=400)
    if c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
        conn.close()
        return JSONResponse({"error": "该用户名已注册"}, status_code=400)
    if email and c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
        conn.close()
        return JSONResponse({"error": "该邮箱已被绑定"}, status_code=400)
    referral = None
    if referral_code:
        if not is_valid_referral_code(referral_code):
            conn.close()
            return JSONResponse({"error": "拉新邀请码无效"}, status_code=400)
        referral = find_referral_by_code(conn, referral_code)
        if not referral:
            conn.close()
            return JSONResponse({"error": "拉新邀请码无效"}, status_code=400)
        if referral[3].lower() == username.lower() or (
            email and referral[2] and referral[2].lower() == email.lower()
        ):
            conn.close()
            return JSONResponse({"error": "不能使用自己的拉新邀请码注册"}, status_code=400)
    hashed = hash_password(password)
    c.execute("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", (email or None, username, hashed))
    new_id = c.lastrowid
    c.execute("UPDATE invite_codes SET status='used', used_by=?, used_at=? WHERE id=?",
              (new_id, utc_now(), inv[0]))
    if referral:
        c.execute(
            "INSERT INTO referral_attributions (invitee_user_id, inviter_user_id, referral_code_id) VALUES (?, ?, ?)",
            (new_id, referral[1], referral[0]),
        )
        c.execute(
            "INSERT OR IGNORE INTO referral_rewards "
            "(invitee_user_id, inviter_user_id, reward_type, reward_date, amount) "
            "VALUES (?, ?, 'registration', '', 10)",
            (new_id, referral[1]),
        )
    conn.commit()
    conn.close()
    token = create_token(email or "", username, "user")
    return JSONResponse({"message": "注册成功", "token": token, "user": {
        "email": email or None, "has_email": bool(email), "username": username,
        "orange_balance": 0, "role": "user",
    }}, status_code=201)


# ============================================================
# 绑定邮箱（无邮箱用户）
# ============================================================
@app.post("/api/user/bind-email")
async def bind_email(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    user = _user_by_payload(payload)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    data = await request.json()
    email = str(data.get("email") or "").strip()
    code = str(data.get("code") or "").strip()
    if not email or not code:
        return JSONResponse({"error": "邮箱和验证码不能为空"}, status_code=400)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    if c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
        conn.close()
        return JSONResponse({"error": "该邮箱已被其他账号绑定"}, status_code=400)
    code_row = validate_code(c, email, code)
    if not code_row:
        conn.close()
        return JSONResponse({"error": "验证码错误或已过期"}, status_code=400)
    c.execute("DELETE FROM codes WHERE id=?", (code_row[0],))
    c.execute("UPDATE users SET email=? WHERE id=?", (email, user[0]))
    conn.commit()
    conn.close()
    return JSONResponse({"message": "邮箱绑定成功", "email": email, "has_email": True}, status_code=200)


async def probe_dashboard_domain(client: httpx.AsyncClient, domain: str):
    try:
        response = await client.head(f"https://{domain}")
        if response.is_success:
            return {"status": "OK", "detail": f"HTTPS 访问成功，服务器返回 HTTP {response.status_code}"}
        return {"status": "WARN", "detail": f"HTTPS 请求已到达，但服务器返回 HTTP {response.status_code}"}
    except httpx.HTTPError as error:
        print(f"[dashboard] 探测 {domain} 失败：{type(error).__name__}")
        return {"status": "WARN", "detail": f"探测失败（{type(error).__name__}）"}

async def lookup_git_head(client: httpx.AsyncClient):
    error_detail = "无法获取 Git 提交号"
    try:
        response = await client.get(
            "https://api.github.com/repos/orange838/orange-community/commits/main",
            headers={
                "User-Agent": "orange-community-monitor",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        sha = str(response.json().get("sha") or "")[:7]
        if not sha:
            raise ValueError("GitHub API 响应中没有提交 SHA")
        return sha, ""
    except (httpx.HTTPError, ValueError, TypeError) as error:
        error_detail = str(error) or type(error).__name__
        print(f"[dashboard] GitHub API commit lookup failed: {type(error).__name__}")
    try:
        response = await client.get(
            "https://github.com/orange838/orange-community/commits/main.atom",
            headers={"User-Agent": "orange-community-monitor", "Accept": "application/atom+xml"},
        )
        response.raise_for_status()
        match = re.search(r"<id>tag:github\.com,2008:Grit::Commit/([0-9a-f]{40})</id>", response.text, re.I)
        if not match:
            raise ValueError("GitHub Atom feed 中没有提交 SHA")
        return match.group(1)[:7], ""
    except (httpx.HTTPError, ValueError) as error:
        error_detail += f"；Atom 备用源失败：{error}"
        print(f"[dashboard] GitHub Atom feed commit lookup failed: {type(error).__name__}")
        return "N/A", error_detail

def dashboard_count_rows(table: str):
    conn = sqlite3.connect(DATABASE)
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error as error:
        print(f"[dashboard] 读取表 {table} 统计失败：{error}")
        return None
    finally:
        conn.close()

async def build_local_dashboard_status():
    async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
        domain_checks, (git_head, git_head_error) = await asyncio.gather(
            asyncio.gather(*(probe_dashboard_domain(client, domain) for domain in DASHBOARD_DOMAINS)),
            lookup_git_head(client),
        )
    counts = {
        "users": dashboard_count_rows("users"),
        "checkins": dashboard_count_rows("checkin_records"),
        "invites": dashboard_count_rows("invite_codes"),
        "verifications": dashboard_count_rows("turnstile_verification_logs"),
        "posts": dashboard_count_rows("posts"),
        "messages": dashboard_count_rows("user_messages"),
    }
    conn = sqlite3.connect(DATABASE)
    try:
        turnstile = conn.execute(
            "SELECT SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN passed=0 THEN 1 ELSE 0 END) "
            "FROM turnstile_verification_logs WHERE created_at >= datetime('now', '-24 hours')"
        ).fetchone()
        passed, failed = int(turnstile[0] or 0), int(turnstile[1] or 0)
    except sqlite3.Error as error:
        print(f"[dashboard] Turnstile 汇总读取失败：{error}")
        passed = failed = None
    finally:
        conn.close()
    total = passed + failed if passed is not None and failed is not None else None
    pass_rate = (
        "无法获取" if total is None
        else "暂无数据" if total == 0
        else f"{int(passed / total * 100 + 0.5)}%"
    )
    pages_status = "OK" if all(item["status"] == "OK" for item in domain_checks) else "WARN"
    d1_status = "OK" if all(value is not None for value in counts.values()) else "WARN"
    https_detail = "\n".join(
        f"{domain}：{check['detail']}" for domain, check in zip(DASHBOARD_DOMAINS, domain_checks)
    )
    values = lambda value: "无法获取" if value is None else str(value)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "generatedAt": now,
        "source": "local-fastapi",
        "summary": {
            "pages": {"status": pages_status, "domain": f"{len(DASHBOARD_DOMAINS)} 个站点域名已逐一检查"},
            "worker": {"status": "OK", "route": "GET /api/status 本次请求成功，本地 FastAPI 正在运行"},
            "d1": {"status": d1_status, "databaseName": "orange_community.db"},
            "https": {
                "status": pages_status,
                "domains": f"{len(DASHBOARD_DOMAINS)} 个站点均可通过 HTTPS 访问"
                if pages_status == "OK" else "存在访问异常，请查看下方域名检查结果",
            },
            "api": {"status": "OK", "endpoint": "GET /api/status 本次请求成功返回"},
            "deploy": {"status": "WARN" if git_head == "N/A" else "OK", "branch": "main"},
            "turnstile": {
                "status": "WARN" if total is None or counts["verifications"] is None else "OK",
                "passRate": pass_rate,
            },
        },
        "resources": [
            {
                "name": "网站与监控站点",
                "type": "Pages 托管与自定义域名",
                "status": pages_status,
                "detail": (
                    f"社区网站 Pages 项目：orange-community\n监控范围内共检查 {len(DASHBOARD_DOMAINS)} 个站点地址，"
                    f"逐项结果见“网站 HTTPS 连接”。\n" + "\n".join(f"• {domain}" for domain in DASHBOARD_DOMAINS)
                ),
            },
            {
                "name": "本地后端接口",
                "type": "FastAPI",
                "status": "OK",
                "detail": "本次 GET /api/status 请求已成功处理，本地 FastAPI 正在运行。",
            },
            {
                "name": "社区数据库",
                "type": "SQLite 数据库",
                "status": d1_status,
                "detail": (
                    f"数据库：orange_community.db\n注册用户：{values(counts['users'])} 位\n"
                    f"帖子：{values(counts['posts'])} 条\n站内消息：{values(counts['messages'])} 条"
                ),
            },
            {"name": "网站 HTTPS 连接", "type": "域名加密连接检查", "status": pages_status, "detail": https_detail},
            {
                "name": "本地资源接入",
                "type": "FastAPI 与 SQLite 连接",
                "status": d1_status,
                "detail": "本地 FastAPI 已正常响应，且监控已读取 SQLite 统计。" if d1_status == "OK"
                else "SQLite 部分统计读取失败，请查看对应数据明细。",
            },
            {
                "name": "最新代码版本",
                "type": "main 分支",
                "status": "WARN" if git_head == "N/A" else "OK",
                "detail": git_head_error if git_head == "N/A" else f"Git 提交：{git_head}",
            },
            {
                "name": "Turnstile",
                "type": "Security",
                "status": "WARN" if total is None or counts["verifications"] is None else "OK",
                "detail": (
                    "最近 24 小时统计无法获取" if total is None
                    else f"{passed} passed / {failed} failed (24h)"
                ),
            },
        ],
        "domains": [
            {"name": domain, "value": check["detail"]}
            for domain, check in zip(DASHBOARD_DOMAINS, domain_checks)
        ],
        "d1Details": [
            {"name": "Database name", "value": "orange_community.db"},
            {"name": "Tables", "value": "SQLite"},
            {"name": "Users", "value": values(counts["users"])},
            {"name": "Check-ins", "value": values(counts["checkins"])},
            {"name": "Invite codes", "value": values(counts["invites"])},
            {"name": "Turnstile records", "value": values(counts["verifications"])},
            {"name": "Posts", "value": values(counts["posts"])},
            {"name": "Messages", "value": values(counts["messages"])},
        ],
        "deployments": [
            {"name": "Project", "value": "orange-community"},
            {"name": "Branch", "value": "main"},
            {"name": "Git head", "value": git_head_error if git_head == "N/A" else git_head},
        ],
        "turnstile": [
            {"name": "Passed", "value": values(passed)},
            {"name": "Failed", "value": values(failed)},
            {"name": "Total", "value": values(total)},
            {"name": "Pass rate", "value": pass_rate},
        ],
    }

@app.get("/api/status")
async def dashboard_status():
    return JSONResponse(await build_local_dashboard_status())

@app.get("/api/health")
async def health():
    return JSONResponse({"ok": True, "runtime": "local-fastapi"}, status_code=200)

init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=3000, reload=True)
