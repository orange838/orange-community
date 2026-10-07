const summaryGrid = document.getElementById('summaryGrid');
const resourceTableBody = document.getElementById('resourceTableBody');
const domainList = document.getElementById('domainList');
const d1List = document.getElementById('d1List');
const deploymentList = document.getElementById('deploymentList');
const turnstileList = document.getElementById('turnstileList');
const updatedAt = document.getElementById('updatedAt');
const refreshBtn = document.getElementById('refreshBtn');

function formatStatus(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized.includes('ok') || normalized.includes('healthy') || normalized.includes('online') || normalized === 'success' || normalized === 'active') {
    return '正常';
  }
  if (normalized.includes('warn') || normalized.includes('warning') || normalized.includes('partial')) {
    return '警告';
  }
  if (normalized.includes('err') || normalized.includes('error') || normalized.includes('failed') || normalized.includes('fail')) {
    return '异常';
  }
  if (normalized === 'n/a' || normalized.includes('unknown') || normalized.includes('无法获取')) {
    return '未知';
  }
  return value || 'N/A';
}

function badgeClass(status) {
  const normalized = String(status || '').toLowerCase();
  if (normalized.includes('ok') || normalized.includes('healthy') || normalized.includes('online') || normalized === 'success' || normalized === 'active') {
    return 'ok';
  }
  if (normalized === 'n/a' || normalized === 'unknown' || normalized.includes('未知') || normalized.includes('无法获取')) {
    return 'warn';
  }
  if (normalized.includes('warn') || normalized.includes('warning') || normalized.includes('partial')) {
    return 'warn';
  }
  return 'err';
}

function labelMap(label) {
  const map = {
    'Pages Project': 'Pages 项目',
    'Worker API': 'Worker 接口',
    'D1 Database': 'D1 数据库',
    'Git Head': 'Git 头提交',
    'Database name': '数据库名',
    'Tables': '数据表数量',
    'Users': '用户数',
    'Check-ins': '签到记录数',
    'Invite codes': '邀请码数量',
    'Turnstile records': '人机验证记录数',
    'Database size': '数据库大小',
    'Read queries 24h': '24h 读查询',
    'Write queries 24h': '24h 写查询',
    'Rows read 24h': '24h 读取行数',
    'Rows written 24h': '24h 写入行数',
    'Project': '项目',
    'Branch': '分支',
    'Git head': 'Git 头提交',
    'Pages': 'Pages 项目',
    'Worker': 'Worker 接口',
    'D1': 'D1 数据库',
    'API': 'API 健康',
    'Deploy': '部署状态',
    'Turnstile': '人机验证',
    'Passed': '通过次数',
    'Failed': '失败次数',
    'Total': '总次数',
    'Pass rate': '通过率',
    'HTTPS': 'HTTPS',
    'Cloudflare': 'Cloudflare',
    'DNS/SSL': 'DNS/SSL',
    'Security': '安全',
    'Status file': '状态文件',
    'No data': '暂无',
    'Active': '正常',
    'OK': '正常',
    'WARN': '警告',
    'ERR': '异常'
  };

  return map[String(label)] ?? String(label);
}

function renderSummary(summary) {
  const cards = [
    { label: 'Pages', value: formatStatus(summary.pages?.status), meta: summary.pages?.domain || '未知' },
    { label: 'Worker', value: formatStatus(summary.worker?.status), meta: summary.worker?.route || '未知' },
    { label: 'D1', value: formatStatus(summary.d1?.status), meta: summary.d1?.databaseName || '未知' },
    { label: 'HTTPS', value: formatStatus(summary.https?.status), meta: summary.https?.domains || '未知' },
    { label: 'API', value: formatStatus(summary.api?.status), meta: summary.api?.endpoint || '未知' },
    { label: 'Deploy', value: formatStatus(summary.deploy?.status), meta: summary.deploy?.branch || 'main' },
    { label: 'Turnstile', value: formatStatus(summary.turnstile?.status), meta: summary.turnstile?.passRate || '暂无数据' }
  ];

  summaryGrid.innerHTML = cards.map(card => `
    <article class="summary-card">
      <span class="summary-label">${labelMap(card.label)}</span>
      <p class="summary-value">${card.value}</p>
      <div class="summary-meta">${card.meta}</div>
    </article>
  `).join('');
}

function renderResourceTable(items) {
  resourceTableBody.innerHTML = items.map(item => `
    <tr>
      <td>${labelMap(item.name)}</td>
      <td>${labelMap(item.type)}</td>
      <td><span class="badge ${badgeClass(item.status)}">${formatStatus(item.status)}</span></td>
      <td>${item.detail}</td>
    </tr>
  `).join('');
}

function renderList(target, items) {
  target.innerHTML = items.map(item => `
    <li>
      <strong>${labelMap(item.name)}</strong>
      <span>${labelMap(item.value)}</span>
    </li>
  `).join('');
}

const LIVE_STATUS_URL = 'https://api.cslblog.dpdns.org/api/status';

// 只显示实时数据，避免接口不可用时把过期快照误当成当前状态
async function fetchDashboardData() {
  const live = await fetch(LIVE_STATUS_URL, { cache: 'no-store' });
  if (!live.ok) {
    throw new Error(`实时状态接口返回 HTTP ${live.status}`);
  }
  return await live.json();
}
async function loadDashboard() {
  try {
    const data = await fetchDashboardData();
    renderSummary(data.summary);
    renderResourceTable(data.resources);
    renderList(domainList, data.domains);
    renderList(d1List, data.d1Details);
    renderList(deploymentList, data.deployments);
    renderList(turnstileList, data.turnstile);

    const ts = new Date(data.generatedAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
    updatedAt.textContent = `更新时间：${ts}`;
  } catch (error) {
    console.error('监控数据加载失败：', error);
    renderSummary({
      pages: { status: '未知', domain: '实时状态暂不可用' },
      worker: { status: '未知', route: '实时状态暂不可用' },
      d1: { status: '未知', databaseName: '实时状态暂不可用' },
      https: { status: '未知', domains: '实时状态暂不可用' },
      api: { status: '未知', endpoint: '实时状态暂不可用' },
      deploy: { status: '未知', branch: '实时状态暂不可用' }
    });

    renderResourceTable([
      { name: '实时监控接口', type: 'Worker API', status: 'warn', detail: '无法读取实时状态；请稍后重试，不展示过期快照' }
    ]);

    const unavailable = [{ name: '状态', value: '未知' }];
    renderList(domainList, unavailable);
    renderList(d1List, unavailable);
    renderList(deploymentList, unavailable);
    renderList(turnstileList, unavailable);
    updatedAt.textContent = '实时状态暂不可用';
  }
}

refreshBtn.addEventListener('click', loadDashboard);
loadDashboard();
