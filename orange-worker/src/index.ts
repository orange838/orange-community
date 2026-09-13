import { scrypt } from "scrypt-js";

interface Env {
  DB: D1Database;
  CF_TURNSTILE_SECRET_KEY: string;
  RESEND_API_KEY: string;
  PROTECTED_ADMIN_EMAIL: string;
  PROTECTED_ADMIN_USERNAME: string;
}

type User = {
  id: number;
  email: string;
  username: string;
  password: string;
  orange_balance: number;
  last_sign_in_date: string | null;
  role: "admin" | "user";
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });

const allowedOrigins = new Set([
  "https://cslblog.dpdns.org",
  "https://orange-community.pages.dev"
]);

const cors = (response: Response, request: Request) => {
  const headers = new Headers(response.headers);
  const origin = request.headers.get("Origin");
  if (origin && allowedOrigins.has(origin)) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Vary", "Origin");
  }
  headers.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  return new Response(response.body, { status: response.status, headers });
};

const today = () => new Date().toISOString().slice(0, 10);

const encode = (value: string) => new TextEncoder().encode(value);

const toHex = (bytes: Uint8Array) =>
  [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");

const fromHex = (value: string) =>
  new Uint8Array(value.match(/.{1,2}/g)?.map((byte) => parseInt(byte, 16)) ?? []);

const getActivityName = (path: string) => ({
  "/api/profile": "查看个人信息",
  "/api/send-code": "发送验证码",
  "/api/register": "注册账号",
  "/api/login": "登录账号",
  "/api/checkin": "签到",
  "/api/admin/users": "查看用户管理",
  "/api/admin/users/update": "修改用户信息",
  "/api/admin/logs": "查看操作日志"
}[path] ?? "访问接口");

async function recordActivity(
  db: D1Database,
  request: Request,
  response: Response,
  body: Record<string, unknown>
) {
  const url = new URL(request.url);
  if (
    request.method === "OPTIONS" ||
    !url.pathname.startsWith("/api/") ||
    url.pathname === "/api/health"
  ) return;
  const actorEmail = String(
    body.email ?? body.admin_email ?? url.searchParams.get("email") ?? ""
  ) || null;
  const actor = actorEmail ? await getUserByEmail(db, actorEmail) : null;
  await db.prepare(
    "INSERT INTO activity_logs " +
    "(actor_email, actor_username, action, action_detail, method, path, status) " +
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
  ).bind(
    actor?.email ?? actorEmail,
    actor?.username ?? null,
    getActivityName(url.pathname),
    `${request.method} ${url.pathname}`,
    request.method,
    url.pathname,
    response.status
  ).run();
}

async function hashPassword(password: string) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey("raw", encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: 600_000, hash: "SHA-256" },
    key,
    256
  );
  return `pbkdf2:sha256:600000$${toHex(salt)}$${toHex(new Uint8Array(bits))}`;
}

async function verifyPassword(stored: string, password: string) {
  if (stored.startsWith("scrypt:")) {
    const [parameters, salt, expected] = stored.split("$");
    const [, n, r, p] = parameters.split(":");
    const derived = await scrypt(encode(password), encode(salt), Number(n), Number(r), Number(p), 64);
    return toHex(derived) === expected;
  }

  if (stored.startsWith("pbkdf2:sha256:")) {
    const [parameters, saltHex, expected] = stored.split("$");
    const iterations = Number(parameters.split(":")[2]);
    const key = await crypto.subtle.importKey("raw", encode(password), "PBKDF2", false, ["deriveBits"]);
    const bits = await crypto.subtle.deriveBits(
      { name: "PBKDF2", salt: fromHex(saltHex), iterations, hash: "SHA-256" },
      key,
      256
    );
    return toHex(new Uint8Array(bits)) === expected;
  }

  return false;
}

async function verifyTurnstile(token: string | undefined, env: Env) {
  if (!token) return false;
  if (!env.CF_TURNSTILE_SECRET_KEY) return false;
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    body: new URLSearchParams({ secret: env.CF_TURNSTILE_SECRET_KEY, response: token })
  });
  const result = await response.json<{ success?: boolean }>();
  return result.success === true;
}

async function getUserByEmail(db: D1Database, email: string) {
  return db.prepare(
    "SELECT id, email, username, password, orange_balance, last_sign_in_date, role FROM users WHERE email = ?"
  ).bind(email).first<User>();
}

function isProtectedUser(user: User, env: Env) {
  return user.email === env.PROTECTED_ADMIN_EMAIL || user.username === env.PROTECTED_ADMIN_USERNAME;
}

