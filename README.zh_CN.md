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
