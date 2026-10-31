# AI 助手共享交接记录

> 所有参与本仓库的编程助手先阅读根目录 [`AGENTS.md`](./AGENTS.md) 和本文档。
> 本文只记录项目上下文和变更摘要，不存放密钥或其他秘密。

## 项目现状

- 仓库：`orange838/orange-community`，主要分支：`main`。
- 前端：`orange-frontend/`，Vue 3 + Vite。
- 生产 API：`orange-worker/`，Cloudflare Worker + D1；`orange-backend/` 是本地 FastAPI + SQLite 后端。两个目录同属此 Git 仓库，API 路由与主要业务行为需保持同步。
- 监控界面：`cloudflare-monitor/`；读取 Worker 的 `/api/status` 实时状态。
- 生产 Worker 绑定 D1。第三方凭据应只通过运行环境的 Secret 管理；不得写入源码、此文件或 Git。
- 仓库许可证已改为根目录 `LICENSE` 中的自定义非商业使用许可：非商业用途按条款使用，商业用途须事先取得书面授权；不是 GPLv3 / OSI 开源许可证。

## 最近同步点

- 最近同步的后端代码提交：`ae7e990`（2026-10-20，本地 FastAPI 与生产 Worker API 对齐）。
- 最近同步的前端提交：`428e585`（2026-10-31，登录统一提示 + 失败限流 + 安全响应头）；上一版 `392dbe4`（2026-10-29，新增推广链接分栏 + 页脚徽章飞入动画）；此前 `b30e9d0`（2026-10-25，娃娃机帮助弹窗 logo 加版本参数绕过旧 404 缓存）；该提交之前依次有玻璃主题 `f6e32ea`、许可证 `197d43f`、验证码中文化 `2544266`/`2c33331`、logo 补齐 `fcfa9d5`。
- 在继续任务前，检查从该提交到当前 HEAD 的提交，以及所有未提交修改。
- `build-guide.js` 和 `橙子社区类项目搭建指南.docx` 在最近检查时是未跟踪的用户文件；除非用户明确要求，不要编辑、删除或纳入提交。
- `ae7e990` 已提交；推送前需检查当前 `main` 与 `origin/main` 的 ahead/behind 状态。账号封禁/超级管理员相关代码已在当前历史中，生产 D1 的封禁字段迁移状态需以数据库实际状态确认。

## 已知行为与注意事项

- Worker 的 `/api/status` 为监控看板提供实时状态数据，包含 Pages/域名探测、API、D1 计数、Git 提交和 Turnstile 汇总。
- 监控应区分“正常 / 警告 / 未知”；探测或 D1 查询失败不能用“正常”或 0 伪装。
- 看板实时状态接口不可用时，不要把静态快照冒充为当前实时状态。
- Turnstile 统计只记录动作、通过状态、主机名和时间；不应保存验证 Token。
- `orange-backend/main.py` 与 `orange-worker/src/index.ts` 当前有相同的 32 个 HTTP 路由；SQLite/D1 持久化写法和运行时健康状态文案按各自环境区分。FastAPI 帖子过滤覆盖常见中英文词和常见变体，Worker 使用 `glin-profanity` 的完整词库，词库覆盖面不完全相同。
- README 不应包含本地运行/部署方法，也不应包含 Cloudflare 部署说明。

## 最近交接记录

### 2026-10-31 — 登录安全加固（对照《AI 写的登录页安全自查》海报）
- 同提示防枚举：密码登录统一回“账号或密码错误”，验证码登录统一回“邮箱或验证码错误”；账号不存在时也跑一次 PBKDF2 假哈希（`DUMMY_PASSWORD_HASH`），避免响应耗时泄露账号是否存在。
- 登录限流：新增 `login_attempts` 表（identifier + ip 主键），15 分钟内失败 5 次锁 15 分钟，返回 429 + `retry_after_minutes`；登录成功清计数。Worker 与本地 `main.py` 两边同步。
- 踩过的坑：最初锁定后把 failures 写成 0，导致第 6 次请求又把锁解了；改成“累计值照存 + 只设 locked_until”。改这里时别再把计数归零。
- 安全头：新增 `orange-frontend/public/_headers`（HSTS / X-Frame-Options DENY / Referrer-Policy / Permissions-Policy / CSP），Worker 的 cors() 里补 HSTS + nosniff，本地 FastAPI 加同名中间件。
- CSP 不带 `'unsafe-inline'`：把 `index.html` 的首屏主题内联脚本拆到 `public/theme-init.js`；改回内联会直接触发 CSP 拦截、首屏主题失效。
- XSS 现状：全站无 `v-html` / `innerHTML`，用户内容全走插值转义；但 token 仍存 localStorage（XSS 可直接窃取），改 HttpOnly Cookie 涉及跨域，尚未做。
- 未改的例外：`/api/send-code?type=reset` 与 `/api/reset-password` 仍会回“该邮箱尚未注册”，属于另一种枚举口子；改成静默回“已发送”会影响“收不到验证码”的排查体验，待定。

