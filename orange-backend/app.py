
import os
import random
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
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
        'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'
    )
    c.execute(
        'CREATE TABLE IF NOT EXISTS codes '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'email TEXT NOT NULL, '
        'code TEXT NOT NULL, '
        'expires_at TIMESTAMP NOT NULL, '
        'is_used INTEGER DEFAULT 0)'
    )
    conn.commit()
    conn.close()
    print("数据库已就绪")

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
        # 插入新用户
        cursor.execute("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", (email, username, password))
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
                "SELECT id, email, username, password FROM users WHERE email=? OR username=?",
                (account, account)
            )
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "用户不存在"}), 401
            if user[3] != password:
                return jsonify({"error": "密码错误"}), 401
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
            cursor.execute("SELECT id, email, username, password FROM users WHERE email=?", (email,))
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
    return jsonify({
        "message": f"欢迎回来，{user[2]}！",
        "user": {"email": user[1], "username": user[2]}
    }), 200

# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=3000)