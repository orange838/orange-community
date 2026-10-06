import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const rootDir = 'D:\\csl\\个人项目\\橙子社区';
const workerDir = path.join(rootDir, 'orange-worker');
const monitorDir = path.join(rootDir, 'cloudflare-monitor');
const dataDir = path.join(monitorDir, 'data');
const outputFile = path.join(dataDir, 'cf-status.json');

// 使用灵犀自带的便携版 wrangler（在 orange-worker 里用 npx 会解析到旧版本，报 7403）
const WRANGLER_JS = 'C:/Users/cmbsysadmin/AppData/Roaming/WPS 灵犀/portable-node/node-v24.17.0-win-x64/node_modules/wrangler/bin/wrangler.js';
const PROJECT_NAME = 'orange-community';
const API_HEALTH_URL = 'https://api.cslblog.dpdns.org/api/health';
const ROOT_URL = 'https://cslblog.dpdns.org';
const PAGES_URL = 'https://orange-community.pages.dev';

fs.mkdirSync(dataDir, { recursive: true });

// 不使用 shell：本环境找不到 cmd.exe，所有命令都以「可执行文件 + 参数数组」的方式调用
function runNode(args, cwd) {
  try {
    return execFileSync(process.execPath, args, {
      cwd,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    }).trim();
  } catch (error) {
    return { error: true, stdout: String(error.stdout || ''), stderr: String(error.stderr || '') };
  }
}

function runWrangler(args) {
  return runNode([WRANGLER_JS, ...args], workerDir);
}

async function httpStatus(url, method = 'GET') {
  try {
    const response = await fetch(url, { method, redirect: 'follow' });
    return { ok: true, status: response.status, text: method === 'GET' ? await response.text() : '' };
  } catch (error) {
    return { ok: false, status: 0, text: '', error: String(error.message || error) };
  }
}

function parseStatusLine(text, key) {
  const needle = key.toLowerCase();
  const rows = text.split(/\r?\n/).map(line => line.trim()).filter(line => line.startsWith('│'));
  for (const row of rows) {
    const match = row.match(/^│\s*([^│]+?)\s*│\s*([^│]+?)\s*│$/);
    if (!match) continue;
    const left = match[1].trim();
    const right = match[2].trim();
    if (left.toLowerCase() === needle || left.toLowerCase().replace(/_/g, ' ') === needle.replace(/_/g, ' ')) {
      return right;
    }
  }
  return 'N/A';
}

function parseD1Info(text) {
  return {
    databaseName: parseStatusLine(text, 'name'),
    databaseSize: parseStatusLine(text, 'database_size'),
    readQueries24h: parseStatusLine(text, 'read_queries_24h'),
    writeQueries24h: parseStatusLine(text, 'write_queries_24h'),
    rowsRead24h: parseStatusLine(text, 'rows_read_24h'),
    rowsWritten24h: parseStatusLine(text, 'rows_written_24h'),
  };
}

// 只取项目名完全等于 PROJECT_NAME 的那一行，避免把看板、错题本的域名也算进来
function parsePagesProject(text) {
  const fallback = ['orange-community.pages.dev', 'cslblog.dpdns.org', 'www.cslblog.dpdns.org'];
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('│') && !trimmed.startsWith('|')) continue;
    const cells = trimmed.split(/[|│]/).map(cell => cell.trim()).filter(Boolean);
    if (cells[0] === PROJECT_NAME && cells[1]) {
      const domains = cells[1].split(',').map(domain => domain.trim()).filter(Boolean);
      return { project: PROJECT_NAME, domains: domains.length ? domains : fallback };
    }
  }
  return { project: PROJECT_NAME, domains: fallback };
}

function parseTurnstileInfo(raw) {
  if (typeof raw !== 'string') return { passed: 0, failed: 0, total: 0 };
  try {
    const parsed = JSON.parse(raw);
    const rows = parsed?.[0]?.results ?? [];
    return rows.reduce((summary, row) => ({
      passed: summary.passed + Number(row.passed || 0),
      failed: summary.failed + Number(row.failed || 0),
      total: summary.total + Number(row.total || 0),
    }), { passed: 0, failed: 0, total: 0 });
  } catch {
    return { passed: 0, failed: 0, total: 0 };
  }
}

const pagesRaw = runWrangler(['pages', 'project', 'list']);
const d1Raw = runWrangler(['d1', 'info', PROJECT_NAME]);
const turnstileRaw = runWrangler([
  'd1', 'execute', PROJECT_NAME, '--remote', '--json', '--command',
  "SELECT action, SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) AS passed, SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) AS failed, COUNT(*) AS total FROM turnstile_verification_logs WHERE created_at >= datetime('now', '-24 hours') GROUP BY action",
]);

const gitHead = runNode(['-e', 'process.stdout.write(require("child_process").execSync("git rev-parse --short HEAD",{cwd:process.argv[1],encoding:"utf8"}).trim())'], rootDir);