### 2026-10-29 — 新增「推广链接」分栏 + 页脚徽章飞入动画
- 侧栏在“公告”后新增 `/promo`「推广链接」，页面 `src/view/Promo.vue`。
- 三张卡片：DigitalPlat FreeDomain、土豆公益（就是页脚那两个徽章），以及纵横铁路 `zhtl.cslblog.dpdns.org`（Minecraft 1.21.1 + NeoForge 21.1.x、v1.3.0、GPL-3.0，文案按站点实际内容写，不要随意编）。
- 动画实现：共享元素花招。进入页面时量页脚 `[data-promo-badge]` 的 rect，把卡片先 translate+scale 到那个位置再回弹到原位，同时页脚淡出；`onBeforeUnmount` 全部复原。**仅 `html.style-glass` 生效**，兼容模式直接静态显示；另尊重 `prefers-reduced-motion`。
- 页脚两个 `<a>` 已加 `data-promo-badge="digitalplat|tudou"` 和 `class="footer-badge"`，改页脚时别删，否则动画失去起点。
- 实测：glass 中途帧矩阵有位移且页脚 opacity→0；classic 无 transform；390 宽无横向溢出；`npm run build` 通过。

### 2026-10-26 — 本地 FastAPI 与线上 Worker 全量对账
- 逐接口比对 33 个路由：路由集合、鉴权、密码哈希（`pbkdf2:sha256:100000`）、Turnstile（action + hostname 白名单 + Origin 一致）、验证码冷却 60s 与最多 5 次尝试、签到 +5 橙子 + 邀请人 +2、注册拉新 +10、封禁/禁言、帖子 80/5000 字限制、六位拉新码、弱密码提醒 —— 均一致。
- 差异已修：本地原先只有 40 个硬编码敏感词，线上用 `glin-profanity` 全词库。新增 `orange-worker/scripts/export-profanity-words.mjs` 从依赖包导出 english 415 + chinese 293 词到 `orange-backend/profanity_words.json`；`filter_profanity` 改为加载该词库并预编译正则，保留 `ignore:["逼"]` 对齐线上（“牛逼”不误伤）。
- 升级 `glin-profanity` 后重跑导出脚本即可，不要手改 JSON。
- 已知过度过滤（两侧一致，要改得同时改）：中文词库含“乳”“卵”等单字，`乳制品` 会被替换成 `***制品`。
- 环境差异保留：`/api/status` 本地探测域名 + 读 SQLite + git HEAD，线上查 D1/Pages/GitHub；Turnstile 服务异常时本地返回具体原因，线上只返回失败。

### 2026-10-25 — 娃娃机帮助弹窗 logo 404 修复
- 现象：`/captcha` 帮助弹窗顶部图标破图。根因是本地化副本里写死引用 `/playcaptcha.svg`，而文件只存在于 `public/playcaptcha/playcaptcha.svg`。
- 处理：`public/playcaptcha.svg` 补齐一份（commit `fcfa9d5`）；线上该路径已返回 `200 image/svg+xml`，headless 实测 `naturalWidth=683`。
- 用户强刷后仍见破图，判断是浏览器缓存了旧的 404 响应，故把 `playcaptcha-local.js` 里引用改成 `/playcaptcha.svg?v=2` 破坏缓存（commit `b30e9d0`）。
- 后续图片有改动时同步递增 `?v=` 版本号；`public/` 根路径与 `public/playcaptcha/` 下各有一份，替换时保持一致。

