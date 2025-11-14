# Next.js + TypeScript Migration Plan

## 1. Why migrate?
- **Consistent UI stack** – React/Next.js enables component reuse, routing, and form state instead of hand-maintained static HTML.
- **Type safety** – TypeScript for API contracts (zabrání chybám ve fetch + responses).
- **Modern build pipeline** – Tailwind/PostCSS integrated, SSR/ISR available for authenticated pages, easier to deploy on Vercel/Render.
- **DX** – Hot reload, ESLint, Prettier, Storybook options.

## 2. Stack (2025 best-practice)
| Category | Tech Used | Notes |
|----------|-----------|-------|
| Runtime | **Next.js 14 (App Router) + React 18** | App directory, server & client components, Turbopack dev server. |
| Language | **TypeScript** (strict mode) | Shared types for API requests/responses (`zod` for validation). |
| Styling | **Tailwind CSS 3 + PostCSS** | Custom theme tokens (`tailwind.config.js`) for liquid glass palette. |
| State & fetching | **TanStack Query** + custom fetch wrapper | Handles JWT header injection, caching, optimistic updates. |
| Forms | **React Hook Form + Zod Resolver** | Login/register/settings forms with validation. |
| Scanner | **react-html5-qrcode** | React-friendly QR/UPC scanning component. |
| Icons/Typography | **Radix UI Icons + SF Pro** | Consistent design system. |
| Build tooling | ESLint (Next.js config) + Prettier + Husky | Lint/format on commit (`lint-staged`). |
| Testing | Vitest + React Testing Library (smoke tests) | Optional for key components. |
| Auth storage | In-memory + `sessionStorage`, optional secure cookie | No localStorage usage for tokens. |

Backend (FastAPI) remains – only minimal adjustments (CORS, static file mount removal).

## 3. Work packages & timeline (concrete)
| Phase | Deliverables | Duration |
|-------|--------------|----------|
| **A. Bootstrap (Next.js + tooling)** | ✅ `frontend/` vytvořeno (`create-next-app --ts --tailwind`), Tailwind config + ESLint/Prettier/Husky, `apiClient`, `.env`. | 1 day |
| **B. Auth shell** | ✅ `/login` a `/register` (Hook Form + Zod), token handling, shared layout/navigation. | 2 days |
| **C. Dashboard + Settings** | ✅ Replika Apple glass dashboard + Settings (datasource TanStack Query, nákup vstupů, změna hesla). | 2 days |
| **D. Scanner** | ✅ `/scanner` route (Html5-qrcode wrapper) s manuálním zadáním a status messagingem. | 1.5 days |
| **E. Admin** | ✅ `/admin/login` + guard, `/admin` metrics overview, `/admin/users` search + credit adjustments, `/admin/tokens` activation controls. | 1.5 days |
| **F. Integration & docs** | 🚧 Cross-page QA, responsive fixes, README/DEPLOY updates, Docker/Coolify instructions for dual services. | 1.5 days |

**Total:** ~9.5 days (1–2 devs). Buffer recommended for review cycles.

## 4. Migration strategy
1. **Parallel dev servers** – FastAPI (`:8000`) + Next dev server (`:3000`) with `/api` proxy (Next middleware rewrites to FastAPI). 
2. **Feature parity** – replace one page at a time (Auth → Dashboard → Settings → Scanner → Admin) while keeping old static pages as fallback.
3. **Deployment** – Once stable, build Next.js (`npm run build && next export` or SSR mode). Option A: serve static export via FastAPI `StaticFiles`. Option B: deploy as separate service (Coolify) and point DNS accordingly.
4. **Token handling** – Continue using FastAPI JWT; on login store token in memory + `sessionStorage`, attach via `apiClient` interceptor. Later optional: HTTP-only cookie via FastAPI response.

## 5. Deliverables
- `frontend/` Next.js project (TypeScript, Tailwind).
- Updated `README.md` with dev instructions (`npm install`, `npm run dev`, `npm run build`).
- Updated Docker/Coolify instructions (backend + frontend services).
- Legacy `static/` folder deprecated once new UI is live.

## 6. Risks / mitigations
| Risk | Mitigation |
|------|------------|
| Increased bundle size | Use dynamic imports for scanner, tree-shake unused libs. |
| Auth token leakage | Store JWT only in memory or `sessionStorage`, disable SSR for protected pages or implement server middleware verifying cookies. |
| Timeline slip | Deliver in phases (Auth + Dashboard first) to unblock stakeholders. |

## Phase E recap (done)
- Created dedicated admin route group (`/admin/login`, `/admin`, `/admin/users`, `/admin/tokens`) in Next.js with liquid-glass styling.
- Shared session-aware guard verifies `is_admin` via FastAPI and redirects unauthorized users.
- Admin dashboard aggregates user/token metrics, shows latest signups, and visualizes token activity.
- User management table supports live search + credit adjustments with optimistic feedback; token table toggles activation and filters status.

## Phase F focus
- Finish documentation refresh (README + DEPLOY) describing dual-service dev flow (FastAPI + Next dev/build) and new admin touchpoints.
- QA responsive breakpoints (mobile nav, tables) and run lint/tests ahead of merge.
- Align docker/coolify configs once frontend deploy target is defined (SSR vs static export) and capture in docs.

Projekt je nyní ve fázi F – po dokončení dokumentace a QA můžeme úplně vypnout původní statické šablony.

**Průběžný stav (F)**
- README doplněno o Next.js dev kroky a odkaz na produkční Dockerfile.
- DEPLOY.md vysvětluje dvouslužbovou architekturu (FastAPI API + Next.js UI) v Coolify a popisuje nově přidaný `frontend/Dockerfile`.
- Další kroky: mobilní QA (App/Scanner/Admin), případné úpravy docker-compose pro lokální SSR build a kontrola, že legacy `/static` stránky lze bezpečně odstranit.
