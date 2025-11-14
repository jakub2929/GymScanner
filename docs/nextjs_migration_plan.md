# Next.js + TypeScript Migration Plan

## 1. Why migrate?
- **Consistent UI stack** – React/Next.js enables component reuse, routing, and form state instead of hand-maintained static HTML.
- **Type safety** – TypeScript for API contracts (zabrání chybám ve fetch + responses).
- **Modern build pipeline** – Tailwind/PostCSS integrated, SSR/ISR available for authenticated pages, easier to deploy on Vercel/Render.
- **DX** – Hot reload, ESLint, Prettier, Storybook options.

## 2. Recommended stack snapshot
| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | **Next.js 14 (App Router)** | Hybrid SSR/CSR, file-based routing, built-in bundler (Turbopack / Webpack) and image/font optimizations. |
| Language | **TypeScript** | Static typing across API DTOs, form state, and service hooks. |
| UI | **React 18** | Component ecosystem, concurrent features, integrates with Next.js seamlessly. |
| Styling | **Tailwind CSS w/ PostCSS** | Utility-first styling + custom tokens for liquid glass themes. |
| Data fetching | **TanStack Query (React Query)** | Request caching, retries, loading/error states for `/api/**` endpoints. |
| Forms | **React Hook Form** | Lightweight form state for login/register/settings. |
| Charts (if needed) | Recharts/Nivo (opt-in) | Future metrics (usage, credits). |
| Scanner | `react-html5-qrcode` or custom hook | Wraps camera access in React-friendly API. |
| Auth storage | `sessionStorage` or HTTP-only cookie | Avoids XSS risk; easy to share between pages. |
| Lint/Format | ESLint + Prettier + Husky | Enforces consistent code style. |

Backend (FastAPI) remains – only minimal adjustments (CORS, static file mount removal).

## 3. Work packages & estimates
1. **Setup / Tooling (1 day)**
   - `npx create-next-app@latest frontend --ts --tailwind`.
   - Configure path aliases, Prettier, ESLint, Husky.
   - Define shared `apiClient` wrapper w/ interceptors and typed responses.
2. **Auth + Layout (2 days)**
   - Build `app/(auth)/page.tsx` with login/register forms, replicating Apple glass style.
   - Implement context/state for token management (store in memory + cookies if needed).
   - Navigation shell (Dashboard, Settings, Scanner, Admin).
3. **Dashboard & Settings (2 days)**
   - Componentize QR card, entries CTA, toast, modals.
   - Settings page with forms (change password, account info).
4. **Scanner page (1.5 days)**
   - Wrap QR scanner library, manual token entry, status messaging.
5. **Admin pages (1.5 days)**
   - Admin login, list/search users, update credits, tokens table.
6. **Integration + polish (1.5 days)**
   - Wire typed fetchers to all endpoints, handle errors globally.
   - QA on desktop/mobile, adjust theming tokens, update README/deploy docs.

**Total:** ~9 calendar days (1–2 people). Add buffer for acceptance/iterations.

## 4. Migration strategy
1. **Parallel frontend** – keep FastAPI running on `localhost:8000`, serve Next.js dev server on `localhost:3000`. Configure proxy for API requests.
2. **Gradual switch** – once pages are ready, update FastAPI to serve `frontend/out` (Next.js static export) or deploy separately behind reverse proxy.
3. **Routing alignment** – maintain same paths (`/dashboard`, `/settings`, `/scanner`, etc.) for seamless backend compatibility.
4. **Token handling** – continue using JWT from FastAPI; store in secure cookie or `sessionStorage`. Refresh logic can remain manual (no refresh tokens yet).

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

Once this plan is approved, next branch will bootstrap the Next.js project (Phase 1) and migrate the login flow as a proof of concept before rest of pages.
