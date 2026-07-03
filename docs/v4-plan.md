# v4 Plan — Adapt to the July 2026 Rewards redesign

> Status: **Phase 2 complete, Phase 3 next**. Lives on branch `feat/rewards-redesign-v4`
> (target version `4.0.0`). This document is the source of truth for the rewrite; update
> it as recon findings land and decisions are made.

## Background

In July 2026 Microsoft rolled out a major redesign of the Rewards experience. Observed and
suspected effects:

- The Rewards page is now a **Next.js App Router application** (v16.2.6, deployed
  2026-07-01) using React Server Components. Confirmed by Phase 2 recon.
  The existing Selenium selectors are ineffective. The new URL is
  `https://rewards.bing.com/dashboard` (both `rewards.bing.com/` and
  `rewards.microsoft.com/` redirect there).
- **Points earnable per day appear reduced** — a Microsoft policy change, not a bug on our
  side. No engineering fix; document expectations only.
- **Mobile search points appear to no longer be collectable** via browser automation.

### Why *everything* broke at once (root cause)

The entire data model of the current tool flows through a single line:

- `src/utils.py:290` — `getDashboardData()` does `execute_script("return dashboard")`,
  reading a global `dashboard` JavaScript object off `rewards.bing.com`.

`getAccountPoints`, `getRemainingSearches`, activity enumeration, punch cards, and bonus
points are all built on that scraped global. **Phase 2 confirms `window.dashboard` no
longer exists** — the new Next.js App Router page does not expose it, which is why every
feature failed simultaneously rather than selectors degrading incrementally.

### Validated facts (from the current codebase)

- **Mobile Read-to-Earn is pure API** (`src/readToEarn.py`): OAuth2 token via
  `login.live.com/oauth20_authorize.srf`, then `POST` to
  `prod.rewardsplatform.microsoft.com/dapi/me/activities`. The webdriver is used **only** to
  complete the OAuth redirect and capture the `code=`; it never touches the Rewards SPA. This
  survives the redesign as long as the classic MS auth flow does.
- **Mobile searches are browser-driven** (`src/searches.py`): `sb_form_q` searchbar +
  `submit()`, gated by `browserType == "mobile"` (resolution/UA spoofing in `src/browser.py`).
  This is the Selenium-interaction path that is now uncounted.

## Guiding principle

Prefer **API-driven** over **DOM-driven** wherever the new SPA allows it. The browser becomes
an *auth + interaction* tool (login, actual Bing searches, quiz/activity iframes), not the
primary data source. This is what makes us resilient to the *next* redesign, not just this one.

> **Open question, not a conclusion.** The `dapi/me/*` endpoints that Read-to-Earn uses are a
> *candidate* backend for the new SPA, not a foregone answer. Large orgs do not always make
> clean choices. Recon must distinguish between at least:
> - (a) the same `dapi` REST API also backs the new web dashboard;
> - (b) the React app uses a **brand-new** API / GraphQL / BFF;
> - (c) the old API is kept **only for mobile** while web moved to something else.
>
> We map what is actually there before betting the data layer on any one of these.

## Phase 0 — Branch & scaffolding  ✅

- [x] Cut `feat/rewards-redesign-v4` (major version → `4.0.0-dev`).
- [x] Land this planning doc so intent is tracked.

## Phase 1 — Debug / recon tooling *first* (the enabler)

Build a small, permanent **page-recon harness**, runnable from the terminal, *before* touching
automation logic. It is CLI-first; the Chrome/Claude browser integration is used only where a
terminal-only path cannot capture visual state (screenshots, rendered layout).

Requirements:

- **Owns the login flow.** It must not assume an authenticated session — it drives login
  (credentials + TOTP) and reaches the logged-in Rewards dashboard on its own. This makes the
  recon harness the natural proving ground for the login state-machine refactor (see Phase 3).
- **Captures, for a logged-in session:** DOM dump, screenshot, detected framework
  (React + version), relevant `window` globals, and **network requests** — with special
  attention to any `dapi/me/*` or new-era API/GraphQL calls the SPA fires.
- **Packaged as a repo command + skill** (e.g. `uv run python -m src.recon` and a `/recon`
  skill) so future breakages are diagnosable in one command instead of manual visible-mode
  repro.
- Reuses the `DebugRecorder` / evidence-bundle design already specified in
  [ROADMAP.md](../ROADMAP.md) (login refactor) — same machinery, broader target.
- **Security:** never persist passwords, TOTP secrets, computed OTPs, JWTs, or auth cookie
  values; redact per the ROADMAP security constraints. Evidence dir gitignored.

## Phase 2 — Recon & the framework decision  ✅

Using the Phase 1 tooling on a real logged-in account. Evidence captured in
`logs/recon/20260703T114117Z/` (gitignored).

### Findings

**1. Framework confirmed — Next.js App Router, not a plain React SPA**