### 2026-10-25 — 抓娃娃验证码中文化
- 新增 `src/components/playcaptcha-local.js`：从 `playcaptcha@0.1.0` 的 `dist/index.js` 复制，仅替换界面文案（标题、步骤、按钮、提示、错误提示、帮助弹窗、玩具名称），逻辑与画布代码未改。
- `PlayCaptcha.vue` 改为从本地副本导入（CSS 仍用 `src/assets/clawcaptcha.css`）；npm 包保留在依赖里备用。
- 升级 `playcaptcha` 时需重新对照 dist 打补丁，**不要直接覆盖本地文件**，否则文案会退回英文。
- 实测：`/captcha` 全部文案为中文，排版无溢出；线上 bundle 已含中文（`index-DUJ9nvya.js`）。
- commit `2544266`，已推送并部署。

### 2026-10-25 — 推送方式改为本机专用 SSH 密钥（不再需要人工 push）
- 背景：主站与错题本仓库此前的 push 依赖用户本机 `~/.ssh`，而 Agent 运行身份读不到该目录，导致每次都要用户手动 push。
- 现在：本仓库 `.ssh/lingxi_ed25519`（已在 `.gitignore`，**绝不入库**）为该机器专用密钥，用户已在 GitHub 账号里登记为 `lingxi-agent`。
- 两个仓库的 `core.sshCommand` 均指向该密钥，并带 `HostName=20.205.243.166`（本机 hosts 会把 github.com 指到 127.0.0.1，必须覆盖）与仓库内 `known_hosts`。
- 后续 Agent 可直接 `git push`，无需用户介入；换机器或换密钥时只需重新生成本地密钥并在 GitHub 登记，**不要把私钥写进任何文档或提交**。
- 本次提交 `e1b3827`（.gitignore 增加 `.ssh/`、`.tmp-test/`）。

### 2026-10-25 — 许可证改为 PolyForm Noncommercial + 附加许可
- `LICENSE` 由自写的「橙子社区非商业使用许可」替换为：**PolyForm Noncommercial License 1.0.0 官方原文（未改）** + 第 2 部分额外许可 + 第 3 部分署名 + 第 4 部分免责。
- 关键规则：非商业自由使用/修改/分发且**不强制开源**；商业只能「公开修改版源码」或「书面商业授权」二选一；**署名必须保留**，只有商业授权明确约定时才可移除；PolyForm 原文的「非商业组织无条件可用」被 2.4 条收紧为按实际用途判断。
- 新增 `NOTICE`（Required Notice 行 + 许可摘要 + 授权邮箱 `admin@cslblog.dpdns.org`）；`README.md` / `README.zh_CN.md` 的许可段同步重写；`.gitignore` 增加 `.tmp-test/`。
- commit `415251c`，待推送。

### 2026-10-25 — 亚克力毛玻璃主题 + 样式开关
- 新增 `src/composables/useStyleMode.js`（模块级共享 ref），`html.style-glass` / `html.style-classic` 两个根类控制主题；选择写入 `localStorage.site_style`，`index.html` 内联脚本在首屏渲染前打类，避免刷新闪烁；不支持 `backdrop-filter` 时自动降级为 `classic`。
- **默认 classic（兼容纯色）**，和改造前完全一致；用户主动开开关才进 glass。
- 侧边栏底部新增开关控件（兼容 / 圆点 / 新版），`role="switch"` + `aria-checked`；原「文字按钮」方案已删除，演示页 `/style-demo` 也已删除。
- glass 主题：`body::before` 固定渐变光斑 + `body::after` SVG 噪点（`mix-blend-mode: overlay`，opacity .26）；侧栏、顶栏、消息面板、内容卡片、登录卡片全部 `backdrop-filter: blur()` 半透明，内容卡片 alpha .74 保证可读；`prefers-reduced-transparency` 与 `@supports not` 双重降级。
- 实测（headless，1280×860）：切换后 `html.style-glass`、`aria-checked`、`localStorage` 三者一致；页面高度 860/860 无滚动条。
- commit `1f7ef91`，待推送。

### 2026-10-25 — 侧边栏新增 QQ 交流群入口
- `.sidebar-footer` 在「GitHub 仓库」上方新增一条外链：`https://qm.qq.com/q/J1lkB9JoWc`，显示文案「💬 加入 QQ 交流群」；页面级滚动条仍为 0（1280×800 与 390×844 实测 doc 高度相等）。
- commit `5ba2280`，待推送部署。

