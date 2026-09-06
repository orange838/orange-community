
import os
import random
import hashlib
import secrets
import json
import sqlite3
from datetime import datetime, timedelta
from io import BytesIO

# ============================================================
# 环境变量加载（请确保项目根目录 .env 文件存在）
# .env 中需要配置：
#   SECRET_KEY=你的Flask密钥
#   CF_TURNSTILE_SECRET_KEY=你的Cloudflare Turnstile长密钥
#   RESEND_API_KEY=你的Resend邮件服务API密钥
# ============================================================
from dotenv import load_dotenv
load_dotenv()

# ============================================================
# Cloudflare Workers 全局变量 - 本地开发时提供 Mock
# ============================================================
try:
    _ = Response
except NameError:
    class _MockResponse:
        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}
    Response = _MockResponse  # type: ignore

try:
    _ = fetch
except NameError:
    import aiohttp
    _cf_session = aiohttp.ClientSession()

    class _MockFetchResponse:
        def __init__(self, status, headers, body):
            self.status = status
            self._headers = dict(headers)
            self._body = body

        async def json(self):
            return json.loads(self._body)

        async def text(self):
            return self._body.decode()

    async def fetch(url, init=None):
        method = init.get("method", "GET") if init else "GET"
        req_headers = init.get("headers", {}) if init else {}
        body = init.get("body") if init else None
        async with _cf_session.request(method, url, headers=req_headers, data=body) as resp:
            resp_body = await resp.read()
            return _MockFetchResponse(resp.status, resp.headers, resp_body)

# ============================================================
# 环境变量
# ============================================================
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
CF_SECRET_KEY = os.getenv("CF_TURNSTILE_SECRET_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "[REDACTED_REVOKED_RESEND_KEY]")

# D1 binding (injected by Cloudflare Workers)
d1_binding = None

# ============================================================
# 密码哈希工具
# ============================================================
def hash_password(password):
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"pbkdf2:sha256:{salt}${pwd_hash}"


def verify_password(stored_password, plain_password):
    if not stored_password:
        return False
    try:
        if stored_password.startswith("pbkdf2:sha256:"):
            _, algo, salt_hash = stored_password.split(":", 2)
            salt, hash_val = salt_hash.split("$")
            new_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000).hex()
            return new_hash == hash_val
        # 兼容旧版 werkzeug 密码（本地调试用）
        from werkzeug.security import check_password_hash
        return check_password_hash(stored_password, plain_password)
    except (TypeError, ValueError):
        return stored_password == plain_password


# ============================================================
# 保护的管理员信息
# ============================================================
PROTECTED_ADMIN_EMAILS = {'3659793158@qq.com'}
PROTECTED_ADMIN_USERNAMES = {'orange'}


def is_protected_admin_user(user_record):
    if not user_record:
        return False
    email = (user_record[1] if len(user_record) > 1 else '') or ''
    username = (user_record[2] if len(user_record) > 2 else '') or ''
    return email in PROTECTED_ADMIN_EMAILS or username in PROTECTED_ADMIN_USERNAMES


# ============================================================
# Cloudflare Turnstile 人机验证
# ============================================================
async def verify_turnstile(token, ip=None):
    """向 Cloudflare 发送 token 进行人机验证"""
    if not token:
        return False, "未提供验证令牌"
    if not CF_SECRET_KEY:
        return False, "服务器配置错误：缺少 CF_TURNSTILE_SECRET_KEY"

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {
        "secret": CF_SECRET_KEY,
        "response": token,
    }
    if ip:
        payload["remoteip"] = ip

    try:
        resp = await fetch(url, {
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload)
        })
        result = await resp.json()
        if result.get("success"):
            return True, "验证通过"
        else:
            return False, "人机验证失败，请重试"
    except Exception as e:
        return False, f"验证服务异常: {str(e)}"


# ============================================================
# D1 数据库适配器
# ============================================================
class D1DB:
    def __init__(self, binding):
        self.binding = binding

    async def execute(self, query, params=None):
        """执行写入操作 (INSERT, UPDATE, DELETE)"""
        stmt = self.binding.prepare(query)
        if params:
            stmt = stmt.bind(*params)
        return await stmt.run()

    async def fetchone(self, query, params=None):
        """查询单条数据"""
        stmt = self.binding.prepare(query)
        if params:
            stmt = stmt.bind(*params)
        result = await stmt.first()
        return result

    async def fetchall(self, query, params=None):
        """查询多条数据"""
        stmt = self.binding.prepare(query)
        if params:
            stmt = stmt.bind(*params)
        result = await stmt.all()
        return result


