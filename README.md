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

## License & Commercial Use

This project is licensed under the **GNU General Public License v3.0**.

- **Open Source:** You are free to use, modify, and distribute this software for personal or non-commercial purposes, provided that you adhere to the terms of the GPLv3 (e.g., open-sourcing your modifications).
- **Commercial Use:** If you wish to use this software for commercial purposes, closed-source modification, or private deployment without open-sourcing your code, please contact the author for a commercial license.

📧 **Contact for Commercial Licensing:** 3659793158@qq.com
