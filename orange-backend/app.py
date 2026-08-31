
import os
import random
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import resend
import requests

# ============================================================
# 环境变量加载（请确保 orange-backend/.env 文件存在）
# .env 中需要配置以下变量：
#   SECRET_KEY=你的Flask密钥
#   CF_TURNSTILE_SECRET_KEY=你的Cloudflare Turnstile长密钥
#   RESEND_API_KEY=你的Resend邮件服务API密钥
# ============================================================
load_dotenv()

# 初始化 Flask
app = Flask(__name__)
CORS(app)  # 允许跨域

# 配置
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
CF_SECRET_KEY = os.getenv("CF_TURNSTILE_SECRET_KEY")
DATABASE = 'orange_community.db'

# Resend API Key（邮件验证码服务）
resend.api_key = os.getenv("RESEND_API_KEY", "[REDACTED_REVOKED_RESEND_KEY]")

def hash_password(password):
    return generate_password_hash(password)


def verify_password(stored_password, plain_password):
    if not stored_password:
        return False
    try:
        return check_password_hash(stored_password, plain_password)
    except (TypeError, ValueError):
        return stored_password == plain_password


def migrate_plaintext_passwords():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    rows = c.execute('SELECT id, email, password FROM users').fetchall()
    for user_id, email, password_value in rows:
        if not password_value:
            continue
        hashed_prefixes = ('scrypt:', 'pbkdf2:', 'bcrypt$', 'argon2', 'sha256:', 'md5:')
        if any(password_value.startswith(prefix) for prefix in hashed_prefixes):
            continue
        new_hash = hash_password(password_value)
        c.execute('UPDATE users SET password=? WHERE id=?', (new_hash, user_id))
    conn.commit()
    conn.close()


PROTECTED_ADMIN_EMAILS = {'3659793158@qq.com'}
PROTECTED_ADMIN_USERNAMES = {'orange'}


def is_protected_admin_user(user_record):
    if not user_record:
        return False
    email = (user_record[1] if len(user_record) > 1 else '') or ''
    username = (user_record[2] if len(user_record) > 2 else '') or ''
    return email in PROTECTED_ADMIN_EMAILS or username in PROTECTED_ADMIN_USERNAMES


# ============================================================
# 1. Cloudflare Turnstile 人机验证函数
# ============================================================
def verify_turnstile(token):
    """向 Cloudflare 发送 token 进行人机验证"""
    if not token:
        return False, "未提供验证令牌"
    if not CF_SECRET_KEY:
        return False, "服务器配置错误：缺少 CF_TURNSTILE_SECRET_KEY"

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {
        "secret": CF_SECRET_KEY,
        "response": token,
        "remoteip": request.remote_addr  # 防止重放攻击
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)
        result = resp.json()
        if result.get("success"):
            return True, "验证通过"
        else:
            return False, "人机验证失败，请重试"
    except Exception as e:
        return False, f"验证服务异常: {str(e)}"

# ============================================================
# 2. 数据库初始化
# ============================================================
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        'CREATE TABLE IF NOT EXISTS users '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'email TEXT UNIQUE NOT NULL, '
        'username TEXT NOT NULL, '
        'password TEXT NOT NULL, '
        'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, '
        'orange_balance INTEGER DEFAULT 0, '
        'last_sign_in_date TEXT, '
        'role TEXT DEFAULT "user")'
    )
    c.execute(
        'CREATE TABLE IF NOT EXISTS codes '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'email TEXT NOT NULL, '
        'code TEXT NOT NULL, '
        'expires_at TIMESTAMP NOT NULL, '
        'is_used INTEGER DEFAULT 0)'
    )
    c.execute(
        'CREATE TABLE IF NOT EXISTS checkin_records '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'email TEXT NOT NULL, '
        'checkin_date TEXT NOT NULL, '
        'points INTEGER DEFAULT 5, '
        'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'
    )

    user_cols = [row[1] for row in c.execute('PRAGMA table_info(users)').fetchall()]
    for col_name, default_value in [('orange_balance', '0'), ('last_sign_in_date', None), ('role', '"user"')]:
        if col_name not in user_cols:
            if default_value is None:
                c.execute(f'ALTER TABLE users ADD COLUMN {col_name} TEXT')
            else:
                c.execute(f'ALTER TABLE users ADD COLUMN {col_name} INTEGER DEFAULT {default_value}' if col_name == 'orange_balance' else f'ALTER TABLE users ADD COLUMN {col_name} TEXT DEFAULT {default_value}')

    conn.commit()
    conn.close()
    migrate_plaintext_passwords()
    print("数据库已就绪")


