# CSL Personal Blog - Orange Community

Welcome to the **Orange Community** repository! This project serves as the official codebase for CSL's personal blog and community platform.

##  Overview
This platform is designed to be a dedicated space for sharing technical insights, personal thoughts, and community discussions. It combines a modern blog architecture with an interactive community backend.

## ️ Tech Stack
- **Production backend**: Cloudflare Workers (TypeScript)
- **Frontend**: Vue.js
- **Production database**: Cloudflare D1
- **Local compatibility backend**: Python FastAPI + SQLite

### Run the backend locally

```bash
cd orange-backend
python -m pip install -r requirements.txt
python main.py
```

The API runs at `http://127.0.0.1:3000` by default. The existing frontend
continues to use the `/api/*` routes.

### Full Cloudflare deployment

The TypeScript Worker is in [`orange-worker/`](./orange-worker/). It uses Cloudflare
D1 and keeps the existing `/api/*` route contract. Before deploying, verify that
the remote D1 database is empty or backed up; do not overwrite production data blindly.

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

The generated `local-d1-data.sql` contains password hashes. It is temporary,
must not be committed, and should be removed after migration.

Deploy the frontend to Cloudflare Pages with project directory `orange-frontend`,
build command `npm run build`, and output directory `dist`. Set these production
variables in Pages:

```text
VITE_API_URL=https://your-worker-domain
VITE_CF_SITE_KEY=your-turnstile-site-key
```

Remote D1 inspection, migration, and deployment require `CLOUDFLARE_API_TOKEN`.
The current local session does not have that token, so it cannot perform remote writes.

##  Contributing
This is a personal project, but feedback and discussions are always welcome! Feel free to open an issue if you have any suggestions.

---
*Built with ️ by CSL with AI assistance.*
