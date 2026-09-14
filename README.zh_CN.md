# CSL 个人博客 - 橙子社区

欢迎来到 **橙子社区 (Orange Community)** 仓库！本项目是 CSL 个人博客及社区平台的官方代码库。

##  项目简介
本平台旨在打造一个集技术分享、个人随笔与社区互动于一体的现代化空间。项目采用前后端分离架构，旨在提供稳定、高效的社区服务。

## ️ 技术栈
- **生产后端**: Cloudflare Workers（TypeScript）
- **前端**: Vue.js
- **生产数据库**: Cloudflare D1
- **本地兼容后端**: Python FastAPI + SQLite

后端本地启动：

```bash
cd orange-backend
python -m pip install -r requirements.txt
python main.py
```

API 地址默认是 `http://127.0.0.1:3000`，现有前端继续使用原来的 `/api/*` 接口路径。

### 完全部署到 Cloudflare

TypeScript Worker 位于 [`orange-worker/`](./orange-worker/)，使用 Cloudflare
D1，并保持现有 `/api/*` 接口路径。部署前必须先确认远程 D1 中没有需要保留的数据，
或先导出备份；不要直接覆盖远程数据库。

```bash
cd orange-worker
npm install
python scripts/export-local-db.py
npx wrangler d1 execute orange-community --remote --file=./schema.sql
npx wrangler d1 execute orange-community --remote --file=./local-d1-data.sql
npx wrangler secret put CF_TURNSTILE_SECRET_KEY
npx wrangler secret put RESEND_API_KEY
npm run deploy
```

`local-d1-data.sql` 包含密码哈希，只能在本地临时生成和使用，不能提交到 Git。

生产 Worker 已连接到 Cloudflare Workers Builds。仓库的 `main` 分支推送会自动构建
并部署 `orange-worker/`，构建命令为 `npm install && npm run typecheck`，部署命令为
`npx wrangler deploy`。修改 Worker 后只需提交并推送代码，不需要再手动执行部署命令。

前端需要部署到 Cloudflare Pages，构建目录为 `orange-frontend`，构建命令为
`npm run build`，输出目录为 `dist`。Pages 的生产环境变量必须设置：

```text
VITE_API_URL=https://你的-Worker-域名
VITE_CF_SITE_KEY=你的-Turnstile-site-key
```

远程 D1 查询、数据迁移和部署需要配置 `CLOUDFLARE_API_TOKEN`；当前本地会话没有该
令牌，因此不会自动执行远程写操作。

##  参与贡献
这是一个个人项目，但非常欢迎大家提出建议或参与讨论！如有任何想法，请随时提交 Issue。

---
*由 CSL 在 AI 辅助下构建。*
