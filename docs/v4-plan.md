# July 2026 Rewards redesign — investigation and implementation record

> Historical record of the investigation and v4 implementation. The work was merged to
> `main` and released as `4.0.0`; this is no longer the source of truth for active
> development planning.

## Current status

The core redesign adaptation is delivered in `main`:

- Dashboard data is parsed from the Next.js RSC payload in `src/rsc.py`, and balance,
  daily-set items, activity cards, activity counters, and claimable streak points no longer
  depend on `window.dashboard`.
- Daily-set activities and `/earn` “Keep earning” cards use RSC data to find the correct
  rendered card anchor, then click it through Selenium. Direct navigation to a
  `destination` URL was tested and does **not** award points.
- Streak bonus claiming, the redesigned login flow, and Bing re-authentication were updated
  for the new experience. Punch cards are deliberately skipped because they are not exposed
  by the currently parsed RSC data.

The following planned work remains open:

- The login state-machine refactor, `DebugRecorder`, page fingerprinting, typed errors, and
  `--diagnose` mode are not implemented.
- Mobile searches still run when mobile searches are selected; the proposed dedicated
  feature flag, defaulting off, was not added.
- Search counters are still read from the legacy Bing information endpoint when available,
  with conservative fallback limits when they are not. A native replacement has not been
  found in the RSC payload.
- `PREFER_BING_INFO` remains declared in `src/utils.py`, although the old dashboard
  dual-path is no longer used.
- Phase 4 cleanup is deferred: `selenium-wire`, `pyautogui`, `setuptools<81`, and
  undetected-chromedriver remain dependencies; Ruff, pre-commit, and dedicated lint/test CI
  have not been added.

## Background

In July 2026 Microsoft rolled out a major redesign of the Rewards experience. Observed and
suspected effects:

- The Rewards page is now a **Next.js App Router application** (v16.2.6, deployed
  2026-07-01) using React Server Components. Confirmed in Phase 2.
  The existing Selenium selectors are ineffective. The new URL is
  `https://rewards.bing.com/dashboard` (both `rewards.bing.com/` and
  `rewards.microsoft.com/` redirect there).
- **Points earnable per day appear reduced** — a Microsoft policy change, not a bug on our
  side. No engineering fix; document expectations only.
- **Mobile search points appear to no longer be collectable** via browser automation.

### Why *everything* broke at once (pre-v4 root cause)

Before v4, the entire data model flowed through a single line:

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
> clean choices. Investigation must distinguish between at least:
> - (a) the same `dapi` REST API also backs the new web dashboard;
> - (b) the React app uses a **brand-new** API / GraphQL / BFF;
> - (c) the old API is kept **only for mobile** while web moved to something else.
>
> We map what is actually there before betting the data layer on any one of these.

## Phase 0 — Branch & scaffolding  ✅

- [x] Cut `feat/rewards-redesign-v4` (major version → `4.0.0-dev`).
- [x] Land this planning doc so intent is tracked.

## Phase 1 — Debug tooling *first* (the enabler)

Diagnosing a breakage must not require reproducing it by hand in visible mode. Some form of
permanent, general-purpose evidence capture has to exist before automation logic is rewritten.

A single-purpose recon harness was built and used to answer the Phase 2 questions, then
**removed**: it was tied too tightly to one investigation (fixed probe URLs, a bespoke
report format, its own login driver) to be worth maintaining as a permanent tool. The
findings it produced are preserved in Phase 2 below.

What replaces it is deliberately **not** specified here. The requirement is a *generic*
debugger, and that design already lives in [ROADMAP.md](../ROADMAP.md) under the login-flow
refactor: `DebugRecorder`, page fingerprinting, typed errors carrying `(step, fingerprint,
artefacts)`, and a `--diagnose` flag. That machinery is broader than the Rewards page and
should be built once, there, rather than duplicated per investigation.

Constraints any such tool must respect:

- **Do not assume an authenticated session.** `Login.login()` short-circuits on
  `utils.isLoggedIn()`, so a cached cookie means "logged in" is reported while
  `execute_login()` never runs and no sign-in page is ever visited. Any tool investigating
  the login flow must be able to force a fresh session, and must say plainly when it did not.
- **Hook, do not fork.** `execute_login()` walks a known sequence of steps (email, post-email,
  password, post-password, TOTP, post-login dialogs, dashboard). Evidence capture belongs at
  those existing boundaries, not in a parallel login implementation maintained alongside them.
- **Security.** Never persist passwords, TOTP secrets, computed OTPs, JWTs, or auth cookie
  values. Microsoft sign-in URLs additionally carry `epct`, `code_challenge`, `state` and the
  account name as query parameters, and those values reach disk through URLs, page dumps and
  any captured HTML — redact per the ROADMAP security constraints. Evidence dir gitignored.

## Phase 2 — Framework decision  ✅

Established against a real logged-in account before the recon tool was retired.

### Findings

**1. Framework confirmed — Next.js App Router, not a plain React SPA**

`window.next` and `__NEXT_DATA__` are both present. Build tag
`dpl=20260701-3` (deployed 2026-07-01). The app uses **React Server Components (RSC)**
with streaming via `self.__next_f.push([1, "..."])` inline scripts injected into the
initial HTML. There is no separate client-side data fetch for the dashboard — all
structured data arrives in the first SSR response.

**1b. Full front-end inventory (re-verified live 2026-07-31)**

There are **two unrelated front-end applications** in play, which is why the login code
and the dashboard code cannot share techniques. Observed on 2026-07-31 against an
authenticated session and again through a forced fresh login, so the sign-in pages were
walked step by step rather than skipped via a cached cookie.

