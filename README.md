# CSL Personal Blog - Orange Community

<p align="center">
  <a href="./LICENSE"><img alt="License: PolyForm Noncommercial 1.0.0" src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-2f6f4e?style=flat-square&logo=github"></a>
</p>

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

This project is licensed under the **PolyForm Noncommercial License 1.0.0**
([official text](https://polyformproject.org/licenses/noncommercial/1.0.0), reproduced
verbatim in [`LICENSE`](./LICENSE)), plus additional permissions and an attribution
requirement set out in [`NOTICE`](./NOTICE). It is a source-available (fair source)
license, not an OSI-approved open-source license.

`LICENSE` is kept verbatim on purpose: GitHub only recognises the license when the text
is unmodified, so the repository shows "PolyForm Noncommercial License 1.0.0" instead of
"Other". **The additional terms in `NOTICE` are part of the license** — read both.

- **Non-commercial use** — free to use, run, modify and distribute, including modified
  versions, with **no obligation to publish your changes**.
- **Commercial use** — two options: **(a)** publish your modified source under the same
  license, or **(b)** obtain a written commercial license. Only a written commercial
  license may allow removing the attribution.
- **Attribution is mandatory** — keep the copyright notice and the visible
  "Powered by Orange Community" credit described in [`NOTICE`](./NOTICE).
- **Organizations** — schools, charities and government bodies are **not** granted
  blanket permission; what counts is the actual purpose of use.

If you are an individual who modified the project, we would appreciate it if you publish
your changes under the same license — but this is a request, **not** a condition of the
license.

Commercial licensing: admin@cslblog.dpdns.org
