import { scrypt } from "scrypt-js";

interface Env {
  DB: D1Database;
  CF_TURNSTILE_SECRET_KEY: string;
  RESEND_API_KEY: string;
  PROTECTED_ADMIN_EMAIL: string;
  PROTECTED_ADMIN_USERNAME: string;
  GITHUB_CLIENT_ID: string;
  GITHUB_CLIENT_SECRET: string;
  CPOAUTH_CLIENT_ID: string;
  CPOAUTH_CLIENT_SECRET: string;
  // JWT 签名密钥（务必配置一个随机长字符串，与本地 backend 的 SECRET_KEY 保持一致）
  SECRET_KEY: string;
}

type User = {
  id: number;
  email: string;
  username: string;
  password: string;
  orange_balance: number;
  last_sign_in_date: string | null;
  role: "admin" | "user";
  github_id?: string | null;
  github_username?: string | null;
  cpoauth_id?: string | null;
  cpoauth_username?: string | null;
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });

const allowedOrigins = new Set([
  "https://cslblog.dpdns.org",
  "https://www.cslblog.dpdns.org",
  "https://orange-community.pages.dev"
]);

const allowedTurnstileHostnames = new Set([
  "cslblog.dpdns.org",
  "www.cslblog.dpdns.org",
  "orange-community.pages.dev"
]);

const cors = (response: Response, request: Request) => {
  const headers = new Headers(response.headers);
  const origin = request.headers.get("Origin");
  if (origin && allowedOrigins.has(origin)) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Vary", "Origin");
  }
  headers.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization");
  return new Response(response.body, { status: response.status, headers });
};

// 签到/日期统一按东八区计算（避免 UTC 日期错位），与本地 backend 对齐
const todayCN = () => new Date(Date.now() + 8 * 3600_000).toISOString().slice(0, 10);

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

const roleLabel = (role: string) => role === "admin" ? "管理员" : "普通用户";

const verificationEmailHtml = (type: string, code: string) => `
<!doctype html>
<html lang="zh-CN">
  <body style="margin:0;background:#f4f7fb;color:#172033;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">
      Orange Community ${type}验证码：${code}，有效期 5 分钟。
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f7fb;padding:32px 12px;">
      <tr><td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 8px 28px rgba(31,55,88,.10);">
          <tr>
            <td style="padding:28px 32px;background:linear-gradient(135deg,#ff9f43,#f07832);color:#ffffff;">
              <div style="font-size:13px;letter-spacing:2px;opacity:.9;">ORANGE COMMUNITY</div>
              <div style="font-size:26px;font-weight:700;margin-top:8px;">${type}验证码</div>
            </td>
          </tr>
          <tr>
            <td style="padding:34px 32px 24px;">
              <p style="margin:0;font-size:16px;line-height:1.8;">您好，您正在进行 Orange Community ${type}操作。</p>
              <p style="margin:24px 0 10px;color:#64748b;font-size:14px;">您的验证码是</p>
              <div style="padding:18px 12px;text-align:center;background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;color:#ea580c;font-size:36px;font-weight:700;letter-spacing:10px;">${code}</div>
              <p style="margin:18px 0 0;color:#64748b;font-size:14px;line-height:1.8;">验证码有效期为 <strong style="color:#172033;">5 分钟</strong>，请勿将验证码透露给他人。</p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px 28px;border-top:1px solid #eef2f7;color:#94a3b8;font-size:12px;line-height:1.8;">
              如果您没有请求此验证码，请忽略这封邮件。<br>
              这是一封系统邮件，请勿直接回复。
            </td>
          </tr>
        </table>
        <p style="margin:18px 0 0;color:#94a3b8;font-size:12px;">© Orange Community</p>
      </td></tr>
    </table>
  </body>
</html>`;

