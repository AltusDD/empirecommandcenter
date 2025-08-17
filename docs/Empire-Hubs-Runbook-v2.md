# Empire Command Center — Hubs v2.0 Master Runbook

> **Purpose**\
> Single source of truth capturing decisions, standards, contracts, and guardrails for the ECC “Entity Hubs” (Property, Unit, Lease, Tenant, Owner). Hand this file to any tool/agent/new chat to restore full context and continue execution without drift.

---

## 0) Executive Summary

- We replaced ad‑hoc pages with a **universal Card Shell** and strict **Information Hierarchy**: **Owner → Property → Unit → Lease → Tenant**.
- We established a **high‑contrast Altus theme** and **3‑column command layout** (Left Rail, Center Content, Right Rail) and added **automated no‑drift gates** (Storybook + Playwright + lint/format hooks) that fail builds on visual or contract regressions.
- We upgraded the Property Hub to **boardroom‑grade KPIs** with sparklines, contextual sublines, and a map‑anchored hero; moved actions to the **Left Rail**, and reserved the **Right Rail** for **Insights & Activity**.
- We defined **RPC data contracts**, **API proxy endpoints**, and **frontend hooks** so each hub loads with one optimized request.

---

## 1) Accomplishments to Date (✓)

- **IA & Navigation**
  - Portfolio Hubs: `/portfolio/{properties|units|leases|tenants|owners}` (V3 tables) with drill‑downs into card pages.
  - Entity Hubs: `/card/{entity}/{id}` (Property, Unit, Lease, Tenant, Owner).
- **Design System**
  - Tokenized, high‑contrast Altus theme (gold/black) and global CSS variables.
  - Sidebar color and active state restored to brand (and locked via tests).
  - Panel/typography/badge/button patterns unified.
- **Universal Card Shell**
  - Grid: `grid-template-columns: 320px 1fr 300px` with `gap: 24px;`
  - **Left Rail**: Identity + Primary Actions
  - **Center**: Hero (name/address/map/owner link), Tabs, KPI Row
  - **Right Rail**: Insights (flags/recommendations) & Activity (event feed)
- **Property Hub (Overview)**
  - Hero with map (click → Google Maps), owner badge → Owner Hub, unit count, DL open link.
  - KPI row (Occupancy, Collected 30d, AR/Delinquency, NOI) with **sparklines** + **two sublines** for context.
  - Actions consolidated to **Left Rail**; Right Rail reserved for intelligence.
  - Layout tightening so all cards fit within container.
- **No‑Drift Guardrails**
  - Storybook for component isolation (KPIHeader etc.).
  - Playwright E2E: Architecture (3‑col present), Theming (sidebar brand), KPI integrity (sparklines + sublines).
  - Husky + lint‑staged + eslint/stylelint + `check:ui` script.
  - Git tagging/reset protocol for quick rollback when drift occurs.

---

## 2) Theme & Tokens (Authoritative)

```css
:root {
  /* Brand */
  --gold: #F7C948;            /* primary accent */
  --success: #32D296;         /* green */
  --danger:  #E5484D;         /* red */

  /* Surfaces */
  --bg:      #0A0A0A;         /* true black */
  --surface: #141414;         /* off‑black (sidebar/panels) */
  --panel:   #141414;         /* widget background */
  --border-1:#2C2C2C;         /* separators */

  /* Type */
  --fg: #FFFFFF;              /* primary text */
  --muted-1:#C2C2C2;
  --muted-2:#9AA0A6;

  /* Sidebar (locked by tests) */
  --nav-bg: var(--surface);
  --nav-fg: var(--fg);
  --nav-active: var(--gold);
  --nav-hover: color-mix(in srgb, var(--gold) 30%, var(--fg));
}
```

**Rules**

- No raw hex in components; **tokens only**.
- High contrast: text always `--fg` or `--muted-*` on `--panel`.
- Use thin borders (`--border-1`) and subtle gold accents on hover/focus.

---

## 3) Universal Card Shell

```css
.card-shell { display:grid; grid-template-columns:320px 1fr 300px; gap:24px; max-width:1720px; margin:0 auto; padding:8px 0 24px; }
.panel { background:var(--panel); border:1px solid var(--border-1); border-radius:14px; }
.center-wrap { display:grid; gap:16px; }
.kpi-row { display:grid; grid-template-columns:repeat(4, minmax(220px,1fr)); gap:12px; }
```

