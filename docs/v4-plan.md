# v4 Plan — Adapt to the July 2026 Rewards redesign

> Status: **planning / in progress**. Lives on branch `feat/rewards-redesign-v4`
> (target version `4.0.0`). This document is the source of truth for the rewrite; update
> it as recon findings land and decisions are made.

## Background

In July 2026 Microsoft rolled out a major redesign of the Rewards experience. Observed and
suspected effects:

- The Rewards page is now a **React single-page application** with a substantially different
  DOM. The existing Selenium selectors are ineffective. (Officially unverified that it is
  React — Phase 2 confirms this.)
- **Points earnable per day appear reduced** — a Microsoft policy change, not a bug on our
  side. No engineering fix; document expectations only.
- **Mobile search points appear to no longer be collectable** via browser automation.

### Why *everything* broke at once (root cause)

The entire data model of the current tool flows through a single line:

- `src/utils.py:290` — `getDashboardData()` does `execute_script("return dashboard")`,
  reading a global `dashboard` JavaScript object off `rewards.bing.com`.

`getAccountPoints`, `getRemainingSearches`, activity enumeration, punch cards, and bonus
points are all built on that scraped global. A React SPA almost certainly no longer exposes
that global, which is why the whole tool failed simultaneously rather than a few selectors
degrading.

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

## Phase 2 — Recon & the framework decision

Using the Phase 1 tooling on a real logged-in account:

1. **Confirm React SPA** and map the new DOM for the interactive bits (search box, activity
   cards, quizzes, punch cards).
2. **Determine what backs the dashboard** — points, counters, activity list, punch cards —
   across hypotheses (a)/(b)/(c) above. This determines how much of v4 is API vs DOM.
3. **Verify the mobile-search death** and confirm the OAuth flow Read-to-Earn depends on still
   works.
4. **Decide Selenium vs Playwright, with evidence.** Current lean is **Playwright** (native
   auto-waiting suits an SPA; lets us drop both `selenium-wire` and `undetected-chromedriver`).
   The open risk is the **stealth / anti-detection** story (`playwright-stealth`, Camoufox
   Playwright integration) — recon must confirm a viable approach before we commit. Fallback is
   ROADMAP Option A (keep Selenium, drop `selenium-wire`).

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