// ============================================================
// 常量
// ============================================================
const CODE_TTL_MS = 5 * 60_000;          // 验证码 5 分钟有效
const SEND_CODE_COOLDOWN_MS = 60_000;    // 同一邮箱 60 秒内仅可发送一次
const CODE_MAX_ATTEMPTS = 5;             // 验证码最多尝试 5 次
const TOKEN_TTL_HOURS = 24 * 7;          // token 7 天有效
const GITHUB_REDIRECT_URI = "https://api.cslblog.dpdns.org/api/auth/github/callback";
const CPOAUTH_REDIRECT_URI = "https://api.cslblog.dpdns.org/api/auth/cpoauth/callback";
const CPOAUTH_AUTHORIZE_URL = "https://www.cpoauth.com/oauth/authorize";

// ============================================================
// JWT（HS256，无状态），与本地 backend 算法一致
// ============================================================
function b64url(bytes: Uint8Array) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlToBytes(s: string) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const bin = atob(s);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

async function hmacSign(secret: string, data: string) {
  const key = await crypto.subtle.importKey(
    "raw", encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, encode(data)));
}

async function createToken(secret: string, email: string, username: string, role: string, ttlHours = TOKEN_TTL_HOURS) {
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(encode(JSON.stringify({ alg: "HS256", typ: "JWT" })));
  const payload = b64url(encode(JSON.stringify({
    email, username, role, iat: now, exp: now + ttlHours * 3600
  })));
  const signingInput = `${header}.${payload}`;
  const sig = b64url(await hmacSign(secret, signingInput));
  return `${signingInput}.${sig}`;
}

async function verifyToken(secret: string, token: string) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const [header, payload, sig] = parts;
    const signingInput = `${header}.${payload}`;
    const expected = b64url(await hmacSign(secret, signingInput));
    if (expected !== sig) return null;
    const parsed = JSON.parse(new TextDecoder().decode(b64urlToBytes(payload))) as {
      email: string; username: string; role: string; exp: number;
    };
    if (parsed.exp < Math.floor(Date.now() / 1000)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function getAuth(request: Request, env: Env) {
  const auth = request.headers.get("Authorization") ?? "";
  if (!auth.startsWith("Bearer ")) return null;
  return verifyToken(env.SECRET_KEY, auth.slice(7).trim());
}

// ============================================================
// GitHub OAuth：签名 state + 换取 token + 获取用户信息
// ============================================================
async function githubState(secret: string, payload: { mode: string; bindEmail?: string }) {
  const exp = Math.floor(Date.now() / 1000) + 600; // 10 分钟内有效
  const data = b64url(encode(JSON.stringify({ ...payload, exp })));
  const sig = b64url(await hmacSign(secret, data));
  return `${data}.${sig}`;
}

async function verifyGithubState(secret: string, state: string) {
  try {
    const parts = state.split(".");
    if (parts.length !== 2) return null;
    const expected = b64url(await hmacSign(secret, parts[0]));
    if (expected !== parts[1]) return null;
    const parsed = JSON.parse(new TextDecoder().decode(b64urlToBytes(parts[0]))) as {
      mode: string; bindEmail?: string; exp: number;
    };
    if (parsed.exp < Math.floor(Date.now() / 1000)) return null;
    return parsed;
  } catch {
    return null;
  }
}

async function githubExchangeCode(clientId: string, clientSecret: string, code: string, redirectUri: string) {
  const res = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, code, redirect_uri: redirectUri })
  });
  const data = (await res.json()) as { access_token?: string; error?: string };
  if (!data.access_token) throw new Error(data.error ?? "github no access_token");
  return data.access_token;
}

async function githubUser(accessToken: string) {
  const res = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "orange-community"
    }
  });
  const u = (await res.json()) as { id: number; login: string; email?: string | null };
  return u;
}

async function cpoauthExchangeCode(clientId: string, clientSecret: string, code: string, redirectUri: string) {
  const res = await fetch("https://www.cpoauth.com/api/oauth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ grant_type: "authorization_code", code, redirect_uri: redirectUri, client_id: clientId, client_secret: clientSecret })
  });
  const data = (await res.json()) as { access_token?: string; error?: string };
  if (!data.access_token) throw new Error(data.error ?? "cpoauth no access_token");
  return data.access_token;
}

async function cpoauthUser(accessToken: string) {
  const res = await fetch("https://www.cpoauth.com/api/oauth/userinfo", {
    headers: { Authorization: `Bearer ${accessToken}`, Accept: "application/json" }
  });
  const u = (await res.json()) as { sub?: string; username?: string; display_name?: string };
  return u;
}