- **Left Rail**: identity/title block, owner & lineage breadcrumbs, **primary actions** (+ Work Order, + Task, Contact).
- **Center**: `Hero` (name, full address, badges, map), `Tabs` (Overview, Financials, Units, Work, Files, Comms, …), KPI row.
- **Right Rail**: **Insights** (flags, recommendations) & **Activity** (recent events). No actions here.

---

## 4) KPI System (with Sparklines)

**Component contract**

```ts
interface KPIProps { label:string; value:string; sublines:[string,string]; trend:number[]; }
```

- Each KPI renders: **label**, **value**, **sparkline (90d)**, and **two sublines** (e.g., “98% of GPR”, “▲$1.2k vs LM”).
- Sparkline is pure SVG (no heavy chart lib) for crisp, fast visuals.

**Example placement**

```tsx
<KPI label="Occupancy" value={`${k.occ.toFixed(1)}%`} sublines={[`Units: ${k.occ_units}/${k.total_units}`, `▲ ${k.delta_occ_pp} pp vs prior`]} trend={k.occ_90d}/>
```

**Playwright lock**

- Assert 4 KPIs, each with an SVG sparkline and 2 sublines.

---

## 5) Hero with Map & Badges

- Title → property name (H3 weight)
- Subtitle → **Street, City, State, Zip** (always all 5 fields)
- Badges: Profile (e.g., Residential Single Family), **Owner → Owner Hub**, **N Units → Units table**, **Open DL**
- Map thumbnail aligned right; click opens Google Maps with full address query.

---

## 6) Right Rail Intelligence

- **Insights**: array of `{severity:'info'|'warn'|'risk', title, detail, link?}`
- **Activity**: array of `{id, when, label, href}`
- No quick actions; actions live in **Left Rail** only.

---

## 7) Backend Contracts (Phase 1)

> Read‑only RPCs queried by the UI (one call per hub) via server proxy.

**RPC functions (Supabase)**

- `get_property_dashboard(id bigint)`\
  Returns: `{ anchor, owner, kpis, insights[], activity_stream[], rent_roll_slice[], ar_aging{}, cashflow_12m[] }`
- `get_unit_dashboard(id bigint)`\
  Returns: `{ anchor, property, active_lease, tenant, unit_specs, maintenance_history[], media[] }`
- `get_lease_dashboard(id bigint)`\
  Returns: `{ anchor, status, key_dates, rent_terms, balance, ledger[], documents[], servicing_log[] }`
- `get_tenant_dashboard(id bigint)`\
  Returns: `{ anchor, contacts[], active_lease, communications[], payments[], documents[], history[] }`
- `get_owner_dashboard(id bigint)`\
  Returns: `{ anchor, kpis, properties[], documents[], communications[] }`

**Rules**

- **security invoker** for reads → RLS enforced.
- Heavy rollups backed by **materialized views** (nightly/HOURLY refresh).
- All writes go through server endpoints with auth, authz, and audit events.

---

## 8) API Layer (Phase 2)

Azure Functions (or Node server) exposes **read‑only RPC proxies**:

```
GET /api/rpc/get_property_dashboard?id={id}
GET /api/rpc/get_unit_dashboard?id={id}
GET /api/rpc/get_lease_dashboard?id={id}
GET /api/rpc/get_tenant_dashboard?id={id}
GET /api/rpc/get_owner_dashboard?id={id}
```

- Validate `id`, forward to Supabase, return JSON (no massaging besides camelCase).
- Cache micro‑TTL (e.g., 15–60s) per entity for snappy UI.

---

## 9) Frontend Data Hooks (Phase 3)

```ts
// usePropertyDashboard.ts
export function usePropertyDashboard(id:number){
  return useSWR(id? `/api/rpc/get_property_dashboard?id=${id}` : null, fetcher, { revalidateOnFocus:false });
}
```

- Unit/Lease/Tenant/Owner mirrors of the above.
- Each hub page performs a **single hook call** to render the Overview.

---

## 10) Guardrails & Tooling (Phase 4)