The recon fingerprinter detected `window.next` and `__NEXT_DATA__`. Build tag
`dpl=20260701-3` (deployed 2026-07-01). The app uses **React Server Components (RSC)**
with streaming via `self.__next_f.push([1, "..."])` inline scripts injected into the
initial HTML. There is no separate client-side data fetch for the dashboard — all
structured data arrives in the first SSR response.

**2. What backs the dashboard — hypothesis (c) confirmed**

> The old `dapi` API is kept **only for mobile** (Read-to-Earn). The web dashboard moved
> to RSC streaming — the server embeds all data in the page HTML.

No `fetch()` calls for dashboard data were found in the inline scripts. No `/api/`
internal routes or external API calls appear in the network log for dashboard load.
All three critical data objects are embedded directly in the RSC payload:

| Data | RSC script | Key shape |
|------|-----------|-----------|
| Point balance + level | Script 42 | `{"balance": 10699, "level": 3}` |
| Activity counters | Script 58 | `{"activitiesProgress": 0, "activitiesRemaining": 2, "activitiesRequirement": 2, "blendedRatio": 0.586}` |
| Daily set items | Script 38 | Array of `{offerId, points, isCompleted, destination, title, description, date, imageUrl, isLocked, unlockCriteria}` |

The `destination` field on each `dailySetItem` is a direct URL (e.g. a Bing search URL)
that completes the activity. This means we can navigate directly to the destination
instead of clicking activity cards in the DOM.

**3. Search counters — not yet located**

`pcSearch`, `mobileSearch`, `pointProgressMax`, and `pointProgress` keys were *not*
found in the captured page source. These counters are either in a lazily-loaded RSC
component, behind a separate route (e.g. `/pointsbreakdown`), or require a search
action to trigger. This is the main unknown heading into Phase 3.

**4. Mobile search death — unverified (but expected)**

Not directly probed in this recon session. Mobile searches use a separate browser
context (`browserType == "mobile"` with resolution/UA spoofing). The Bing search
submission mechanic (`sb_form_q` + `submit()`) likely still works — the break is that
the new dashboard no longer reports mobile search progress. Gated behind `search.mobile`
flag defaulting off per the Phase 3 plan.

**5. Read-to-Earn OAuth flow — assumed intact**

The Read-to-Earn path uses `login.live.com → prod.rewardsplatform.microsoft.com/dapi/me/activities`.
This API endpoint is independent of the web dashboard redesign. No recon evidence
contradicts it. Consider adding a `/recon --mode read-to-earn` probe in a future
harness iteration.

### Framework decision — Keep Selenium / undetected-chromedriver

The new data model changes the calculus:

- Dashboard data extraction is now **HTML parsing** of the `page_source` — not DOM
  traversal and not `execute_script`. Selenium's weakness (poor auto-waiting for SPA
  mutations) is irrelevant for the read path.
- Activity completion is **direct URL navigation** to `destination` values embedded in
  the RSC payload — no complex DOM interaction required for the happy path.
- The login flow and UC are both working. Adding Playwright migration risk on top of
  a data-layer rewrite is scope creep.
- `selenium-wire` can still be dropped (see Phase 4) without switching frameworks.

**Decision: keep `undetected-chromedriver` + Selenium for Phase 3.** Playwright
remains an option for a future Phase 5 if stealth or await ergonomics become a
blocking issue.

## Phase 3 — Core rewrite (on the branch)

- **Data layer:** built on whatever Phase 2 establishes as the real backend; collapse the dead
  `PREFER_BING_INFO` dual-path in the process (ROADMAP debt).
- **Interaction layer:** re-implement search + activities + punch cards + bonus points against
  the new page on the chosen framework.
- **Login:** implement the ROADMAP login state-machine refactor here (page descriptors, typed
  errors, `DebugRecorder`, scripted-driver tests). The new page brings new variants regardless,
  and the recon harness already exercises this flow.
- **Mobile split:**
  - Mobile **Read-to-Earn**: keep enabled (API/OAuth, unaffected by the web redesign).
  - Mobile **searches**: keep the code, gate behind a `search.mobile` feature flag defaulting
    **off**, documented as "MS stopped counting these as of July 2026". Microsoft has not yet
    redesigned the mobile app, so this may return — the flag makes re-enabling trivial.

## Phase 4 — Cleanup folded in (ROADMAP debt)

Since the tree is already churning:

- Drop `selenium-wire` → unpin `setuptools<81`; drop `pyautogui` if unused; drop
  `undetected-chromedriver` if we adopt Playwright.
- Ruff + pre-commit + minimal CI (lint / format / tests).
- Docs: flip the README warning to "v4 in progress", add a `4.0.0` CHANGELOG entry, and
  document the new architecture + recon runbook under `docs/`.

## Non-goals / accept-and-document

- **Reduced points-per-day** is a Microsoft policy change — no engineering fix; set
  expectations in the README.
