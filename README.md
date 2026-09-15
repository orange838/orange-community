# CSL Personal Blog - Orange Community

Welcome to the **Orange Community** repository, the codebase for CSL's personal blog and community platform.

## Overview

Orange Community combines technical articles, personal notes, and community features in a separated frontend and backend architecture.

## Technology

- Frontend: Vue.js
- API: Cloudflare Workers with TypeScript
- Database: Cloudflare D1
- Compatibility backend: Python FastAPI and SQLite
- Monitoring dashboard: static HTML, CSS, and JavaScript

## Main directories

- [`orange-frontend/`](./orange-frontend/) - Vue frontend
- [`orange-worker/`](./orange-worker/) - Worker API and D1 integration
- [`orange-backend/`](./orange-backend/) - compatibility backend
- [`cloudflare-monitor/`](./cloudflare-monitor/) - project monitoring dashboard

## Monitoring dashboard

The monitoring dashboard summarizes the project's service status, including API health, Pages domains, D1 usage, HTTPS status, Git information, and Turnstile verification metrics.

The dashboard documentation is available in [`cloudflare-monitor/README.zh_CN.md`](./cloudflare-monitor/README.zh_CN.md).

## Contributing

This is a personal project. Suggestions and issue reports are welcome.