### 2026-10-25 — 修复页面级滚动条 + 登录/注册独立整页 + 表单草稿恢复
- **滚动条根因**：`src/style.css` 从未被 `main.js` 引入，`html/body` 一直带着浏览器默认 8px 外边距，而 `.app-container` 为 `height:100vh`，整页多出 16px → 页面级滚动条。
  - 已在 `main.js` 引入 `style.css`，并把 `html, body` 设为 `margin:0; height:100%; overflow:hidden`、`#app` 铺满、统一 `box-sizing:border-box`。
  - `.app-container` 增加 `overflow:hidden` 与 `100dvh` 兜底；`.main-wrapper` 补 `min-width/min-height:0`；顶栏与页脚 `flex:none`，保证只有 `.content-area` 内部滚动。
- **登录/注册、人机验证改独立整页**：`/login`、`/captcha` 不再套在侧边栏/顶栏/页脚里（App.vue 新增 `isBarePage` + `.bare-shell`，Toast 移到最外层保证任何页面可用）。登录页卡片居中、加了"← 返回首页"，页面模式压缩了间距避免内容区滚动。
- **娃娃机移动端横向溢出**：`.play-captcha-wrap` 原为固定 440px 内容宽度，在 390px 视口溢出；改为 `width:100%;max-width:440px` + `:deep(.clawcap){width:100%}`，`/captcha` 加 `overflow-x:hidden`。
- **表单草稿恢复加固**：`sessionStorage` 草稿抽取为 `saveDraft/restoreDraft`，跳 `/captcha` 前与组件卸载时（仅当前路由为 `/captcha`）各存一次，`onMounted` 最先恢复；登录成功后清除草稿，避免残留凭据。
- **邀请/拉新链接**：App.vue 原 `openModal(false)`（函数已删，运行时报错）改为带 `invite/ref` 参数跳 `/login?mode=register`；`getQueryParam` 优先读 hash 路由 query，兼容 `window.location.search`。
- 实测（headless Chrome，1280×800 / 1280×720 / 390×844）：三档下 `documentElement.scrollHeight == clientHeight`，首页/登录页无页面滚动条；`/login` 独立页无 `.content-area`；填邮箱→获取验证码→`/captcha`→返回后邮箱、登录方式均恢复；390 宽 `/captcha` 无横向溢出。
- commit `0a34d94` 已 push 并部署完成（线上 bundle 含 `.bare-shell` / `back-home`）。
- 遗留：PlayCaptcha 组件文案仍是英文（中文化选了方案 A，尚未替换）；`src/components/playcaptcha-local.js` 为未启用的本地副本，未纳入提交。

### 2026-10-21 — 登录/注册改为独立页面（删除登录弹窗）
- LoginModal 新增 `mode`（modal 默认 | page）：page 模式无遮罩/无关闭按钮，登录成功返回上页或首页。
- 新建 `view/LoginPage.vue` + 路由 `/login`，同页内登录/注册切换（URL `?mode=login|register`）。
- App.vue 删除登录弹窗与 `openModal`，顶部"登录/注册"按钮、SSO 未登录、`open-login-modal` 事件均改跳转 `/login`；Posts.vue `goLogin` 也改跳转。
- 获取验证码的 PlayCaptcha 检查仅在点"获取验证码"时触发，跳 `/captcha` 验证后返回。
- commit `d55f6ac` 已 push，待浏览器验证。
### 2026-10-20 — 同步本地 FastAPI 与线上 Worker 后端
- `orange-backend/main.py` 补齐 Worker 的 `/api/status`、拉新码/归因与奖励、橙子流水、帖子、站内消息、封禁状态与管理接口，并保持邮件验证码尝试限制、密码强度和 Turnstile 动作/主机名校验。
- SQLite 启动迁移新增帖子、消息、推荐奖励、橙子流水和封禁字段；奖励由幂等唯一约束及触发器发放；删除旧拉新码别名表，旧码不再可用。
- 将本地已有的邮箱优先账号查找、HMAC 恒时签名比较同步到 `orange-worker/src/index.ts`；同时移除用户要求删除的 HTTP 2xx 解释文案。
- 验证：Python 编译、Worker TypeScript 检查通过；两端 HTTP 路由集合均为 32 项且一致；隔离 SQLite 测试覆盖邮箱注册和无邮箱邀请码注册、推荐奖励/每日签到幂等、帖子过滤、封禁/解封、橙子日志、旧库迁移与监控响应。
- 提交：`ae7e990`。本次同步范围为同一主仓库内的 `orange-backend/` 与 `orange-worker/` 两个目录；推送待确认。