async function handle(request: Request, env: Env) {
  if (request.method === "OPTIONS") return new Response(null, { status: 204 });
  const url = new URL(request.url);
  const body = request.method === "POST" ? await request.json<Record<string, unknown>>() : {};

  if (url.pathname === "/api/health" && request.method === "GET") {
    return json({ ok: true, runtime: "cloudflare-worker" });
  }

  if (url.pathname === "/api/profile" && request.method === "GET") {
    const email = url.searchParams.get("email");
    if (!email) return json({ error: "未登录" }, 401);
    const user = await getUserByEmail(env.DB, email);
    if (!user) return json({ error: "用户不存在" }, 404);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM checkin_records WHERE email = ?")
      .bind(email).first<{ count: number }>();
    return json({
      email: user.email,
      username: user.username,
      orange_balance: user.orange_balance ?? 0,
      last_sign_in_date: user.last_sign_in_date,
      sign_in_count: Number(count?.count ?? 0),
      has_checked_in_today: user.last_sign_in_date === today(),
      role: user.role ?? "user"
    });
  }

  if (url.pathname === "/api/send-code" && request.method === "POST") {
    const email = String(body.email ?? "");
    const type = body.type === "login" ? "登录" : "注册";
    if (!email) return json({ error: "没邮箱" }, 400);
    if (!env.RESEND_API_KEY) return json({ error: "服务器配置错误：缺少 RESEND_API_KEY" }, 500);
    const code = String(Math.floor(100000 + Math.random() * 900000));
    const expiresAt = new Date(Date.now() + 5 * 60_000).toISOString();
    await env.DB.prepare("INSERT INTO codes (email, code, expires_at) VALUES (?, ?, ?)")
      .bind(email, code, expiresAt).run();
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        from: "Orange Community <onboarding@cslblog.dpdns.org>",
        to: [email],
        subject: `Orange Community ${type}验证码`,
        html: `<p>您的${type}验证码是：<strong>${code}</strong>，有效期 5 分钟。</p>`
      })
    });
    if (!response.ok) return json({ error: "发送失败" }, 500);
    return json({ message: "已发送" });
  }

  if (url.pathname === "/api/register" && request.method === "POST") {
    if (!await verifyTurnstile(body.cf_token as string | undefined, env)) {
      return json({ error: "人机验证失败，请重试" }, 403);
    }
    const email = String(body.email ?? "");
    const username = String(body.username ?? "");
    const password = String(body.password ?? "");
    const code = String(body.code ?? "");
    if (!email || !password || !code) return json({ error: "缺参数" }, 400);
    const validCode = await env.DB.prepare(
      "SELECT id FROM codes WHERE email = ? AND code = ? AND is_used = 0 AND expires_at > ? ORDER BY id DESC LIMIT 1"
    ).bind(email, code, new Date().toISOString()).first<{ id: number }>();
    if (!validCode) return json({ error: "码不对或过期" }, 400);
    try {
      await env.DB.batch([
        env.DB.prepare("UPDATE codes SET is_used = 1 WHERE id = ?").bind(validCode.id),
        env.DB.prepare("INSERT INTO users (email, username, password) VALUES (?, ?, ?)")
          .bind(email, username, await hashPassword(password))
      ]);
    } catch {
      return json({ error: "注册失败" }, 500);
    }
    return json({ message: "注册成功" }, 201);
  }

  if (url.pathname === "/api/login" && request.method === "POST") {
    if (!await verifyTurnstile(body.cf_token as string | undefined, env)) {
      return json({ error: "人机验证失败，请重试" }, 403);
    }
    if (body.method === "code") {
      const email = String(body.email ?? "");
      const code = String(body.code ?? "");
      if (!email || !code) return json({ error: "邮箱和验证码不能为空" }, 400);
      const user = await getUserByEmail(env.DB, email);
      if (!user) return json({ error: "该邮箱未注册" }, 404);
      const validCode = await env.DB.prepare(
        "SELECT id FROM codes WHERE email = ? AND code = ? AND is_used = 0 AND expires_at > ?"
      ).bind(email, code, new Date().toISOString()).first<{ id: number }>();
      if (!validCode) return json({ error: "验证码错误或已过期" }, 400);
      await env.DB.prepare("UPDATE codes SET is_used = 1 WHERE id = ?").bind(validCode.id).run();
      return json({ message: `欢迎回来，${user.username}！`, user: {
        email: user.email,
        username: user.username,
        orange_balance: user.orange_balance ?? 0,
        role: user.role ?? "user"
      }});
    }
    const account = String(body.account ?? "");
    const password = String(body.password ?? "");
    if (!account || !password) return json({ error: "账号和密码不能为空" }, 400);
    const user = await env.DB.prepare(
      "SELECT id, email, username, password, orange_balance, last_sign_in_date, role FROM users WHERE email = ? OR username = ?"
    ).bind(account, account).first<User>();
    if (!user) return json({ error: "用户不存在" }, 401);
    if (!await verifyPassword(user.password, password)) return json({ error: "密码错误" }, 401);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM checkin_records WHERE email = ?")
      .bind(user.email).first<{ count: number }>();
    return json({
      message: `欢迎回来，${user.username}！`,
      user: {
        email: user.email,
        username: user.username,
        orange_balance: user.orange_balance ?? 0,
        sign_in_count: Number(count?.count ?? 0),
        role: user.role ?? "user"
      }
    });
  }

  if (url.pathname === "/api/checkin" && request.method === "POST") {
    const email = String(body.email ?? "");
    if (!email) return json({ error: "请先登录后再签到" }, 401);
    const user = await getUserByEmail(env.DB, email);
    if (!user) return json({ error: "用户不存在" }, 404);
    const date = today();
    if (user.last_sign_in_date === date) {
      return json({ error: "今日已签到", orange_balance: user.orange_balance ?? 0 }, 409);
    }
    const balance = Number(user.orange_balance ?? 0) + 5;
    await env.DB.batch([
      env.DB.prepare("INSERT INTO checkin_records (email, checkin_date, points) VALUES (?, ?, 5)").bind(email, date),
      env.DB.prepare("UPDATE users SET orange_balance = ?, last_sign_in_date = ? WHERE email = ?").bind(balance, date, email)
    ]);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM checkin_records WHERE email = ?")
      .bind(email).first<{ count: number }>();
    return json({ message: "签到成功", points: 5, orange_balance: balance, last_sign_in_date: date, sign_in_count: Number(count?.count ?? 0), has_checked_in_today: true });
  }

  if (url.pathname === "/api/admin/users" && request.method === "GET") {
    const email = url.searchParams.get("email");
    const admin = email ? await getUserByEmail(env.DB, email) : null;
    if (!admin || admin.role !== "admin") return json({ error: "无权限" }, 403);
    const users = await env.DB.prepare("SELECT id, email, username, orange_balance, role FROM users ORDER BY id").all();
    return json({ users: users.results });
  }

  if (url.pathname === "/api/admin/users/update" && request.method === "POST") {
    const adminEmail = String(body.admin_email ?? "");
    const admin = await getUserByEmail(env.DB, adminEmail);
    if (!admin || admin.role !== "admin") return json({ error: "无权限" }, 403);
    const target = await env.DB.prepare("SELECT id, email, username, orange_balance, role FROM users WHERE id = ?")
      .bind(Number(body.id)).first<User>();
    if (!target) return json({ error: "用户不存在" }, 404);
    const role = String(body.role ?? "").toLowerCase();
    if (!["admin", "user"].includes(role)) return json({ error: "角色值无效" }, 400);
    if ((isProtectedUser(target, env) || target.email === adminEmail) && role !== "admin") {
      return json({ error: isProtectedUser(target, env) ? "orange 账号禁止设置为普通用户" : "管理员不能将自己设置为普通用户" }, 403);
    }
    const balance = Number(body.orange_balance);
    if (!Number.isInteger(balance) || balance < 0) return json({ error: "橙子数量必须为非负整数" }, 400);
    await env.DB.batch([
      env.DB.prepare("UPDATE users SET orange_balance = ?, role = ? WHERE id = ?")
        .bind(balance, role, target.id),
      env.DB.prepare(
        "INSERT INTO admin_audit_logs " +
        "(admin_email, admin_username, target_user_id, target_email, target_username, " +
        "old_balance, new_balance, old_role, new_role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
      ).bind(
        admin.email,
        admin.username,
        target.id,
        target.email,
        target.username,
        Number(target.orange_balance ?? 0),
        balance,
        target.role ?? "user",
        role
      )
    ]);
    return json({ message: "更新成功", id: target.id, orange_balance: balance, role });
  }

  if (url.pathname === "/api/admin/logs" && request.method === "GET") {
    const email = url.searchParams.get("email");
    const admin = email ? await getUserByEmail(env.DB, email) : null;
    if (!admin || admin.role !== "admin") return json({ error: "无权限" }, 403);
    const logs = await env.DB.prepare(
      "SELECT id, actor_email, actor_username, action, action_detail, method, path, status, created_at " +
      "FROM activity_logs ORDER BY id DESC LIMIT 100"
    ).all();
    return json({ logs: logs.results });
  }

  return json({ error: "未找到接口" }, 404);
}

export default {
  async fetch(request: Request, env: Env) {
    try {
      const body = request.method === "POST"
        ? await request.clone().json<Record<string, unknown>>()
        : {};
      const response = await handle(request, env);
      await recordActivity(env.DB, request, response, body);
      return cors(response, request);
    } catch (error) {
      console.error(error);
      return cors(json({ error: "服务器内部错误" }, 500), request);
    }
  }
};
