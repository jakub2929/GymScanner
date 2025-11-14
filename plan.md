# Postgres Integration Plan

**Overall progress:** 20%

**Status indicators**
- 🟩 Requirements clarified and repo audited
- 🟨 Compose & env refactor pending
- 🟥 Build + Coolify verification pending

## Step-by-step plan
1. **Dependencies & Dockerfile sanity check** – Confirm `psycopg2-binary` is pinned in `requirements.txt` and that `Dockerfile.production` already runs `pip install -r requirements.txt` so Postgres connectivity works inside the image.  
2. **Environment wiring** – Define definitive defaults for `DATABASE_URL`, `PYTHONUNBUFFERED`, `JWT_SECRET_KEY`, etc., ensuring values are injected via the `web` service `environment:` block while still allowing Coolify overrides.  
3. **Compose refactor** – Expand `docker-compose.yml` to include the FastAPI web container and a new `db` service (`postgres:15-alpine`), wire `depends_on` with a health check, add a named volume for persistence, and remove any reliance on external/internal Coolify DBs.  
4. **Documentation touch-up** – Align `COOLIFY_ENV_VARS.md` (and related quickstart docs if needed) with the new DATABASE_URL + Postgres expectations so deployment operators know which env vars remain configurable.  
5. **Validation tasks (post-implementation)** – Run `docker compose build`, `docker compose up -d`, and `pnpm build` (per repo norms) to ensure both the FastAPI container and PostgreSQL stack come up cleanly under the Coolify-compatible compose.

## Exact file changes required
- `requirements.txt` – Ensure `psycopg2-binary==2.9.9` is present (append if missing); no other dependency drift.  
- `Dockerfile.production` – Confirm/install requirements via `pip install -r requirements.txt` (already present, but verify).  
- `docker-compose.yml` – Replace the single-service definition with the dual-service (web + db) stack including volume + health check + env wiring + depends_on.  
- `COOLIFY_ENV_VARS.md` & `COOLIFY_ENV_VARS_ACTUAL.txt` (if needed) – Document the new DATABASE_URL default and note Coolify overrides.  
- Any other deployment docs referencing SQLite or Coolify’s internal PG should be updated for clarity.

## Final `docker-compose.yml`
```yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.production
    environment:
      PYTHONUNBUFFERED: "1"
      DATABASE_URL: postgresql+psycopg2://gymuser:superheslo@db:5432/gymdb
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:-changeme}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: gymuser
      POSTGRES_PASSWORD: superheslo
      POSTGRES_DB: gymdb
    volumes:
      - gym-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gymuser -d gymdb"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  gym-db-data:
```

## Required environment variables
- `DATABASE_URL` – Defaulted in compose to `postgresql+psycopg2://gymuser:superheslo@db:5432/gymdb`; Coolify can override via secrets if needed.  
- `PYTHONUNBUFFERED` – Set to `1` for deterministic logging.  
- `JWT_SECRET_KEY` – Provide a secure value through Coolify; compose default is a placeholder.  
- (Any existing auth/payment secrets) – Continue injecting through Coolify; verify docs mention they override compose defaults.

## Operator runbook
1. `docker compose build` – Ensure images compile with psycopg2 dependencies.  
2. `docker compose up -d` (or Coolify deploy) – Boot both services; verify `db` volume `gym-db-data` persists.  
3. `pnpm install && pnpm build` – Validate the Tailwind/Next frontend build path per repo norm.  
4. In Coolify, map env/secrets (JWT_SECRET_KEY, etc.) to override compose defaults as required.  
5. Confirm FastAPI logs show successful connection to `postgresql+psycopg2://gymuser@db:5432/gymdb` and tables auto-create on first boot.
