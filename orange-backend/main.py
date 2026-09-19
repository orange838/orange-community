import os
import base64
import hashlib
import hmac
import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from urllib.parse import quote
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
DATABASE = "orange_community.db"

# 签到日期统一按东八区计算（与线上 worker 对齐，避免 UTC 日期错位）
CN_TZ = timezone(timedelta(hours=8))
CODE_TTL_MINUTES = 5
SEND_CODE_COOLDOWN_SECONDS = 60
CODE_MAX_ATTEMPTS = 5
TOKEN_TTL_HOURS = 24 * 7

# ============================================================
# 密码哈希：与线上 worker 完全一致 pbkdf2:sha256:600000$saltHex$keyHex
# ============================================================
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000, dklen=32)
    return f"pbkdf2:sha256:600000${salt.hex()}${key.hex()}"

def verify_password(stored: str, password: str) -> bool:
    if not stored:
        return False
    # 新格式：pbkdf2:sha256:600000$saltHex$keyHex
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

# ============================================================
# 数据库初始化（与线上 schema.sql 对齐，含 activity_logs / turnstile 日志）
# ============================================================
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT UNIQUE NOT NULL, "
        "username TEXT NOT NULL, "
        "password TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "orange_balance INTEGER DEFAULT 0, "
        "last_sign_in_date TEXT, "
        "role TEXT DEFAULT 'user', "
        "github_id TEXT UNIQUE, "
        "github_username TEXT)"
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
        "email TEXT NOT NULL, "
        "checkin_date TEXT NOT NULL, "
        "points INTEGER DEFAULT 5, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
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

    code_cols = [row[1] for row in c.execute("PRAGMA table_info(codes)").fetchall()]
    if "attempts" not in code_cols:
        c.execute("ALTER TABLE codes ADD COLUMN attempts INTEGER DEFAULT 0")
    if "created_at" not in code_cols:
        c.execute("ALTER TABLE codes ADD COLUMN created_at TEXT")

    # 签到唯一约束（与线上 schema.sql 的 UNIQUE(email, checkin_date) 对齐，防并发刷分）
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_checkin_email_date ON checkin_records(email, checkin_date)")
    except sqlite3.OperationalError:
        pass

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

# ============================================================
# Cloudflare Turnstile 人机验证
# ============================================================
async def verify_turnstile(token, expected_action: str = None):
    """向 Cloudflare 发送 token 进行人机验证，并记录日志"""
    log_result = lambda passed: _log_turnstile(expected_action, passed)

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
            ok = result.get("success") is True
            await log_result(ok)
            return (True, "验证通过") if ok else (False, "人机验证失败，请重试")
    except Exception as e:
        await log_result(False)
        return False, f"验证服务异常: {str(e)}"