### 2026-10-19 — 将签到与拉新邀请码整合进任务中心
- `orange-frontend/src/App.vue` 将侧栏“签到”入口改为“任务”；新增 `/tasks` 路由，旧 `/checkin` 自动跳转到任务中心，OAuth 现存跳转链接继续有效。
- 新增 `orange-frontend/src/view/Tasks.vue`：类别采用横向标签切换；每个类别下的任务同时以表格行展示（图标、名称、描述、奖励、操作），不需要点击任务后再显示。迁入原签到操作并保留邮箱账号签到限制；登录用户进入任务中心时自动确保专属拉新码存在。
- `orange-frontend/src/view/Profile.vue` 移除拉新邀请码模块；个人信息页仍保留签到次数摘要。
- 初版提交 `267cd3e` 和自动邀请码/横向分类修订 `b80595b` 已推送。后续改为类别下直接展示所有具体任务列表行，`npm run build` 和 `git diff --check` 通过；当前修订待提交推送。

### 2026-10-19 — 六位拉新码及免邮箱注册归因
- 拉新码改为六位大小写字母/数字组合；旧码立即失效，不保留旧码别名。
- 注册表单对邮箱验证码注册和管理员免邮箱邀请码注册都提供可选拉新码输入；后端两种注册路径都会验证并记录归因，管理员邀请码仅代表免邮箱注册资格，与拉新码分离。
- 更新免邮箱注册与忘记密码文案，说明两种码的用途以及免邮箱账号需先绑定邮箱才可通过邮件重置密码；推广分类改名“推广中心”。
- 验证及推送状态待完成。

### 2026-10-18 — 普通用户拉新邀请码
- `orange-worker/schema.sql` 与 `orange-worker/src/index.ts`：新增每位用户一个可复用拉新码；已登录用户可创建，普通邮箱注册时可附带拉新码并在新表中持久记录邀请人与被邀请人。拒绝无效码及使用本人邮箱自邀；现有管理员生成的一次性无邮箱邀请码流程未改动。
- `orange-frontend/src/view/Profile.vue`：个人信息页创建和复制 `?ref=` 拉新链接；`LoginModal.vue` 支持从链接预填或手动填写拉新码，仍走原有邮箱验证码注册；`App.vue` 识别拉新链接并打开注册弹窗。
- 不发放奖励或额外权益；每位用户仅有一个码，允许重复使用。新表由 Worker 幂等自动创建，`schema.sql` 同步供新库使用。
- 验证：Worker `npm run typecheck`、前端 `npm run build`、SQLite schema/邀请关系 SQL 检查和 `git diff --check` 通过。提交 `3d6a2c8` 已推送到 `origin/main`。

### 2026-10-18 — 看板(cloudflare-monitor)新增帖子数/消息数
- worker `buildDashboardStatus` 的 `/api/status` 额外统计 `posts`（帖子）、`user_messages`（消息）行数，D1 detail 改为 "8 张表 / N 位用户 / M 条帖子 / K 条消息"，d1Details 新增 Posts、Messages 两项。
- 看板前端用 `renderList(d1List, data.d1Details)` 动态遍历渲染，无需改前端，自动显示新项。
- commit `79fce59` 已 push，线上验证 d1Details Posts=0 / Messages=26。
### 2026-10-16 — 账号封禁/禁言与超级管理员