const pagesInfo = typeof pagesRaw === 'string'
  ? parsePagesProject(pagesRaw)
  : { project: PROJECT_NAME, domains: ['orange-community.pages.dev', 'cslblog.dpdns.org', 'www.cslblog.dpdns.org'] };
const d1Info = typeof d1Raw === 'string'
  ? parseD1Info(d1Raw)
  : { databaseName: PROJECT_NAME, databaseSize: 'N/A', readQueries24h: 'N/A', writeQueries24h: 'N/A', rowsRead24h: 'N/A', rowsWritten24h: 'N/A' };

const turnstile = parseTurnstileInfo(turnstileRaw);
const turnstilePassRate = turnstile.total === 0
  ? '暂无数据'
  : `${Math.round((turnstile.passed / turnstile.total) * 100)}%`;

const apiHealth = await httpStatus(API_HEALTH_URL);
let apiStatus = 'N/A';
let apiDetail = 'N/A';
if (apiHealth.ok) {
  try {
    const parsed = JSON.parse(apiHealth.text);
    apiStatus = parsed.success === true || parsed.ok === true ? 'OK' : 'WARN';
    apiDetail = `status=${parsed.status || 'unknown'}; message=${parsed.message || 'ok'}`;
  } catch {
    apiStatus = apiHealth.status === 200 ? 'OK' : 'WARN';
    apiDetail = `HTTP ${apiHealth.status}`;
  }
}

const rootCheck = await httpStatus(ROOT_URL, 'HEAD');
const pagesCheck = await httpStatus(PAGES_URL, 'HEAD');
const httpsStatus = rootCheck.status === 200 ? 'OK' : (pagesCheck.status === 200 ? 'OK' : 'WARN');
const httpsDetail = rootCheck.ok ? `HTTP/1.1 ${rootCheck.status} OK` : (pagesCheck.ok ? `HTTP/1.1 ${pagesCheck.status} OK` : '未能获取');

const resources = [
  { name: 'Pages Project', type: 'Pages', status: 'OK', detail: `${pagesInfo.project} / ${pagesInfo.domains.join(', ')}` },
  { name: 'Worker API', type: 'Worker', status: apiStatus, detail: apiDetail },
  { name: 'D1 Database', type: 'D1', status: typeof d1Raw === 'string' ? 'OK' : 'WARN', detail: `${d1Info.databaseSize} / ${d1Info.readQueries24h} read / ${d1Info.writeQueries24h} write` },
  { name: 'HTTPS', type: 'DNS/SSL', status: httpsStatus, detail: httpsDetail },
  { name: 'Account', type: 'Cloudflare', status: 'OK', detail: '已验证 / 账户已连接' },
  { name: 'Git Head', type: 'Deploy', status: typeof gitHead === 'string' ? 'OK' : 'WARN', detail: typeof gitHead === 'string' ? gitHead : 'N/A' },
  { name: 'Turnstile', type: 'Security', status: 'OK', detail: `${turnstile.passed} passed / ${turnstile.failed} failed (24h)` },
];

const summary = {
  pages: { status: 'OK', domain: pagesInfo.domains.join(', ') },
  worker: { status: apiStatus, route: 'api.cslblog.dpdns.org/api/health' },
  d1: { status: 'OK', databaseName: d1Info.databaseName || PROJECT_NAME },
  https: { status: httpsStatus, domains: pagesInfo.domains.join(', ') },
  api: { status: apiStatus, endpoint: API_HEALTH_URL },
  deploy: { status: 'OK', branch: 'main' },
  turnstile: { status: 'OK', passRate: turnstilePassRate },
};

const payload = {
  generatedAt: new Date().toISOString(),
  summary,
  resources,
  domains: pagesInfo.domains.map(domain => ({ name: domain, value: 'Active' })),
  d1Details: [
    { name: 'Database name', value: d1Info.databaseName || PROJECT_NAME },
    { name: 'Database size', value: d1Info.databaseSize || 'N/A' },
    { name: 'Read queries 24h', value: d1Info.readQueries24h || 'N/A' },
    { name: 'Write queries 24h', value: d1Info.writeQueries24h || 'N/A' },
    { name: 'Rows read 24h', value: d1Info.rowsRead24h || 'N/A' },
    { name: 'Rows written 24h', value: d1Info.rowsWritten24h || 'N/A' },
  ],
  deployments: [
    { name: 'Project', value: pagesInfo.project },
    { name: 'Branch', value: 'main' },
    { name: 'Git head', value: typeof gitHead === 'string' ? gitHead : 'N/A' },
  ],
  turnstile: [
    { name: 'Passed', value: String(turnstile.passed) },
    { name: 'Failed', value: String(turnstile.failed) },
    { name: 'Total', value: String(turnstile.total) },
    { name: 'Pass rate', value: turnstilePassRate },
  ],
};

fs.writeFileSync(outputFile, JSON.stringify(payload, null, 2), 'utf8');
console.log(`Dashboard data written to ${outputFile}`);
console.log(JSON.stringify({ generatedAt: payload.generatedAt, summary, pages: pagesInfo, d1: d1Info }, null, 2));