@app.route('/api/profile', methods=['GET'])
def get_profile():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "未登录"}), 401

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    user = c.execute(
        'SELECT email, username, orange_balance, last_sign_in_date, role FROM users WHERE email=?',
        (email,)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "用户不存在"}), 404

    email_value, username, balance, last_sign_in_date, role = user
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sign_in_count = c.execute(
        'SELECT COUNT(*) FROM checkin_records WHERE email=?',
        (email_value,)
    ).fetchone()[0]
    conn.close()

    return jsonify({
        "email": email_value,
        "username": username,
        "orange_balance": int(balance or 0),
        "last_sign_in_date": last_sign_in_date,
        "sign_in_count": int(sign_in_count or 0),
        "has_checked_in_today": bool(last_sign_in_date == today),
        "role": role
    }), 200


@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json or {}
    email = data.get('email')
    if not email:
        return jsonify({"error": "请先登录后再签到"}), 401

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    user = c.execute(
        'SELECT id, email, username, orange_balance, last_sign_in_date FROM users WHERE email=?',
        (email,)
    ).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "用户不存在"}), 404

    today = datetime.now().strftime('%Y-%m-%d')
    if user[4] == today:
        sign_in_count = c.execute('SELECT COUNT(*) FROM checkin_records WHERE email=? AND checkin_date=?', (email, today)).fetchone()[0]
        conn.close()
        return jsonify({"error": "今日已签到", "sign_in_count": int(sign_in_count or 0), "orange_balance": int(user[3] or 0)}), 409

    reward = 5
    new_balance = int(user[3] or 0) + reward
    c.execute('INSERT INTO checkin_records (email, checkin_date, points) VALUES (?, ?, ?)', (email, today, reward))
    c.execute('UPDATE users SET orange_balance=?, last_sign_in_date=? WHERE email=?', (new_balance, today, email))
    conn.commit()
    sign_in_count = c.execute('SELECT COUNT(*) FROM checkin_records WHERE email=?', (email,)).fetchone()[0]
    conn.close()
    return jsonify({
        "message": "签到成功",
        "points": reward,
        "orange_balance": new_balance,
        "last_sign_in_date": today,
        "sign_in_count": int(sign_in_count or 0),
        "has_checked_in_today": True
    }), 200


@app.route('/api/admin/users', methods=['GET'])
def admin_list_users():
    admin_email = request.args.get('email')
    if not admin_email:
        return jsonify({"error": "未登录"}), 401

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    admin = c.execute('SELECT id, email, username, role FROM users WHERE email=?', (admin_email,)).fetchone()
    if not admin or admin[3] != 'admin':
        conn.close()
        return jsonify({"error": "无权限"}), 403

    rows = c.execute(
        'SELECT id, email, username, orange_balance, role FROM users ORDER BY id ASC'
    ).fetchall()
    conn.close()

    return jsonify({
        "users": [{
            "id": row[0],
            "email": row[1],
            "username": row[2],
            "orange_balance": int(row[3] or 0),
            "role": row[4] or 'user'
        } for row in rows]
    }), 200


@app.route('/api/admin/users/update', methods=['POST'])
def admin_update_user():
    data = request.json or {}
    admin_email = data.get('admin_email')
    user_id = data.get('id')
    new_balance = data.get('orange_balance')
    new_role = data.get('role')

    if not admin_email:
        return jsonify({"error": "未登录"}), 401
    if user_id is None or new_balance is None or not new_role:
        return jsonify({"error": "参数不完整"}), 400

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    admin = c.execute('SELECT id, email, username, role FROM users WHERE email=?', (admin_email,)).fetchone()
    if not admin or admin[3] != 'admin':
        conn.close()
        return jsonify({"error": "无权限"}), 403

    target = c.execute('SELECT id, email, username, orange_balance, role FROM users WHERE id=?', (user_id,)).fetchone()
    if not target:
        conn.close()
        return jsonify({"error": "用户不存在"}), 404

    target_email = target[1]
    target_username = target[2]
    normalized_role = str(new_role).strip().lower()
    if normalized_role not in {'admin', 'user'}:
        conn.close()
        return jsonify({"error": "角色值无效"}), 400

    if target_email in PROTECTED_ADMIN_EMAILS or target_username in PROTECTED_ADMIN_USERNAMES:
        if normalized_role != 'admin':
            conn.close()
            return jsonify({"error": "orange 账号禁止设置为普通用户"}), 403

    if target_email == admin_email and normalized_role != 'admin':
        conn.close()
        return jsonify({"error": "管理员不能将自己设置为普通用户"}), 403

    try:
        new_balance_value = int(new_balance)
    except (TypeError, ValueError):
        conn.close()
        return jsonify({"error": "橙子数量必须为整数"}), 400

    c.execute(
        'UPDATE users SET orange_balance=?, role=? WHERE id=?',
        (new_balance_value, normalized_role, user_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "更新成功", "id": user_id, "orange_balance": new_balance_value, "role": normalized_role}), 200