// ============================================================
// 密码哈希：与本地 backend 一致 pbkdf2:sha256:600000$saltHex$keyHex
// ============================================================
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

// ============================================================
// Turnstile
// ============================================================
async function verifyTurnstile(
  token: string | undefined,
  expectedAction: "login" | "register",
  request: Request,
  env: Env,
  db: D1Database
) {
  const logResult = async (passed: boolean, hostname: string | null = null) => {
    await db.prepare(
      "INSERT INTO turnstile_verification_logs (action, passed, hostname) VALUES (?, ?, ?)"
    ).bind(expectedAction, passed ? 1 : 0, hostname).run();
    return passed;
  };

  if (!token || token.length > 2048 || !env.CF_TURNSTILE_SECRET_KEY) {
    return logResult(false);
  }
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ secret: env.CF_TURNSTILE_SECRET_KEY, response: token })
  });
  if (!response.ok) return logResult(false);
  const result = await response.json<{
    success?: boolean;
    action?: string;
    hostname?: string;
  }>();
  const origin = request.headers.get("Origin");
  const expectedHostname = origin ? new URL(origin).hostname : "";
  const passed = result.success === true
    && result.action === expectedAction
    && allowedTurnstileHostnames.has(result.hostname ?? "")
    && result.hostname === expectedHostname;
  return logResult(passed, result.hostname ?? null);
}

// ============================================================
// 用户 / 验证码 / 活动日志
// ============================================================
async function getUserByEmail(db: D1Database, email: string) {
  return db.prepare(
    "SELECT id, email, username, password, orange_balance, last_sign_in_date, role, github_id, github_username, cpoauth_id, cpoauth_username FROM users WHERE email = ?"
  ).bind(email).first<User>();
}

async function getUserByIdentifier(db: D1Database, identifier: string) {
  return db.prepare(
    "SELECT id, email, username, password, orange_balance, last_sign_in_date, role " +
    "FROM users WHERE email = ? OR username = ?"
  ).bind(identifier, identifier).first<User>();
}

function isProtectedUser(user: { email: string; username: string }, env: Env) {
  return user.email === env.PROTECTED_ADMIN_EMAIL || user.username === env.PROTECTED_ADMIN_USERNAME;
}

async function validateCode(db: D1Database, email: string, code: string) {
  const row = await db.prepare(
    "SELECT id, attempts FROM codes WHERE email = ? AND code = ? AND is_used = 0 AND expires_at > ? " +
    "ORDER BY id DESC LIMIT 1"
  ).bind(email, code, new Date().toISOString()).first<{ id: number; attempts: number }>();
  if (!row) {
    await db.prepare(
      "UPDATE codes SET attempts = attempts + 1 WHERE email = ? AND code = ? AND is_used = 0"
    ).bind(email, code).run();
    return null;
  }
  if ((row.attempts ?? 0) >= CODE_MAX_ATTEMPTS) return null;
  return row;
}

