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

This project is licensed under the **Orange Community License**: the
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)
(verbatim) plus additional permissions and an attribution requirement, set out in
[`LICENSE`](./LICENSE). It is a source-available (fair source) license, not an
OSI-approved open-source license.

- **Non-commercial use** — free to use, run, modify and distribute, including
  modified versions, with **no obligation to publish your changes**.
- **Commercial use** — two options: **(a)** publish your modified source under the
  same license, or **(b)** obtain a written commercial license. Only a written
  commercial license may allow removing the attribution.
- **Attribution is mandatory** — keep the copyright notice and the visible
  "Powered by Orange Community" credit described in [`NOTICE`](./NOTICE).
- **Organizations** — schools, charities and government bodies are **not** granted
  blanket permission; what counts is the actual purpose of use.

Commercial licensing: admin@cslblog.dpdns.org