def _log_turnstile(action, passed):
    try:
        conn = sqlite3.connect(DATABASE)
        conn.execute(
            "INSERT INTO turnstile_verification_logs (action, passed) VALUES (?, ?)",
            (action, 1 if passed else 0),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

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
    elif url_path == "/api/admin/users":
        action_detail = "查看用户列表"
    elif url_path == "/api/admin/logs":
        action_detail = "查看最近 100 条操作日志"
    elif url_path == "/api/admin/users/update":
        action_detail = f"提交用户修改：橙子数量 {body.get('orange_balance', '未提供')}，角色 {body.get('role', '')}"

    action_name = {
        "/api/profile": "查看个人信息",
        "/api/send-code": "发送验证码",
        "/api/register": "注册账号",
        "/api/login": "登录账号",
        "/api/checkin": "签到",
        "/api/admin/users": "查看用户管理",
        "/api/admin/users/update": "修改用户信息",
        "/api/admin/logs": "查看操作日志",
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
@app.post("/api/send-code")
async def send_code(request: Request):
    data = await request.json()
    email = (data.get("email") or "").strip()
    code_type = data.get("type", "register")
    if not email:
        return JSONResponse({"error": "没邮箱"}, status_code=400)
    if not RESEND_API_KEY:
        return JSONResponse({"error": "服务器配置错误：缺少 RESEND_API_KEY"}, status_code=500)

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

    subject = "Orange Community 登录验证码" if code_type == "login" else "Orange Community 注册验证码"
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
    is_human, msg = await verify_turnstile(data.get("cf_token"), "register")
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)

    email = (data.get("email") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password")
    code = data.get("code")
    if not all([email, password, code]):
        return JSONResponse({"error": "缺参数"}, status_code=400)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        row = cursor.execute(
            "SELECT id, attempts FROM codes WHERE email=? AND code=? AND is_used=0 AND expires_at>? ORDER BY id DESC LIMIT 1",
            (email, code, utc_now()),
        ).fetchone()
        if not row:
            # 记录一次失败尝试
            cursor.execute(
                "UPDATE codes SET attempts = attempts + 1 WHERE email=? AND code=? AND is_used=0",
                (email, code),
            )
            conn.commit()
            return JSONResponse({"error": "码不对或过期"}, status_code=400)

        code_id = row[0]
        cursor.execute("UPDATE codes SET is_used=1 WHERE id=?", (code_id,))
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (email, username, password) VALUES (?, ?, ?)",
            (email, username, hashed),
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
    is_human, msg = await verify_turnstile(data.get("cf_token"), "login")
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)

    login_method = data.get("method", "password")
    if login_method not in ("password", "code"):
        return JSONResponse({"error": "不支持的登录方式"}, status_code=400)

    user = None
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if login_method == "password":
        account = data.get("account")
        password = data.get("password")
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
        email = data.get("email")
        code = data.get("code")
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
        code_row = cursor.execute(
            "SELECT id, attempts FROM codes WHERE email=? AND code=? AND is_used=0 AND expires_at>?",
            (email, code, utc_now()),
        ).fetchone()
        if not code_row:
            cursor.execute(
                "UPDATE codes SET attempts = attempts + 1 WHERE email=? AND code=? AND is_used=0",
                (email, code),
            )
            conn.commit()
            conn.close()
            return JSONResponse({"error": "验证码错误或已过期"}, status_code=400)
        cursor.execute("UPDATE codes SET is_used=1 WHERE id=?", (code_row[0],))
        conn.commit()
    conn.close()

    email = user[1]
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sign_in_count = c.execute("SELECT COUNT(*) FROM checkin_records WHERE email=?", (email,)).fetchone()[0]
    balance = c.execute("SELECT orange_balance FROM users WHERE email=?", (email,)).fetchone()[0]
    conn.close()

    role = user[4] if len(user) > 4 else "user"
    token = create_token(email, user[2], role)
    return JSONResponse({
        "message": f"欢迎回来，{user[2]}！",
        "token": token,
        "user": {
            "email": email,
            "username": user[2],
            "orange_balance": int(balance or 0),
            "sign_in_count": int(sign_in_count or 0),
            "role": role,
        },
    }, status_code=200)

# ============================================================
# 用户信息（Bearer token）
# ============================================================
@app.get("/api/profile")
async def get_profile(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "未登录"}, status_code=401)
    email = payload.get("email")
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    user = c.execute(
        "SELECT email, username, orange_balance, last_sign_in_date, role, github_username FROM users WHERE email=?",
        (email,),
    ).fetchone()
    if not user:
        conn.close()
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    email_value, username, balance, last_sign_in_date, role, github_username = user
    sign_in_count = c.execute("SELECT COUNT(*) FROM checkin_records WHERE email=?", (email_value,)).fetchone()[0]
    conn.close()

    return JSONResponse({
        "email": email_value,
        "username": username,
        "orange_balance": int(balance or 0),
        "last_sign_in_date": last_sign_in_date,
        "sign_in_count": int(sign_in_count or 0),
        "has_checked_in_today": bool(last_sign_in_date == today_cn()),
        "role": role,
        "github_username": github_username,
    }, status_code=200)

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
        bind_email = payload.get("email", bind_email)
        state = _github_state({"mode": mode, "bindEmail": bind_email})
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
            owner = c.execute("SELECT id, email, username, orange_balance, role FROM users WHERE email=?",
                              (parsed.get("bindEmail", ""),)).fetchone()
            if not owner:
                conn.close()
                return _redirect("/oauth-callback?error=bind_email_not_found")
            c.execute("UPDATE users SET github_id=?, github_username=? WHERE email=?", (gid, gh_login, owner[1]))
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
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET github_id=NULL, github_username=NULL WHERE email=?", (payload.get("email"),))
    conn.commit()
    conn.close()
    return JSONResponse({"message": "已解绑 GitHub"}, status_code=200)