- 修改 `orange-worker/src/index.ts`：用户管理增加封禁、解封和超级管理员权限；封禁原因必填，可永久或按正整数天临时封禁；橙子账号及超级管理员不可被封禁；仅橙子账号可授予/撤销超级管理员角色；超级管理员可使用现有全部后台 API。
- 封禁仅禁止发新帖，保留登录、签到、浏览、个人资料和旧帖；服务端在发帖接口校验，到期后按北京时间显示期限并自动恢复发帖权限。
- 修改 `orange-frontend/src/view/Admin.vue`、`App.vue`、`Posts.vue`、`Profile.vue` 和 `router/index.js`：后台封禁/解封界面、铃铛消息和每次新登录的封禁弹窗、帖子区禁言状态、超级管理员入口与角色显示。
- 修改 `orange-worker/schema.sql` 并新增 `orange-worker/migration_user_bans.sql`：新库 schema 已含字段；已有 D1 需先执行一次迁移再推送触发自动部署。尚未执行数据库迁移或推送。
- 验证：Worker `npm run typecheck`、前端 `npm run build`、迁移 SQL 的 SQLite 结构检查均通过；`git diff --check` 通过。
- 范围按用户确认仅包括生产 Worker 和前端；兼容 FastAPI 后端未修改。
- 登录状态监听另修复为 getter watch source，确保已打开页面后登录也能收到封禁提醒。前端 build 通过。
- 后续同步：上述功能经过历史改写后已进入当前 `main`（相关当前提交包括 `663c43c`、`aa1a5d8`、`cc7d94d`）。生产 D1 是否已执行 `migration_user_bans.sql` 未在本次确认，涉及该表结构的生产操作前需核对。

### 2026-10-12 — 新增帖子广场发帖功能 + glin-profanity 敏感词过滤

- worker（orange-worker）：新增 `/api/posts` POST（鉴权 + 过滤标题/正文后入库）与 GET（列表倒序，可选 limit）；`filterProfanity()` 双 Filter（英文 wordBoundaries:true + 中文 wordBoundaries:false，detectLeetspeak aggressive），命中替换为 ***；`ensurePostsTable()` 首次调用自动建 posts 表。schema.sql 已追加 posts 建表语句。
- 前端（orange-frontend）：新增 `view/Posts.vue`（发帖表单+帖子列表），路由 `/posts`，导航新增"帖子广场"入口。
- 依赖：orange-worker 安装 glin-profanity（零依赖纯 JS，可在 CF Worker 运行）。
- 本地验证：worker typecheck、前端 build 均通过；敏感词过滤逻辑已实测（中英文+变体词 sh1t/f*ck 均命中替换）。
- 提交：`ea7dba6`（发帖）、`9d430f7`（gitignore 本地产物）、`3e803e3`（登录判断改用 token）。已全部 push 并部署上线。
- 线上实测（通过）：用未绑邮箱账号 123 发帖含 f*ck/下贱/sh1t，命中并替换为 ***；列表展示过滤后文本；DB 入库为过滤后内容。

##### 网络排查记录（重要，避免下次重复踩坑）
- 现象：git push / VS Code 报 `ssh: connect to github.com port 22: Connection refused`。
- **根因**：`C:\Windows\System32\drivers\etc\hosts` 被加速工具（很可能是 Steam++ “GitHub 加速”）写入多条 `github.com → 127.0.0.1`，git/命令行走 hosts 优先把 github 解析到本机 127.0.0.1，本机无 22 服务故 refused；真实 IP（如 20.205.243.166）网络是通的。
- 临时绕过（不改系统文件）：`git config core.sshCommand 'ssh -o HostName=<真实IP> -o StrictHostKeyChecking=accept-new'`，IP 会变需重查 `nslookup github.com`；彻底解决应关闭加速器或清理 hosts 的 github 条目。
- 另：D1 API token 只读，无法在线建表/UPDATE；posts 表由 worker `ensurePostsTable()` 启动时自动创建。
- 补充（10-13）：内置中文词库不含拼音缩写（SB/CNM/牛批 能发），已在 filterProfanity 中文 Filter 加 customWords 补齐（sb/cnm/cnmb/nmd/tmd/wqnmlgb/草泥马/尼玛/牛批/牛b/王八蛋/去你妈的/狗日的/色情/约炮 + md/jb/滚镂子/废物/白痴/智障/蠢货/傻狗/舔狗/婊子/贱人/贱货/畜生/杂种/狗东西/绿帽/他妈的/奶奶的/操你/日你/渣男/人渣）。commit `27232b8`，线上实测 SB/CNM/牛批 均替换为 ***。
- 补充（10-13）：`ignoreWords:["逼"]` 豁免"逼"单字，避免"牛逼"误过滤（实测"牛逼/这题真牛逼"通过，"傻逼"仍靠整词拦截，SB 仍拦截）。
- 删帖功能（10-13）：worker 新增 `DELETE /api/posts?id=`（作者本人或管理员可删），前端 Posts.vue 列表项按作者/管理员显示"删除"按钮。commit `f872b03`。线上实测：管理员删除残留帖子 id=2（操）、id=3（SB）成功，DB 已清。
- 消息系统（10-13）：顶部用户名旁新增🔔铃铛 + 未读数（红点/数字），点击弹消息面板展示内容+时间，打开即标记已读；去掉原登录后"管理员改信息"弹窗。worker：删帖时若管理员删别人的帖子→给作者 INSERT 未读消息"管理员删除了你的帖子《xx》"（作者自己删/管理员删自己 不通知）。commit `7bc43f0`。线上实测：管理员删 123 的帖子后，DB 给 123 插入未读消息 id=13 成功；前端铃铛渲染正常。
### 2026-10-11 — 修复绑邮箱提醒弹窗仍不弹（toastRef 挂载时机）

