# 橙子社区 Cloudflare 监控看板

这个目录是橙子社区的独立 Cloudflare 监控看板，部署后使用以下子域名：

```text
https://dash.cslblog.dpdns.org
```

## 看板内容

看板用于汇总当前项目在 Cloudflare 上的运行状态，包括：

- Pages 项目和域名
- Worker API 健康状态
- D1 数据库大小、读写查询量和行数统计
- HTTPS / DNS 状态
- Git 提交和部署分支
- Turnstile 人机验证通过次数、失败次数和通过率

看板不会展示 Cloudflare API Token、Worker Secret、Resend API Key 或其他密钥。
Cloudflare Account ID 也不写入公开看板。

## 本地运行

在项目根目录执行：

```powershell
cd "D:\csl\个人项目\橙子社区\cloudflare-monitor"
node .\scripts\gather-cf-status.mjs
python -m http.server 8080
```

然后打开：

```text
http://localhost:8080
```

`gather-cf-status.mjs` 会执行 Wrangler、Git 和 HTTPS 健康检查，并把结果写入：

```text
data/cf-status.json
```

## GitHub 自动部署

监控看板使用独立的 Cloudflare Pages 项目：

```text
orange-community-monitor
```

Pages 项目应连接 GitHub 仓库：

```text
orange838/orange-community
```

配置如下：

| 配置项 | 值 |
| --- | --- |
| 生产分支 | `main` |
| 框架预设 | 无 |
| 构建命令 | 留空 |
| 构建输出目录 | `.` |
| 根目录 | `cloudflare-monitor` |
| 自定义域名 | `dash.cslblog.dpdns.org` |

这是纯静态页面，不需要 `npm run build`，也不要使用手动
`wrangler pages deploy`。以后只要推送 `main` 分支，Cloudflare Pages 就会自动重新部署。

## Turnstile 统计

生产 Worker 会把登录和注册的人机验证结果写入 D1 表：

```text
turnstile_verification_logs
```

记录只包含验证动作、是否通过、验证主机名和时间，不保存 Turnstile Token。
监控脚本按最近 24 小时汇总通过次数、失败次数和通过率。

## 注意事项

- 不要把 `.env`、API Token、Secret 或本地数据库导出文件提交到 Git。
- 修改 Worker 后，先执行 `npm run typecheck`。
- 修改监控页面后，提交并推送到 `main`，不要覆盖现有的 `orange-community` 主站 Pages 项目。