# ============================================================
# 签到（Bearer token + 东八区日期 + 唯一约束）
# ============================================================
@app.post("/api/checkin")
async def checkin(request: Request):
    payload = get_auth_user(request)
    if not payload:
        return JSONResponse({"error": "请先登录后再签到"}, status_code=401)
    email = payload.get("email")

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    user = c.execute(
        "SELECT id, email, username, orange_balance, last_sign_in_date FROM users WHERE email=?",
        (email,),
    ).fetchone()
    if not user:
        conn.close()
        return JSONResponse({"error": "用户不存在"}, status_code=404)

    today = today_cn()
    if user[4] == today:
        sign_in_count = c.execute(
            "SELECT COUNT(*) FROM checkin_records WHERE email=? AND checkin_date=?", (email, today)
        ).fetchone()[0]
        conn.close()
        return JSONResponse(
            {"error": "今日已签到", "sign_in_count": int(sign_in_count or 0), "orange_balance": int(user[3] or 0)},
            status_code=409,
        )

    reward = 5
    new_balance = int(user[3] or 0) + reward
    try:
        c.execute("INSERT INTO checkin_records (email, checkin_date, points) VALUES (?, ?, ?)", (email, today, reward))
    except sqlite3.IntegrityError:
        conn.close()
        return JSONResponse({"error": "今日已签到"}, status_code=409)
    c.execute("UPDATE users SET orange_balance=?, last_sign_in_date=? WHERE email=?", (new_balance, today, email))
    conn.commit()
    sign_in_count = c.execute("SELECT COUNT(*) FROM checkin_records WHERE email=?", (email,)).fetchone()[0]
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
    if payload.get("role") != "admin":
        return None, "无权限"
    conn = sqlite3.connect(DATABASE)
    try:
        admin = conn.execute(
            "SELECT id, email, username, role FROM users WHERE email=?", (payload.get("email"),)
        ).fetchone()
    finally:
        conn.close()
    if not admin or admin[3] != "admin":
        return None, "无权限"
    return admin, None

@app.get("/api/admin/users")
async def admin_list_users(request: Request):
    admin, err = _admin_or_none(request)
    if err:
        return JSONResponse({"error": err}, status_code=401 if err == "未登录" else 403)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    rows = c.execute("SELECT id, email, username, orange_balance, role FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return JSONResponse({"users": [
        {"id": r[0], "email": r[1], "username": r[2], "orange_balance": int(r[3] or 0), "role": r[4] or "user",
         "is_protected": (r[1] in PROTECTED_ADMIN_EMAILS or r[2] in PROTECTED_ADMIN_USERNAMES)}
        for r in rows
    ]}, status_code=200)

# ============================================================
# 管理员：更新用户（Bearer token + 非负余额 + 保护账号）
# ============================================================
PROTECTED_ADMIN_EMAILS = {"3659793158@qq.com"}
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
    if balance < 0:
        return JSONResponse({"error": "橙子数量不能为负数"}, status_code=400)

    normalized_role = str(new_role).strip().lower()
    if normalized_role not in {"admin", "user"}:
        return JSONResponse({"error": "角色值无效"}, status_code=400)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    target = c.execute("SELECT id, email, username, orange_balance, role FROM users WHERE id=?", (user_id,)).fetchone()
    if not target:
        conn.close()
        return JSONResponse({"error": "用户不存在"}, status_code=404)

    target_email, target_username = target[1], target[2]
    if target_email in PROTECTED_ADMIN_EMAILS or target_username in PROTECTED_ADMIN_USERNAMES:
        if normalized_role != "admin":
            conn.close()
            return JSONResponse({"error": "orange 账号禁止设置为普通用户"}, status_code=403)
    if target_email == admin[1] and normalized_role != "admin":
        conn.close()
        return JSONResponse({"error": "管理员不能将自己设置为普通用户"}, status_code=403)

    c.execute("UPDATE users SET orange_balance=?, role=? WHERE id=?", (balance, normalized_role, user_id))
    c.execute(
        "INSERT INTO admin_audit_logs "
        "(admin_email, admin_username, target_user_id, target_email, target_username, "
        "old_balance, new_balance, old_role, new_role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            admin[1], admin[2], target[0], target[1], target[2],
            int(target[3] or 0), balance, target[4] or "user", normalized_role,
        ),
    )
    conn.commit()
    conn.close()
    return JSONResponse({"message": "更新成功", "id": user_id, "orange_balance": balance, "role": normalized_role}, status_code=200)

# ============================================================
# 管理员：操作日志（Bearer token + activity_logs，对齐线上）
# ============================================================
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

@app.get("/api/health")
async def health():
    return JSONResponse({"ok": True, "runtime": "local-fastapi"}, status_code=200)

init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=3000, reload=True)