- 现象：消息弹窗（showAlert）刷新能弹，但绑邮箱提醒（showConfirm）刷新不弹。
- 根因：`orange-frontend/src/App.vue` 绑邮箱 watch 用 `{ immediate: true }`。immediate 回调在父组件 **setup 同步阶段**执行，此时 `<Toast ref>` 子组件尚未 mount，`toastRef.value` 为 `null`，`toastRef.value?.showConfirm(...)` 被静默跳过，且 `emailReminded` 已置 true → 之后永不弹。
- 修复：把绑邮箱检查抽成 `remindBindEmail()`，改为 `watch(currentUser.info)`（登录变化触发）+ `onMounted` 里调用一次（刷新/已有登录态场景，此时 Toast 已挂载）。
- 验证：前端 `npm run build` 通过；commit `44dbbef` 已 push，等待部署后实测。
### 2026-10-10 — 修复两个提醒弹窗在页面刷新后不生效

- 根因：`orange-frontend/src/App.vue` 两个 `watch(currentUser.info, ...)`（未绑邮箱提醒、管理员消息提醒）无 `immediate: true`，页面刷新时 `info` 从 localStorage 一开始就有值，`watch` 只在对象变化时触发，初次有值不触发 → 弹窗不弹。
- 修复：两处 watch 结尾加 `{ immediate: true }`。未登录时 `info` 为 null，两处守卫（`emailReminded` / `msgChecked`）仍会正确重置，登录后照常触发。
- 验证：前端 `npm run build` 通过。
- 提交并推送：`d24b56d`。
### 2026-10-09 — 去掉登录提醒的 SSO 限制

- 修改 `orange-frontend/src/App.vue`：未绑邮箱提醒、管理员消息弹窗两处原先 `if (isSsoMode.value || ...) return` 被 SSO 模式（errbook_sso 授权弹窗）跳过，现去掉 `isSsoMode.value` 限制，常规登录与 SSO/OAuth 登录均生效；同步更新两处注释。
- 验证：前端 `npm run build` 通过。
- 提交并推送：`0d4ca57`。

### 2026-10-09 — 页脚新增土豆公益推广徽章

- 修改 orange-frontend/src/App.vue：页脚 .site-footer 改为 flex 布局，在现有 DigitalPlat 徽章旁并排新增一个黄色风格“土豆公益”推广徽章，链接 https://tudouai.cn/r/3n6bl5b（土豆公益账号注册推广链接）。
- 只加了社区站页脚，未改动其它页面。
- 验证：前端 npm run build 通过。
- 提交并推送：48db853。
- 文案修正：实际访问确认 tudouai.cn 是“免费我的世界/七日杀/幻兽帕鲁/饥荒联机 · 一键开服”的游戏联机平台，不是公益慈善。徽章主文案已改为“免费我的世界/七日杀/幻兽帕鲁联机 / 一键开服”，提交推送 9f2a963。

### 2026-10-07 — 监控准确性与许可证澄清

- 修改 `orange-worker/src/index.ts`：给监控接口增加实际 HTTP 探测；探测失败和 D1 统计失败如实报告警告/无法获取。
- 修改 `cloudflare-monitor/app.js`：实时接口失败时显示未知，不再读取旧快照伪装实时状态。
- 新增 `LICENSE`，并修改根目录中英文 README：采用非商业使用许可，商业用途须事先书面授权。
- 验证：Worker `npm run typecheck`、监控 JS `node --check`、前端 `npm run build` 均通过。
- 提交并推送：`b9af95e`。