async function recordActivity(
  db: D1Database,
  request: Request,
  response: Response,
  body: Record<string, unknown>,
  env: Env
) {
  const url = new URL(request.url);
  if (
    request.method === "OPTIONS" ||
    !url.pathname.startsWith("/api/") ||
    url.pathname === "/api/health"
  ) return;

  const tokenPayload = getAuth(request, env) as { email: string } | null;
  const actorIdentifier = String(
    tokenPayload?.email
    ?? body.email ?? body.admin_email ?? body.account ?? url.searchParams.get("email") ?? ""
  ) || null;
  const actor = actorIdentifier ? await getUserByIdentifier(db, actorIdentifier) : null;
  let actionDetail = `${request.method} ${url.pathname}`;
  if (url.pathname === "/api/login") {
    actionDetail = body.method === "code" ? "使用邮箱验证码登录" : "使用账号密码登录";
  } else if (url.pathname === "/api/send-code") {
    actionDetail = body.type === "login" ? "发送登录验证码" : "发送注册验证码";
  } else if (url.pathname === "/api/register") {
    actionDetail = `注册账号 ${String(body.username ?? body.email ?? "新用户")}`;
  } else if (url.pathname === "/api/checkin") {
    actionDetail = response.status === 200 ? "签到成功，获得 5 个橙子" : "尝试签到";
  } else if (url.pathname === "/api/profile") {
    actionDetail = "查看个人信息和签到数据";
  } else if (url.pathname === "/api/admin/users") {
    actionDetail = "查看用户列表";
  } else if (url.pathname === "/api/admin/logs") {
    actionDetail = "查看最近 100 条操作日志";
  } else if (url.pathname === "/api/admin/users/update") {
    const targetId = Number(body.id);
    const audit = Number.isInteger(targetId)
      ? await db.prepare(
        "SELECT old_balance, new_balance, old_role, new_role, target_username " +
        "FROM admin_audit_logs WHERE admin_email = ? AND target_user_id = ? " +
        "ORDER BY id DESC LIMIT 1"
      ).bind(actor?.email ?? actorIdentifier, targetId).first<{
        old_balance: number;
        new_balance: number;
        old_role: string;
        new_role: string;
        target_username: string | null;
      }>()
      : null;
    actionDetail = audit
      ? `修改用户 ${audit.target_username ?? targetId}：橙子数量 ${audit.old_balance} → ${audit.new_balance}，角色 ${roleLabel(audit.old_role)} → ${roleLabel(audit.new_role)}`
      : `提交用户修改：橙子数量 ${String(body.orange_balance ?? "未提供")}，角色 ${roleLabel(String(body.role ?? ""))}`;
  }
  await db.prepare(
    "INSERT INTO activity_logs " +
    "(actor_email, actor_username, action, action_detail, method, path, status) " +
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
  ).bind(
    actor?.email ?? actorIdentifier,
    actor?.username ?? null,
    getActivityName(url.pathname),
    actionDetail,
    request.method,
    url.pathname,
    response.status
  ).run();
}

