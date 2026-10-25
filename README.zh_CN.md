# CSL 个人博客 - 橙子社区

欢迎来到 **橙子社区** 仓库。本项目是 CSL 个人博客及社区平台的代码库。

## 项目简介

橙子社区集成技术分享、个人随笔和社区互动功能，采用前后端分离架构，提供稳定的社区服务。

## 技术栈

- 前端：Vue.js
- API：Cloudflare Workers（TypeScript）
- 数据库：Cloudflare D1
- 兼容后端：Python FastAPI + SQLite
- 监控看板：HTML、CSS 和 JavaScript

## 主要目录

- [`orange-frontend/`](./orange-frontend/)：Vue 前端
- [`orange-worker/`](./orange-worker/)：Worker API 和 D1 集成
- [`orange-backend/`](./orange-backend/)：兼容后端
- [`cloudflare-monitor/`](./cloudflare-monitor/)：项目监控看板

## 监控看板

监控看板汇总项目服务状态，包括 API 健康状态、站点域名、D1 使用情况、HTTPS 状态、Git 信息和 Turnstile 人机验证统计。

详细说明请查看 [`cloudflare-monitor/README.zh_CN.md`](./cloudflare-monitor/README.zh_CN.md)。

## 参与贡献

这是一个个人项目，欢迎提出建议和提交 Issue。

---

## 许可协议与商业使用

本项目采用 **橙子社区许可（Orange Community License）**：正文为
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) 官方原文，
另附额外许可与署名条款，完整文本见 [`LICENSE`](./LICENSE)。它是「源码可见（fair source）」许可，
不是 GPLv3 或 OSI 定义的开源许可证。

- **非商业用途**：可自由使用、运行、修改、分发（含修改版），**不要求公开你的修改**，也不用付费。
- **商业用途（二选一）**：① 把修改版以相同许可公开；② 取得书面商业授权。只有商业授权才可能允许去除署名。
- **署名必须保留**：版权声明与页脚可见的「Powered by 橙子社区」标注，具体见 [`NOTICE`](./NOTICE)。
- **非商业组织不放行**：学校、公益组织、政府机构不因身份自动获得授权，按**实际用途**判断。

商业授权联系：admin@cslblog.dpdns.org

---

> 由 CSL 在 AI 辅助下构建