# ============================================================
# 3. 发送验证码接口（支持登录/注册两种邮件模板）
# ============================================================
@app.route('/api/send-code', methods=['POST'])
def send_code():
    data = request.json
    email = data.get('email')
    # 【新增】获取前端传来的类型，默认 register
    code_type = data.get('type', 'register')

    if not email:
        return jsonify({"error": "没邮箱"}), 400

    code = str(random.randint(100000, 999999))
    expires_at = (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = sqlite3.connect(DATABASE)
        conn.execute("INSERT INTO codes (email, code, expires_at) VALUES (?, ?, ?)", (email, code, expires_at))
        conn.commit()
        conn.close()

        headers = {
            "Authorization": f"Bearer {resend.api_key}",
            "Content-Type": "application/json"
        }

        # 【修改点】根据 type 选择不同标题和正文
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

        response = requests.post(
            "https://api.resend.com/emails",
            json=payload,
            headers=headers,
            timeout=120
        )

        if response.status_code != 200:
            raise Exception(f"Resend API Error: {response.text}")

        return jsonify({"message": "已发送"}), 200

    except Exception as e:
        print(f"发送失败详情: {e}")
        return jsonify({"error": "发送失败"}), 500

# ============================================================
# 4. 注册接口（Turnstile -> 验证码校验 -> 数据库保存）
# ============================================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json

    # ===== 第一步：Turnstile 人机验证 =====
    cf_token = data.get('cf_token')
    is_human, msg = verify_turnstile(cf_token)
    if not is_human:
        return jsonify({"error": msg}), 403

    # ===== 第二步：参数校验 + 邮箱验证码校验 =====
    email = data.get('email')
    password = data.get('password')
    code = data.get('code')
    username = data.get('username')
    if not all([email, password, code]):
        return jsonify({"error": "缺参数"}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        # 校验验证码：未使用、未过期、匹配
        cursor.execute(
            "SELECT id FROM codes WHERE email=? AND code=? AND is_used=0 AND expires_at>? ORDER BY id DESC LIMIT 1",
            (email, code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )

        if not cursor.fetchone():
            return jsonify({"error": "码不对或过期"}), 400

        # 标记验证码已使用
        cursor.execute("UPDATE codes SET is_used=1 WHERE email=? AND code=?", (email, code))
        # 插入新用户，密码必须哈希存储
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", (email, username, hashed_password))
        conn.commit()
        return jsonify({"message": "注册成功"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "注册失败"}), 500
    finally:
        conn.close()

# ============================================================
# 5. 登录接口（支持密码登录 + 验证码登录两种方式）
# ============================================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json

    # Turnstile 人机验证（防止暴力破解）
    cf_token = data.get('cf_token')
    is_human, msg = verify_turnstile(cf_token)
    if not is_human:
        return jsonify({"error": msg}), 403

    # 获取登录方式，默认是密码登录
    login_method = data.get('method', 'password')
    user = None

    # ===== 方式一：密码登录（支持用户名 或 邮箱） =====
    if login_method == 'password':
        account = data.get('account')
        password = data.get('password')
        if not account or not password:
            return jsonify({"error": "账号和密码不能为空"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            # 核心：用 OR 条件同时查用户名和邮箱
            cursor.execute(
                "SELECT id, email, username, password, role, orange_balance FROM users WHERE email=? OR username=?",
                (account, account)
            )
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "用户不存在"}), 401
            if not verify_password(user[3], password):
                return jsonify({"error": "密码错误"}), 401
            if user[3] == password and not any(user[3].startswith(prefix) for prefix in ('scrypt:', 'pbkdf2:', 'bcrypt$', 'argon2', 'sha256:', 'md5:')):
                hashed_password = hash_password(password)
                cursor.execute('UPDATE users SET password=? WHERE id=?', (hashed_password, user[0]))
                conn.commit()
        finally:
            conn.close()

    # ===== 方式二：邮箱验证码登录 =====
    elif login_method == 'code':
        email = data.get('email')
        code = data.get('code')
        if not email or not code:
            return jsonify({"error": "邮箱和验证码不能为空"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            # 先查邮箱是否注册
            cursor.execute("SELECT id, email, username, password, role, orange_balance FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "该邮箱未注册"}), 404

            # 校验验证码：未使用、未过期、匹配
            cursor.execute(
                "SELECT id FROM codes WHERE email=? AND code=? AND is_used=0 AND expires_at>?",
                (email, code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            if not cursor.fetchone():
                return jsonify({"error": "验证码错误或已过期"}), 400

            # 标记验证码已使用
            cursor.execute("UPDATE codes SET is_used=1 WHERE email=? AND code=?", (email, code))
            conn.commit()
        finally:
            conn.close()

    # ===== 登录成功，返回用户信息 =====
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sign_in_count = c.execute('SELECT COUNT(*) FROM checkin_records WHERE email=?', (user[1],)).fetchone()[0]
    balance = c.execute('SELECT orange_balance FROM users WHERE email=?', (user[1],)).fetchone()[0]
    role = user[4] if len(user) > 4 else 'user'
    conn.close()

    return jsonify({
        "message": f"欢迎回来，{user[2]}！",
        "user": {
            "email": user[1],
            "username": user[2],
            "orange_balance": int(balance or 0),
            "sign_in_count": int(sign_in_count or 0),
            "role": role
        }
    }), 200

# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=3000)