| | Rewards dashboard | Microsoft sign-in |
|---|---|---|
| Host | `rewards.bing.com/dashboard` | `login.live.com`, `login.microsoft.com` |
| Framework | **Next.js 16.2.11**, App Router | none — server-rendered pages |
| Rendering | React Server Components | client-side React, no SSR payload |
| React evidence | `__reactFiber$` expando on `<body>` | `_reactRootContainer` expando |
| Component library | **React Aria** (66 × `data-react-aria-pressable`) | **Fluent UI v9** (Griffel, `fui-` classes) |
| Styling | CSS bundle | Griffel CSS-in-JS |
| State source | RSC payload in HTML (`self.__next_f`) | `window.$Config`, `window.ServerData` |
| Bundler | webpack (`webpackChunk_N_E`) | webpack (`webpackChunk_msidentity_sisu_aad`) |
| Build tag | `dpl=20260730-3` | `aadcdn.msauth.net/shared/4/js/` |

Not present anywhere: Angular, Vue, Svelte, jQuery. Next.js moved 16.2.6 → 16.2.11
between 2026-07-17 and 2026-07-31, so the dashboard is under active development and
selector churn should be expected.

Two consequences for the code:

- **React Aria drives every dashboard control.** Its pressables are wired through
  `usePress`, not `onclick`, so `execute_script("arguments[0].click()")` is silently
  ignored and `ActionChains(...).move_to_element(el).click().perform()` is required.
  This is already noted in `AGENTS.md`; the fingerprint is the evidence for it.
- **The sign-in pages are config-driven, not DOM-driven.** `window.$Config` is the
  authoritative state, which supports the ROADMAP recommendation to read
  `window.$Config.sErrorCode` via `execute_script` instead of substring-matching
  `page_source` for fragments like `80041032`.

> **Fingerprinter caveat, fixed 2026-07-31.** The original `JS_FINGERPRINT` probed only
> `__REACT_DEVTOOLS_GLOBAL_HOOK__` and `window.React`. Neither exists in a production
> build — the hook is installed by the DevTools *extension* — so it reported
> `React: NO` on a Next.js page, which is self-contradictory. Detection now derives
> from React's DOM expandos (`__reactFiber$` / `__reactContainer$` /
> `_reactRootContainer`) and asset paths, and every detector reports the evidence that
> triggered it. Grepping static HTML for framework names has the same failure mode: the
> sign-in HTML contains zero occurrences of `react`, and its only `jquery` hits come
> from a `watsonsupportwithjquery` diagnostics bundle that probes for a jQuery which is
> never actually loaded.

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

The `destination` field on each `dailySetItem` is a direct URL (e.g. a Bing search URL).
Later implementation testing showed that direct navigation does not award points, so the
automation uses RSC data to locate and click the rendered activity-card anchor instead.

**3. Search counters — not yet located**

`pcSearch`, `mobileSearch`, `pointProgressMax`, and `pointProgress` keys were *not*
found in the captured page source. These counters are either in a lazily-loaded RSC
component, behind a separate route (e.g. `/pointsbreakdown`), or require a search
action to trigger. This is the main unknown heading into Phase 3.

**4. Mobile search death — unverified (but expected)**

Not directly probed. Mobile searches use a separate browser
context (`browserType == "mobile"` with resolution/UA spoofing). The Bing search
submission mechanic (`sb_form_q` + `submit()`) likely still works — the break is that
the new dashboard no longer reports mobile search progress. Gated behind `search.mobile`
flag defaulting off per the Phase 3 plan.

**5. Read-to-Earn OAuth flow — assumed intact**

The Read-to-Earn path uses `login.live.com → prod.rewardsplatform.microsoft.com/dapi/me/activities`.
This API endpoint is independent of the web dashboard redesign. No evidence gathered so
far contradicts it, but it has never been exercised directly — verifying it end to end is
still outstanding.

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

**Decision: keep `undetected-chromedriver` + Selenium for the v4 implementation.**
Playwright remains an option for a future phase if stealth or await ergonomics become a
blocking issue.

## Phase 3 — Core rewrite (delivered portions and remaining work)

- [x] **Data layer:** RSC parsing now supplies dashboard balance, daily-set items, activity
  cards, activity counters, and streak-claim state.
- [x] **Interaction layer:** daily activities, `/earn` cards, and streak bonus claiming were
  adapted to the new page. Punch cards remain skipped because their data is unavailable.
- [x] **Login:** support for the redesigned Microsoft sign-in flow was added.
- [ ] **Login architecture:** the ROADMAP state-machine refactor, diagnostics, and
  scripted-driver tests remain outstanding.
- [ ] **Mobile split:** Read-to-Earn remains enabled, but the proposed
  `search.mobile` feature flag has not been implemented. Mobile browser searches therefore
  still execute when selected.
- [ ] **Search counters:** no RSC-backed search-counter implementation has been found;
  legacy Bing information and fallback ceilings remain in use.

## Phase 4 — Deferred cleanup (ROADMAP debt)

Since the tree is already churning:

- Drop `selenium-wire` → unpin `setuptools<81`; drop `pyautogui` if unused; drop
  `undetected-chromedriver` if we adopt Playwright.
- Ruff + pre-commit + minimal CI (lint / format / tests).
- Docs: the `4.0.0` release is complete. Keep the README and architecture documentation
  aligned with the RSC implementation as follow-up work.

## Non-goals / accept-and-document

- **Reduced points-per-day** is a Microsoft policy change — no engineering fix; set
  expectations in the README.