- **Storybook** for component contracts (KPIHeader, Hero, RightRail).
- **Playwright** E2E:
  1. `architecture.spec` → `.left-rail`, `.main-col`, `.right-rail` visible.
  2. `theming-sidebar.spec` → sidebar bg + active gold.
  3. `kpi-property.spec` → 4 KPIs, sparklines, sublines.
- **Husky + lint‑staged**: run `eslint`, `stylelint`, `prettier`, `check:ui`.
- **CI** runs: build → Playwright → deploy (fails on any test error).

---

## 11) Performance

- **Materialized views** for rollups (NOI, AR aging, occupancy) refreshed nightly/hourly.
- **Keyset pagination** for large tables (cursor‑based).
- **Virtualized grids** (TanStack Virtual/MUI X) for portfolio hubs.

---

## 12) Security & Audit

- RLS reads via `security invoker` RPCs + `property_staff_assignments` model.
- All writes via server endpoints using service role key + JWT user, with **audit_events** insert on every mutation.

---

## 13) File/Folder Map (frontend)

```
src/
  components/
    kpi/ KPI.tsx KPIHeader.tsx kpi.css
    charts/ Spark.tsx
  pages/
    card/
      property/[id]/ Hero.tsx hero.css Overview.tsx
      unit/[id]/      Overview.tsx
      lease/[id]/     Overview.tsx
      tenant/[id]/    Overview.tsx
      owner/[id]/     Overview.tsx
  layout/ Sidebar.tsx Sidebar.css CardShell.css
  styles/ theme.css elevations.css
  hooks/  usePropertyDashboard.ts useUnitDashboard.ts ...
```

---

## 14) Acceptance Checklists

**Global (every hub)**

-

**Property Hub (Overview)**

-

**Unit Hub (Overview)**

-

**Lease Hub (Workspace)**

-

**Tenant Hub (Relationship)**

-

**Owner Hub (Investor)**

-

---

## 15) Current Punch List (Final A++)

-

---

## 16) Dev Commands

```bash
# Tooling
npm i -D @storybook/react-vite @storybook/react playwright husky lint-staged eslint stylelint prettier
npx storybook@latest init
npx playwright install

# Tests
npm run test:e2e            # playwright
npm run check:ui            # eslint+stylelint+prettier+e2e (gate)

# Snapshots (first time)
npx playwright test --update-snapshots
```

---

## 17) Rollback Protocol

```bash
git tag safepoint/PROPERTIES_V3_OK
# ... if drift happens
git reset --hard safepoint/PROPERTIES_V3_OK
```

---

## 18) Notes for Replit Agent

- Do **not** touch Sidebar nav classes or theme tokens.
- Do **not** insert mock literals in JSX; all values come from the RPC hooks.
- Do **not** place actions in the Right Rail.
- Do **not** change grid columns of Card Shell.
- A PR is **not complete** until `check:ui` passes in CI.

---

## 19) Appendix: Example JSON Shapes (abridged)

```json
// get_property_dashboard
{
  "anchor": {"id": 42, "name": "127 Francis Drive", "address1": "127 Francis Dr", "city":"Macon", "state":"GA", "zip":"31216", "profile":"Residential Single Family", "unit_count": 1, "doorloop_id":"..."},
  "owner": {"id": 7, "name":"Empire Holdings LLC"},
  "kpis": {
    "total_units": 1,
    "occ_units": 1, "occupancy_pct": 96.2, "delta_occ_pp": 1.2, "occ_90d": [92,93,94,96,96.2],
    "collected_30d": 18159, "collected_pct_of_gpr": 98, "last_payment": 205, "collected_90d":[...],
    "ar_total": 19218, "ar_30p": 1200, "delta_ar_vs_lm": -1200, "ar_90d":[...],
    "noi_mtd": 22150, "noi_vs_budget": 105, "noi_delta_lm": -500, "noi_90d":[...]
  },
  "insights": [{"severity":"warn","title":"Property insurance not on file","detail":"Upload policy","link":"/files"}],
  "activity_stream": [{"id":"a1","when":"2h","label":"Payment received $205","href":"/card/lease/55#txn"}]
}
```

---

## 20) Ownership & Next Steps

- This runbook is the **authoritative contract**.
- Replicate the **Property Hub** blueprint to **Unit, Lease, Tenant, Owner** using the same Card Shell and guardrails.
- Keep this file updated after each milestone; tag a git safepoint at every green build.