# ============================================================
# 本地 SQLite 适配器（仅本地开发使用）
# ============================================================
class LocalDB:
    """实现与 D1 相同的 prepare/bind/run/first/all 接口"""
    def __init__(self, db_path="local.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    class _Stmt:
        def __init__(self, conn, query, params):
            self.conn = conn
            self.query = query
            self.params = params

        def bind(self, *params):
            return self._Stmt(self.conn, self.query, self.params + params)

        async def run(self):
            cursor = self.conn.cursor()
            cursor.execute(self.query, self.params)
            self.conn.commit()
            return self

        async def first(self):
            cursor = self.conn.cursor()
            cursor.execute(self.query, self.params)
            row = cursor.fetchone()
            if row:
                return [row[col] for col in row.keys()]
            return None

        async def all(self):
            cursor = self.conn.cursor()
            cursor.execute(self.query, self.params)
            return [[row[col] for col in row.keys()] for row in cursor.fetchall()]

    def prepare(self, query):
        return self._Stmt(self.conn, query, ())


async def get_db():
    """获取数据库连接实例"""
    if not d1_binding:
        raise RuntimeError("D1 Binding not initialized!")
    return D1DB(d1_binding)


# ============================================================
# 数据库初始化
# ============================================================
async def init_db():
    db = await get_db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            orange_balance INTEGER DEFAULT 0,
            last_sign_in_date TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS checkin_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            checkin_date TEXT NOT NULL,
            points INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 列迁移（忽略已存在的列报错）
    for col_sql in [
        "ALTER TABLE users ADD COLUMN orange_balance INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN last_sign_in_date TEXT",
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'",
    ]:
        try:
            await db.execute(col_sql)
        except Exception:
            pass

    # 迁移明文密码
    await migrate_plaintext_passwords()
    print("数据库已就绪")


async def migrate_plaintext_passwords():
    """将旧版明文密码迁移为哈希存储"""
    db = await get_db()
    rows = await db.fetchall('SELECT id, email, password FROM users')
    if not rows:
        return
    for row in rows:
        user_id, email, password_value = row
        if not password_value:
            continue
        hashed_prefixes = ('scrypt:', 'pbkdf2:', 'bcrypt$', 'argon2', 'sha256:', 'md5:')
        if any(password_value.startswith(prefix) for prefix in hashed_prefixes):
            continue
        new_hash = hash_password(password_value)
        await db.execute('UPDATE users SET password=? WHERE id=?', (new_hash, user_id))


# ============================================================
# FastAPI 应用
# ============================================================
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Orange Community API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_client_ip(request: Request) -> str | None:
    """从请求中获取客户端IP，优先使用 Cloudflare cf-connecting-ip 头"""
    ip = request.headers.get('cf-connecting-ip')
    if ip:
        return ip
    if request.client:
        return request.client.host
    return None


# --- 1. 注册 ---
@app.post("/api/register")
async def register(request: Request):
    data = await request.json()

    # 第一步：Turnstile 人机验证
    cf_token = data.get('cf_token')
    ip = _get_client_ip(request)
    is_human, msg = await verify_turnstile(cf_token, ip)
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)

    # 第二步：参数校验 + 邮箱验证码校验
    email = data.get('email')
    password = data.get('password')
    code = data.get('code')
    username = data.get('username')
    if not all([email, password, code]):
        return JSONResponse({"error": "缺参数"}, status_code=400)

    db = await get_db()
    try:
        # 校验验证码：未使用、未过期、匹配
        result = await db.fetchone(
            "SELECT id FROM codes WHERE email=? AND code=? AND is_used=0 AND expires_at>? ORDER BY id DESC LIMIT 1",
            (email, code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        if not result:
            return JSONResponse({"error": "码不对或过期"}, status_code=400)

        # 标记验证码已使用
        await db.execute("UPDATE codes SET is_used=1 WHERE email=? AND code=?", (email, code))
        # 插入新用户，密码必须哈希存储
        hashed_password = hash_password(password)
        await db.execute("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", (email, username, hashed_password))
        return JSONResponse({"message": "注册成功"}, status_code=201)
    except Exception as e:
        print(f"注册失败: {e}")
        return JSONResponse({"error": "注册失败"}, status_code=500)


# --- 2. 登录 ---
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()

    # Turnstile 人机验证（防止暴力破解）
    cf_token = data.get('cf_token')
    ip = _get_client_ip(request)
    is_human, msg = await verify_turnstile(cf_token, ip)
    if not is_human:
        return JSONResponse({"error": msg}, status_code=403)

    # 获取登录方式，默认是密码登录
    login_method = data.get('method', 'password')
    user = None

    # 方式一：密码登录（支持用户名 或 邮箱）
    if login_method == 'password':
        account = data.get('account')
        password = data.get('password')
        if not account or not password:
            return JSONResponse({"error": "账号和密码不能为空"}, status_code=400)

        db = await get_db()
        user = await db.fetchone(
            "SELECT id, email, username, password, role, orange_balance FROM users WHERE email=? OR username=?",
            (account, account)
        )
        if not user:
            return JSONResponse({"error": "用户不存在"}, status_code=401)
        if not verify_password(user[3], password):
            return JSONResponse({"error": "密码错误"}, status_code=401)
        # 迁移明文密码：只有当存储的密码等于输入的密码（即明文密码）时才迁移
        if user[3] == password and not any(user[3].startswith(prefix) for prefix in ('scrypt:', 'pbkdf2:', 'bcrypt$', 'argon2', 'sha256:', 'md5:')):
            hashed = hash_password(password)
            await db.execute('UPDATE users SET password=? WHERE id=?', (hashed, user[0]))

    # 方式二：邮箱验证码登录
    elif login_method == 'code':
        email = data.get('email')
        code = data.get('code')
        if not email or not code:
            return JSONResponse({"error": "邮箱和验证码不能为空"}, status_code=400)

        db = await get_db()
        user = await db.fetchone(
            "SELECT id, email, username, password, role, orange_balance FROM users WHERE email=?",
            (email,)
        )
        if not user:
            return JSONResponse({"error": "该邮箱未注册"}, status_code=404)

        result = await db.fetchone(
            "SELECT id FROM codes WHERE email=? AND code=? AND is_used=0 AND expires_at>?",
            (email, code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        if not result:
            return JSONResponse({"error": "验证码错误或已过期"}, status_code=400)

        # 标记验证码已使用
        await db.execute("UPDATE codes SET is_used=1 WHERE email=? AND code=?", (email, code))

    # 登录成功，返回用户信息
    db = await get_db()
    sign_in_count_result = await db.fetchone('SELECT COUNT(*) FROM checkin_records WHERE email=?', (user[1],))
    sign_in_count = sign_in_count_result[0] if sign_in_count_result else 0
    balance_result = await db.fetchone('SELECT orange_balance FROM users WHERE email=?', (user[1],))
    balance = balance_result[0] if balance_result else 0
    role = user[4] if len(user) > 4 else 'user'

    return JSONResponse({
        "message": f"欢迎回来，{user[2]}！",
        "user": {
            "email": user[1],
            "username": user[2],
            "orange_balance": int(balance or 0),
            "sign_in_count": int(sign_in_count or 0),
            "role": role
        }
    })


# --- 3. 获取个人信息 ---
@app.get("/api/profile")
async def get_profile(request: Request):
    email = request.query_params.get('email')
    if not email:
        return JSONResponse({"error": "未登录"}, status_code=401)

    db = await get_db()
    user = await db.fetchone(
        "SELECT email, username, orange_balance, last_sign_in_date, role FROM users WHERE email=?",
        (email,)
    )
    if not user:
        return JSONResponse({"error": "用户不存在"}, status_code=404)

    email_value, username, balance, last_sign_in_date, role = user
    today = datetime.now().strftime('%Y-%m-%d')
    sign_in_count_result = await db.fetchone('SELECT COUNT(*) FROM checkin_records WHERE email=?', (email_value,))
    sign_in_count = sign_in_count_result[0] if sign_in_count_result else 0

    return JSONResponse({
        "email": email_value,
        "username": username,
        "orange_balance": int(balance or 0),
        "last_sign_in_date": last_sign_in_date,
        "sign_in_count": int(sign_in_count or 0),
        "has_checked_in_today": bool(last_sign_in_date == today),
        "role": role
    })


# --- 4. 签到 ---
@app.post("/api/checkin")
async def checkin(request: Request):
    data = await request.json()
    email = data.get('email')
    if not email:
        return JSONResponse({"error": "请先登录后再签到"}, status_code=401)

    db = await get_db()
    user = await db.fetchone(
        "SELECT id, email, username, orange_balance, last_sign_in_date FROM users WHERE email=?",
        (email,)
    )
    if not user:
        return JSONResponse({"error": "用户不存在"}, status_code=404)

    today = datetime.now().strftime('%Y-%m-%d')
    if user[4] == today:
        sign_in_count_result = await db.fetchone('SELECT COUNT(*) FROM checkin_records WHERE email=? AND checkin_date=?', (email, today))
        sign_in_count = sign_in_count_result[0] if sign_in_count_result else 0
        return JSONResponse({"error": "今日已签到", "sign_in_count": int(sign_in_count or 0), "orange_balance": int(user[3] or 0)}, status_code=409)

    reward = 5
    new_balance = int(user[3] or 0) + reward
    await db.execute('INSERT INTO checkin_records (email, checkin_date, points) VALUES (?, ?, ?)', (email, today, reward))
    await db.execute('UPDATE users SET orange_balance=?, last_sign_in_date=? WHERE email=?', (new_balance, today, email))

    sign_in_count_result = await db.fetchone('SELECT COUNT(*) FROM checkin_records WHERE email=?', (email,))
    sign_in_count = sign_in_count_result[0] if sign_in_count_result else 0

    return JSONResponse({
        "message": "签到成功",
        "points": reward,
        "orange_balance": new_balance,
        "last_sign_in_date": today,
        "sign_in_count": int(sign_in_count or 0),
        "has_checked_in_today": True
    })


# --- 5. 管理员列表用户 ---
@app.get("/api/admin/users")
async def admin_list_users(request: Request):
    admin_email = request.query_params.get('email')
    if not admin_email:
        return JSONResponse({"error": "未登录"}, status_code=401)

    db = await get_db()
    admin = await db.fetchone('SELECT id, email, username, role FROM users WHERE email=?', (admin_email,))
    if not admin or admin[3] != 'admin':
        return JSONResponse({"error": "无权限"}, status_code=403)

    rows = await db.fetchall('SELECT id, email, username, orange_balance, role FROM users ORDER BY id ASC')

    return JSONResponse({
        "users": [{
            "id": row[0],
            "email": row[1],
            "username": row[2],
            "orange_balance": int(row[3] or 0),
            "role": row[4] or 'user'
        } for row in rows]
    })


# --- 6. 管理员更新用户 ---
@app.post("/api/admin/users/update")
async def admin_update_user(request: Request):
    data = await request.json()
    admin_email = data.get('admin_email')
    user_id = data.get('id')
    new_balance = data.get('orange_balance')
    new_role = data.get('role')

    if not admin_email:
        return JSONResponse({"error": "未登录"}, status_code=401)
    if user_id is None or new_balance is None or not new_role:
        return JSONResponse({"error": "参数不完整"}, status_code=400)

    db = await get_db()
    admin = await db.fetchone('SELECT id, email, username, role FROM users WHERE email=?', (admin_email,))
    if not admin or admin[3] != 'admin':
        return JSONResponse({"error": "无权限"}, status_code=403)

    target = await db.fetchone('SELECT id, email, username, orange_balance, role FROM users WHERE id=?', (user_id,))
    if not target:
        return JSONResponse({"error": "用户不存在"}, status_code=404)

    target_email = target[1]
    target_username = target[2]
    normalized_role = str(new_role).strip().lower()
    if normalized_role not in {'admin', 'user'}:
        return JSONResponse({"error": "角色值无效"}, status_code=400)

    if target_email in PROTECTED_ADMIN_EMAILS or target_username in PROTECTED_ADMIN_USERNAMES:
        if normalized_role != 'admin':
            return JSONResponse({"error": "orange 账号禁止设置为普通用户"}, status_code=403)

    if target_email == admin_email and normalized_role != 'admin':
        return JSONResponse({"error": "管理员不能将自己设置为普通用户"}, status_code=403)

    try:
        new_balance_value = int(new_balance)
    except (TypeError, ValueError):
        return JSONResponse({"error": "橙子数量必须为整数"}, status_code=400)

    await db.execute('UPDATE users SET orange_balance=?, role=? WHERE id=?', (new_balance_value, normalized_role, user_id))

    return JSONResponse({"message": "更新成功", "id": user_id, "orange_balance": new_balance_value, "role": normalized_role})


# --- 7. 发送验证码 ---
@app.post("/api/send-code")
async def send_code(request: Request):
    data = await request.json()
    email = data.get('email')
    # 新增：获取前端传来的类型，默认 register
    code_type = data.get('type', 'register')

    if not email:
        return JSONResponse({"error": "没邮箱"}, status_code=400)

    code = str(random.randint(100000, 999999))
    expires_at = (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')

    try:
        db = await get_db()
        await db.execute("INSERT INTO codes (email, code, expires_at) VALUES (?, ?, ?)", (email, code, expires_at))

        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }

        # 根据 type 选择不同标题和正文
        if code_type == 'login':
            subject = "Orange Community 登录验证码"
            html = f"""
            <div style="font-family: 'Microsoft YaHei', Arial, sans-serif; padding: 20px; background-color: #f9f9f9;">
                <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h2 style="color: #ff9900; text-align: center;">欢迎回来！</h2>
                    <p style="color: #333; font-size: 16px;">您好，您正在进行<b>登录</b>操作，您的验证码是：</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <span style="font-size: 36px; font-weight: bold; color: #ff9900; letter-spacing: 5px; background: #fff8e6; padding: 10px 20px; border-radius: 8px;">{code}</span>
                    </div>
                    <p style="color: #666; font-size: 14px;">验证码有效期为 <strong>5分钟</strong>，请勿泄露给他人。</p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px;">如果您未请求此验证码，请忽略此邮件。</p>
                </div>
            </div>
            """
        else:
            # 注册模板（保持原样）
            subject = "Orange Community 注册验证码"
            html = f"""
            <div style="font-family: 'Microsoft YaHei', Arial, sans-serif; padding: 20px; background-color: #f9f9f9;">
                <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h2 style="color: #ff9900; text-align: center;">欢迎加入橙子社区！</h2>
                    <p style="color: #333; font-size: 16px;">您好，您正在进行<b>注册</b>操作，您的验证码是：</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <span style="font-size: 36px; font-weight: bold; color: #ff9900; letter-spacing: 5px; background: #fff8e6; padding: 10px 20px; border-radius: 8px;">{code}</span>
                    </div>
                    <p style="color: #666; font-size: 14px;">验证码有效期为 <strong>5分钟</strong>，请勿泄露给他人。</p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px;">如果您未请求此验证码，请忽略此邮件。</p>
                </div>
            </div>
            """

        payload = {
            "from": "Orange Community <onboarding@cslblog.dpdns.org>",
            "to": [email],
            "subject": subject,
            "html": html
        }

        resp = await fetch("https://api.resend.com/emails", {
            "method": "POST",
            "headers": headers,
            "body": json.dumps(payload)
        })

        if resp.status != 200:
            error_text = await resp.text()
            raise Exception(f"Resend API Error: {error_text}")

        return JSONResponse({"message": "已发送"}, status_code=200)

    except Exception as e:
        print(f"发送失败详情: {e}")
        return JSONResponse({"error": "发送失败"}, status_code=500)


# ============================================================
# Cloudflare Workers ASGI 入口
# ============================================================
_db_initialized = False


async def on_fetch(request, env):
    global d1_binding, _db_initialized
    # 注入 D1 绑定
    d1_binding = env.DB

    # 首次请求时初始化数据库表
    if not _db_initialized:
        try:
            await init_db()
            _db_initialized = True
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            return Response(
                body=json.dumps({"error": "数据库初始化失败"}),
                status=500,
                headers={"Content-Type": "application/json"}
            )

    # 转换 Cloudflare Request 为 ASGI scope
    headers = dict(request.headers)
    body = await request.text()

    scope = {
        "type": "http",
        "method": request.method,
        "path": request.url.pathname,
        "query_string": request.url.search.encode(),
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        "server": ("localhost", 80),
    }

    receive = lambda: {"type": "http.request", "body": body.encode()}

    response_body = BytesIO()
    response_headers = []
    response_status = 200

    async def send(message):
        nonlocal response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = message["status"]
            response_headers = message["headers"]
        elif message["type"] == "http.response.body":
            response_body.write(message.get("body", b""))

    await app(scope, receive, send)

    # 转换 ASGI Response 为 Cloudflare Response
    resp_headers = {k.decode(): v.decode() for k, v in response_headers}
    return Response(
        body=response_body.getvalue(),
        status=response_status,
        headers=resp_headers
    )


# ==========================================
# 本地开发启动入口
# ==========================================
if __name__ == "__main__":
    import asyncio
    import uvicorn
    
    # === 本地开发配置 ===
    print("=== 橙子社区 - 本地开发模式 ===")
    
    # 【修正1】端口改回 3000
    PORT = 3000 
    
    # 【修正2】数据库文件名改回 orange_community.db (截图里看到的)
    DB_FILE = "orange_community.db"

    print(f"服务地址: http://localhost:{PORT}")
    print(f"API 文档: http://localhost:{PORT}/docs")
    print(f"数据库文件: {DB_FILE}")
    print("按 Ctrl+C 停止服务")
    print("=" * 40)
    
    # 设置本地数据库适配器
    global db_binding
    db_binding = LocalDB(DB_FILE) 
    
    # 初始化数据库表结构 (如果表已存在则跳过，不会删数据)
    async def startup():
        await init_db() 
        
    asyncio.run(startup())
    
    # 启动本地开发服务器
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info", reload=False)