// ============================================================
// 路由
// ============================================================
async function handle(request: Request, env: Env) {
  if (request.method === "OPTIONS") return new Response(null, { status: 204 });
  const url = new URL(request.url);
  const body = request.method === "POST"
    ? await request.json<Record<string, unknown>>().catch(() => ({}) as Record<string, unknown>)
    : {};

  if (url.pathname === "/api/health" && request.method === "GET") {
    return json({ ok: true, runtime: "cloudflare-worker" });
  }

  // -------- profile（Bearer token）--------
  if (url.pathname === "/api/profile" && request.method === "GET") {
    const auth = await getAuth(request, env);
    if (!auth) return json({ error: "未登录" }, 401);
    const user = await getUserByEmail(env.DB, auth.email);
    if (!user) return json({ error: "用户不存在" }, 404);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM checkin_records WHERE email = ?")
      .bind(user.email).first<{ count: number }>();
    return json({
      email: user.email,
      username: user.username,
      orange_balance: user.orange_balance ?? 0,
      last_sign_in_date: user.last_sign_in_date,
      sign_in_count: Number(count?.count ?? 0),
      has_checked_in_today: user.last_sign_in_date === todayCN(),
      role: user.role ?? "user",
      github_username: user.github_username ?? null,
      cpoauth_username: user.cpoauth_username ?? null
    });
  }

  // -------- GitHub OAuth --------
  if (url.pathname === "/api/auth/github" && request.method === "GET") {
    if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) {
      return json({ error: "GitHub 登录未配置" }, 500);
    }
    const mode = url.searchParams.get("mode") === "bind" ? "bind" : "login";
    if (mode === "bind") {
      // 绑定必须已登录；绑定目标固定为当前登录邮箱，避免被注入到其他账号
      const auth = await getAuth(request, env);
      if (!auth) return json({ error: "未登录" }, 401);
      const state = await githubState(env.SECRET_KEY, { mode, bindEmail: auth.email });
      const authorizeUrl =
        `https://github.com/login/oauth/authorize` +
        `?client_id=${encodeURIComponent(env.GITHUB_CLIENT_ID)}` +
        `&redirect_uri=${encodeURIComponent(GITHUB_REDIRECT_URI)}` +
        `&scope=${encodeURIComponent("read:user user:email")}` +
        `&state=${state}`;
      return json({ authorize_url: authorizeUrl });
    }
    const state = await githubState(env.SECRET_KEY, { mode: "login", bindEmail: "" });
    const authorizeUrl =
      `https://github.com/login/oauth/authorize` +
      `?client_id=${encodeURIComponent(env.GITHUB_CLIENT_ID)}` +
      `&redirect_uri=${encodeURIComponent(GITHUB_REDIRECT_URI)}` +
      `&scope=${encodeURIComponent("read:user user:email")}` +
      `&state=${state}`;
    return new Response(null, { status: 302, headers: { Location: authorizeUrl } });
  }

  if (url.pathname === "/api/auth/github/callback" && request.method === "GET") {
    const frontBase = "https://cslblog.dpdns.org";
    const redirect = (hash: string) =>
      new Response(null, { status: 302, headers: { Location: `${frontBase}/#${hash}` } });
    const code = url.searchParams.get("code") ?? "";
    const state = url.searchParams.get("state") ?? "";
    if (!code || !state) return redirect("/oauth-callback?error=missing_params");
    const parsed = await verifyGithubState(env.SECRET_KEY, state);
    if (!parsed) return redirect("/oauth-callback?error=invalid_state");
    if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) return redirect("/oauth-callback?error=not_configured");
    try {
      const accessToken = await githubExchangeCode(
        env.GITHUB_CLIENT_ID, env.GITHUB_CLIENT_SECRET, code, GITHUB_REDIRECT_URI
      );
      const gh = await githubUser(accessToken);
      const gid = String(gh.id);
      const user = await env.DB.prepare("SELECT * FROM users WHERE github_id = ?").bind(gid).first<User>();
      const successRedirect = async (u: User, ghName: string) => {
        const token = await createToken(env.SECRET_KEY, u.email, u.username, u.role ?? "user");
        const userJson = encodeURIComponent(JSON.stringify({
          email: u.email,
          username: u.username,
          orange_balance: u.orange_balance ?? 0,
          role: u.role ?? "user",
          github_username: ghName
        }));
        return redirect(`/oauth-callback?token=${encodeURIComponent(token)}&user=${userJson}`);
      };
      if (user) {
        // 已绑定该 GitHub → 直接登录
        return await successRedirect(user, gh.login);
      }
      if (parsed.mode === "bind") {
        // 未绑定但发起的是绑定 → 绑定到当前登录邮箱
        const owner = await getUserByEmail(env.DB, parsed.bindEmail ?? "");
        if (!owner) return redirect("/oauth-callback?error=bind_email_not_found");
        await env.DB.prepare("UPDATE users SET github_id = ?, github_username = ? WHERE email = ?")
          .bind(gid, gh.login, owner.email).run();
        return await successRedirect(owner, gh.login);
      }
      // 未绑定且是登录 → 引导先注册/绑定
      return redirect("/oauth-callback?error=unbound&src=github");
    } catch (e) {
      console.error(e);
      return redirect("/oauth-callback?error=github_error");
    }
  }

  if (url.pathname === "/api/auth/github/unbind" && request.method === "POST") {
    const auth = await getAuth(request, env);
    if (!auth) return json({ error: "未登录" }, 401);
    await env.DB.prepare("UPDATE users SET github_id = NULL, github_username = NULL WHERE email = ?")
      .bind(auth.email).run();
    return json({ message: "已解绑 GitHub" });
  }

  // -------- CP OAuth --------
  if (url.pathname === "/api/auth/cpoauth" && request.method === "GET") {
    if (!env.CPOAUTH_CLIENT_ID || !env.CPOAUTH_CLIENT_SECRET) {
      return json({ error: "CP OAuth 登录未配置" }, 500);
    }
    const mode = url.searchParams.get("mode") === "bind" ? "bind" : "login";
    const buildAuthUrl = (state: string) =>
      `${CPOAUTH_AUTHORIZE_URL}?response_type=code` +
      `&client_id=${encodeURIComponent(env.CPOAUTH_CLIENT_ID)}` +
      `&redirect_uri=${encodeURIComponent(CPOAUTH_REDIRECT_URI)}` +
      `&scope=${encodeURIComponent("openid profile")}` +
      `&state=${state}`;
    if (mode === "bind") {
      const auth = await getAuth(request, env);
      if (!auth) return json({ error: "未登录" }, 401);
      const state = await githubState(env.SECRET_KEY, { mode, bindEmail: auth.email });
      return json({ authorize_url: buildAuthUrl(state) });
    }
    const state = await githubState(env.SECRET_KEY, { mode: "login", bindEmail: "" });
    return new Response(null, { status: 302, headers: { Location: buildAuthUrl(state) } });
  }

  if (url.pathname === "/api/auth/cpoauth/callback" && request.method === "GET") {
    const frontBase = "https://cslblog.dpdns.org";
    const redirect = (hash: string) =>
      new Response(null, { status: 302, headers: { Location: `${frontBase}/#${hash}` } });
    const code = url.searchParams.get("code") ?? "";
    const state = url.searchParams.get("state") ?? "";
    if (!code || !state) return redirect("/oauth-callback?error=missing_params");
    const parsed = await verifyGithubState(env.SECRET_KEY, state);
    if (!parsed) return redirect("/oauth-callback?error=invalid_state");
    if (!env.CPOAUTH_CLIENT_ID || !env.CPOAUTH_CLIENT_SECRET) return redirect("/oauth-callback?error=not_configured");
    try {
      const accessToken = await cpoauthExchangeCode(
        env.CPOAUTH_CLIENT_ID, env.CPOAUTH_CLIENT_SECRET, code, CPOAUTH_REDIRECT_URI
      );
      const cp = await cpoauthUser(accessToken);
      const cid = cp.sub ?? cp.username ?? "";
      if (!cid) return redirect("/oauth-callback?error=github_error");
      const cpName = cp.username ?? cp.display_name ?? cid;
      const user = await env.DB.prepare("SELECT * FROM users WHERE cpoauth_id = ?").bind(cid).first<User>();
      const successRedirect = async (u: User, cpName2: string) => {
        const token = await createToken(env.SECRET_KEY, u.email, u.username, u.role ?? "user");
        const userJson = encodeURIComponent(JSON.stringify({
          email: u.email,
          username: u.username,
          orange_balance: u.orange_balance ?? 0,
          role: u.role ?? "user",
          github_username: u.github_username ?? null,
          cpoauth_username: cpName2
        }));
        return redirect(`/oauth-callback?token=${encodeURIComponent(token)}&user=${userJson}`);
      };
      if (user) {
        return await successRedirect(user, cpName);
      }
      if (parsed.mode === "bind") {
        const owner = await getUserByEmail(env.DB, parsed.bindEmail ?? "");
        if (!owner) return redirect("/oauth-callback?error=bind_email_not_found");
        await env.DB.prepare("UPDATE users SET cpoauth_id = ?, cpoauth_username = ? WHERE email = ?")
          .bind(cid, cpName, owner.email).run();
        return await successRedirect(owner, cpName);
      }
      return redirect("/oauth-callback?error=unbound&src=cpoauth");
    } catch (e) {
      console.error(e);
      return redirect("/oauth-callback?error=github_error");
    }
  }

  if (url.pathname === "/api/auth/cpoauth/unbind" && request.method === "POST") {
    const auth = await getAuth(request, env);
    if (!auth) return json({ error: "未登录" }, 401);
    await env.DB.prepare("UPDATE users SET cpoauth_id = NULL, cpoauth_username = NULL WHERE email = ?")
      .bind(auth.email).run();
    return json({ message: "已解绑 CP OAuth" });
  }

  // -------- send-code（带发送冷却）--------
  if (url.pathname === "/api/send-code" && request.method === "POST") {
    const email = String(body.email ?? "");
    const type = body.type === "login" ? "登录" : "注册";
    if (!email) return json({ error: "没邮箱" }, 400);
    if (!env.RESEND_API_KEY) return json({ error: "服务器配置错误：缺少 RESEND_API_KEY" }, 500);

    // 发送冷却：同一邮箱 60 秒内仅可发送一次
    const last = await env.DB.prepare(
      "SELECT created_at FROM codes WHERE email = ? ORDER BY id DESC LIMIT 1"
    ).bind(email).first<{ created_at: string }>();
    if (last?.created_at) {
      const lastTs = new Date(last.created_at.replace(" ", "T") + "Z").getTime();
      if (Number.isFinite(lastTs) && Date.now() - lastTs < SEND_CODE_COOLDOWN_MS) {
        return json({ error: "发送过于频繁，请 60 秒后再试" }, 429);
      }
    }

    const code = String(Math.floor(100000 + Math.random() * 900000));
    const expiresAt = new Date(Date.now() + CODE_TTL_MS).toISOString();
    await env.DB.batch([
      env.DB.prepare("DELETE FROM codes WHERE is_used = 1 OR expires_at <= ?")
        .bind(new Date().toISOString()),
      env.DB.prepare("DELETE FROM codes WHERE email = ?").bind(email),
      env.DB.prepare("INSERT INTO codes (email, code, expires_at, attempts) VALUES (?, ?, ?, 0)")
        .bind(email, code, expiresAt)
    ]);
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
        text: `您的${type}验证码是：${code}，有效期 5 分钟。请勿将验证码透露给他人。`,
        html: verificationEmailHtml(type, code)
      })
    });
    if (!response.ok) return json({ error: "发送失败" }, 500);
    return json({ message: "已发送" });
  }

  // -------- register（签发 token）--------
  if (url.pathname === "/api/register" && request.method === "POST") {
    if (!await verifyTurnstile(body.cf_token as string | undefined, "register", request, env, env.DB)) {
      return json({ error: "人机验证失败，请重试" }, 403);
    }
    const email = String(body.email ?? "");
    const username = String(body.username ?? "");
    const password = String(body.password ?? "");
    const code = String(body.code ?? "");
    if (!email || !password || !code) return json({ error: "缺参数" }, 400);

    const validCode = await validateCode(env.DB, email, code);
    if (!validCode) return json({ error: "码不对或过期" }, 400);

    try {
      await env.DB.batch([
        env.DB.prepare("DELETE FROM codes WHERE id = ?").bind(validCode.id),
        env.DB.prepare("INSERT INTO users (email, username, password) VALUES (?, ?, ?)")
          .bind(email, username, await hashPassword(password))
      ]);
    } catch {
      return json({ error: "该邮箱或用户名已注册" }, 400);
    }
    const token = await createToken(env.SECRET_KEY, email, username, "user");
    return json({ message: "注册成功", token, user: {
      email, username, orange_balance: 0, role: "user"
    } }, 201);
  }

  // -------- login（签发 token）--------
  if (url.pathname === "/api/login" && request.method === "POST") {
    if (!await verifyTurnstile(body.cf_token as string | undefined, "login", request, env, env.DB)) {
      return json({ error: "人机验证失败，请重试" }, 403);
    }
    const loginMethod = String(body.method ?? "password");
    if (loginMethod !== "password" && loginMethod !== "code") {
      return json({ error: "不支持的登录方式" }, 400);
    }

    if (loginMethod === "code") {
      const email = String(body.email ?? "");
      const code = String(body.code ?? "");
      if (!email || !code) return json({ error: "邮箱和验证码不能为空" }, 400);
      const user = await getUserByEmail(env.DB, email);
      if (!user) return json({ error: "该邮箱未注册" }, 404);
      const validCode = await validateCode(env.DB, email, code);
      if (!validCode) return json({ error: "验证码错误或已过期" }, 400);
      await env.DB.prepare("DELETE FROM codes WHERE id = ?").bind(validCode.id).run();
      const token = await createToken(env.SECRET_KEY, user.email, user.username, user.role ?? "user");
      return json({ message: `欢迎回来，${user.username}！`, token, user: {
        email: user.email,
        username: user.username,
        orange_balance: user.orange_balance ?? 0,
        role: user.role ?? "user"
      }});
    }

    const account = String(body.account ?? "");
    const password = String(body.password ?? "");
    if (!account || !password) return json({ error: "账号和密码不能为空" }, 400);
    const user = await getUserByIdentifier(env.DB, account);
    if (!user) return json({ error: "用户不存在" }, 401);
    if (!await verifyPassword(user.password, password)) return json({ error: "密码错误" }, 401);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM checkin_records WHERE email = ?")
      .bind(user.email).first<{ count: number }>();
    const token = await createToken(env.SECRET_KEY, user.email, user.username, user.role ?? "user");
    return json({
      message: `欢迎回来，${user.username}！`,
      token,
      user: {
        email: user.email,
        username: user.username,
        orange_balance: user.orange_balance ?? 0,
        sign_in_count: Number(count?.count ?? 0),
        role: user.role ?? "user"
      }
    });
  }

  // -------- checkin（Bearer token + 东八区日期 + 唯一约束）--------
  if (url.pathname === "/api/checkin" && request.method === "POST") {
    const auth = await getAuth(request, env);
    if (!auth) return json({ error: "请先登录后再签到" }, 401);
    const user = await getUserByEmail(env.DB, auth.email);
    if (!user) return json({ error: "用户不存在" }, 404);
    const date = todayCN();
    if (user.last_sign_in_date === date) {
      return json({ error: "今日已签到", orange_balance: user.orange_balance ?? 0 }, 409);
    }
    const balance = Number(user.orange_balance ?? 0) + 5;
    await env.DB.batch([
      env.DB.prepare("INSERT INTO checkin_records (email, checkin_date, points) VALUES (?, ?, 5)").bind(user.email, date),
      env.DB.prepare("UPDATE users SET orange_balance = ?, last_sign_in_date = ? WHERE email = ?").bind(balance, date, user.email)
    ]);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM checkin_records WHERE email = ?")
      .bind(user.email).first<{ count: number }>();
    return json({ message: "签到成功", points: 5, orange_balance: balance, last_sign_in_date: date, sign_in_count: Number(count?.count ?? 0), has_checked_in_today: true });
  }

  // -------- admin/users（Bearer token + admin）--------
  if (url.pathname === "/api/admin/users" && request.method === "GET") {
    const auth = await getAuth(request, env);
    if (!auth) return json({ error: "未登录" }, 401);
    const admin = await getUserByEmail(env.DB, auth.email);
    if (!admin || admin.role !== "admin") return json({ error: "无权限" }, 403);
    const users = await env.DB.prepare("SELECT id, email, username, orange_balance, role FROM users ORDER BY id").all();
    return json({ users: users.results.map((u) => ({ ...u, is_protected: isProtectedUser({ email: String(u.email), username: String(u.username) }, env) })) });
  }

  // -------- admin/users/update（Bearer token + 非负余额 + 保护账号）--------
  if (url.pathname === "/api/admin/users/update" && request.method === "POST") {
    const auth = await getAuth(request, env);
    if (!auth) return json({ error: "未登录" }, 401);
    const admin = await getUserByEmail(env.DB, auth.email);
    if (!admin || admin.role !== "admin") return json({ error: "无权限" }, 403);

    const target = await env.DB.prepare("SELECT id, email, username, orange_balance, role FROM users WHERE id = ?")
      .bind(Number(body.id)).first<User>();
    if (!target) return json({ error: "用户不存在" }, 404);
    const role = String(body.role ?? "").toLowerCase();
    if (!["admin", "user"].includes(role)) return json({ error: "角色值无效" }, 400);
    if ((isProtectedUser(target, env) || target.email === admin.email) && role !== "admin") {
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

  // -------- admin/logs（Bearer token + activity_logs）--------
  if (url.pathname === "/api/admin/logs" && request.method === "GET") {
    const auth = await getAuth(request, env);
    if (!auth) return json({ error: "未登录" }, 401);
    const admin = await getUserByEmail(env.DB, auth.email);
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
        ? await request.clone().json<Record<string, unknown>>().catch(() => ({}))
        : {};
      const response = await handle(request, env);
      await recordActivity(env.DB, request, response, body, env);
      return cors(response, request);
    } catch (error) {
      console.error(error);
      return cors(json({ error: "服务器内部错误" }, 500), request);
    }
  }
};
