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

The dashboard documentation is available in [`cloudflare-monitor/README.md`](./cloudflare-monitor/README.md).

## Contributing

This is a personal project. Suggestions and issue reports are welcome.

---

## License

This project is licensed under the **Orange Community Non-Commercial License** in [`LICENSE`](./LICENSE). It permits personal, educational, research, and other non-commercial use. Commercial use requires prior written authorization from the copyright holder. This is a custom source-available license, not GPLv3 or an OSI-approved open-source license. Distribution of modified versions also requires prior written permission.

See the license file for the complete terms. Contact the author for commercial licensing at 3659793158@qq.com.

---

> Built by CSL with the assistance of AI（由 CSL 在 AI 辅助下构建）
