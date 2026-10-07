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

本项目采用自定义的 **橙子社区非商业使用许可**，因此不是 GPLv3 或 OSI 定义的开源许可证。

个人、教育、研究等非商业用途可按许可证使用、研究和修改本项目。未经作者事先书面授权，不得将本项目用于商业用途，包括将其集成到收费产品或服务、作为收费托管服务提供，或在营利性组织的业务中使用。修改版本的分发也须事先取得书面许可。

具体范围和条款以 [`LICENSE`](./LICENSE) 为准。商业使用请先联系作者取得书面授权：3659793158@qq.com。

---

> 由 CSL 在 AI 辅助下构建
