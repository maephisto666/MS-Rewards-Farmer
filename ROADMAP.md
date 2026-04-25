# Roadmap

## Must Have

### Clean dirty sessions

Sometimes, due to errors during login, dirty sessions are created. As a consequence, in subsequent executions opening Chrome is not possible anymore.

## Nice to Have

### Alternative Browser Backend (Camoufox)

The `camoufox-test` branch (now deleted) explored integrating
[Camoufox](https://github.com/nicholasgasior/camoufox), an anti-detection Firefox-based
browser, as an alternative to undetected-chromedriver. This could improve resilience against
bot detection. Revisiting this as a fresh feature once the codebase is stable would be
worthwhile.

### Activity Handling Improvements

The `feat/better-activities` branch contains several improvements worth evaluating and
incorporating:

- **Remove PyAutoGUI dependency** -- the `pyautogui` package is no longer used for activity
  completion and can be dropped from requirements.
- **Navigate directly via activity URL** -- use `activity["destinationUrl"]` instead of
  clicking on activity cards in the page, avoiding click interception issues.
- **Avoid unnecessary page reloads** -- add `forceRefresh` parameters to `goToRewards()`,
  `goToSearch()`, `getDashboardData()`, and related methods to skip navigation when already
  on the correct page.
- **General cleanup** -- remove unused imports and dead code paths.

### Revisit PREFER_BING_INFO and Data Sources

The codebase has two data sources for account info (points, remaining searches, user level):

- **Bing API** (`getBingInfo()`) -- HTTP call to `bing.com/rewards/panelflyout/getuserinfo`.
  Faster (no page navigation), but undocumented and its schema has broken (e.g. `PCSearch`
  key no longer exists). Currently disabled via `PREFER_BING_INFO = False`.
- **Dashboard scraping** (`getDashboardData()`) -- Navigates to `rewards.bing.com` and
  extracts the `dashboard` JavaScript object. Slower (page load + 5s wait), but reliable.

The `PREFER_BING_INFO` flag and all its `if/else` branches throughout `browser.py` and
`utils.py` are a leftover from the upstream repo where it was always `True` and never
exposed as a configuration option. Now that it's `False`, the API code paths are dead code.

This needs revisiting: understand if the Bing API can still be used reliably (possibly with
updated key names), or if the dashboard scraping approach should be the sole data source.
Either way, the dual-path branching should be cleaned up.

### Login Flow Refactor (`src/login.py`)

Three parallel analyses (complexity, debuggability, robustness) converged on the same
conclusion: `src/login.py` has become a fragile procedural script with an ad-hoc state
machine over roughly 30 Microsoft UI variants. Every new variant reported by users
(`ae4bdc7`, `d994c81`, `4155a56`) has required adding another `elif` branch and duplicating
selector lists. The file is at the "one more case and it breaks silently" point.

#### Consolidated verdict

- 508 lines, 2 god functions:
  - `execute_login()` — ~218 lines, cyclomatic ≈ 17, cognitive ≈ 28.
  - `_handle_post_login_dialogs()` — ~93 lines, cyclomatic ≈ 15, cognitive ≈ 22; worst-case
    runtime ≈ 95 s because of a 5-iteration serial dialog prober.
- ~43 explicit selectors / branches across ~30 logical UI variants.
- OTP selector list duplicated in three places (`_detect_post_password_state`,
  `_wait_for_otp_input` clickable + visibility branches).
- Element-centric dispatch (`if el_id == "idA_PWD_SwitchToCredPicker"`): reverse lookup
  from "which locator matched" to "which page am I on" — any new variant breaks the flow.
- Stringly-typed state (`"totp" | "password_required" | "other_ways" | "post_login"`) with
  no enum, no exhaustiveness check.
- Substring matching on `page_source` for localized Microsoft text and raw JSON fragments
  (e.g. `sErrorCode":"80041032`, `"Please enter the password for your Microsoft account."`)
  — breaks on any copy change or non-EN account.
- Magic timeouts `10`/`5`/`3` scattered; no single source of truth.

#### Correctness / debuggability bugs to fix

- `self.webdriver.close()` is called inside `login()`, `locked()`, `banned()` while
  `Browser.__exit__` also calls `close()+quit()` → double-close exception masks the real
  cause of the failure.
- `assert CONFIG.browser.visible` + `input()` as a 2FA fallback: under `python -O` the
  assert is stripped entirely; in Docker/CI the `input()` blocks forever.
- `_find_first_visible` swallows bare `Exception`, hiding `InvalidSessionIdException`,
  stale elements, and driver crashes.
- Failures log only URL + title (and only at steps 1-2). No page dump, no screenshot, no
  JS state, no cookies. Every new variant has to be reproduced manually in visible mode —
  which is exactly the maintenance pattern history shows.
- `_submit_otp` sequential fallbacks: 7 strategies x 3 s timeout = worst-case 21 s
  with no log of which one matched.

#### Recommended architecture

All three workers converged on the same target architecture:

```
src/login/
  __init__.py          # re-exports Login (backward-compat)
  login.py             # thin orchestration, public API
  state_machine.py     # LoginStateMachine, State/PageKind enum, Transition
  descriptors.py       # PageDescriptor dataclass
  pages.py             # DEFAULT_PAGES: tuple of PageDescriptor (the "data")
  locators.py          # named Locator tuples (single source of truth)
  resilient_finder.py  # ResilientFinder + Match (drives clicks/typing with telemetry)
  driver_protocol.py   # LoginDriver Protocol + SeleniumLoginDriver + FakeLoginDriver
  errors.py            # LoginError hierarchy (one subclass per step)
  debug.py             # DebugRecorder (evidence bundle on step / on error)
  fingerprint.py       # page_fingerprint() + log_fingerprint()
```

Key ideas:

- **Page descriptors**. Each Microsoft page is a frozen dataclass: `kind`, `locator_signals`,
  `url_substrings`, `text_substrings`, `action`, `next_states`, `terminal`. Adding a new
  variant becomes ~10 lines in `pages.py` plus one scripted test — no edit to
  `execute_login`, no new `elif`.
- **State machine dispatcher**. Detect matching descriptor -> run its action -> loop until
  terminal. Max hop count guard (e.g. 25) to catch infinite dialog loops.
- **`Locator` + `ResilientFinder`**. Named locators with fallbacks. Finder records which
  named locator hit (`finder.hits = {"otc_autocomp": 13, "otc_tel": 2}`) — free telemetry
  on which variants real accounts use.
- **Typed exception hierarchy**. `LoginError` carrying `(step, fingerprint, artefacts)` with
  subclasses `EmailStepError`, `PostEmailStepError`, `PasswordStepError`,
  `TwoFactorStepError`, `PostLoginError`, `UnknownPageError`, `AccountLockedError`,
  `AccountBannedError`.
- **`DebugRecorder`**. Per-step evidence bundle (page_source, screenshot, url, title,
  scrubbed cookies, scrubbed localStorage/sessionStorage, JS globals `$Config` / `ServerData`
  / `PROOF` / `BrsData`). Gated by `CONFIG.debug.login.enabled`, default `mode: on_error`.
  Must **never** persist `browser.password`, `browser.totp`, the computed OTP value, or JWT
  substrings; cookie values for `ESTSAUTH*`/`MSPAuth*`/`RPSAuth*`/`PPAuth*`/`WLSSC`/`_U`/
  `MUID`/`OIDI*` redacted to `<redacted:NB>`.
- **Page fingerprint**. ~40 LOC utility that classifies the current page by presence of
  named signals; logged at every step so missing variants show up as `matched=[]` in logs
  without dumping pages.
- **Centralised `LoginTimeouts`** dataclass, structured per-step logs
  (`step=email status=ok variant=email_new ms=312`), and a `--diagnose` flag that force-
  dumps evidence at every transition.
- **Test seams**. Extract a `LoginDriver` Protocol and a `ScriptedDriver` fake, making the
  whole flow unit-testable in milliseconds without Chrome.

#### Top 5 highest-ROI improvements (ranked)

1. **`DebugRecorder` + page fingerprint + typed exceptions** — biggest leverage on future
   triage time; small, self-contained, unblocks every later refactor.
2. **Remove double-close + replace `assert` / `input()` control flow** — correctness fixes
   hiding real failure modes today.
3. **Extract `SelectorRegistry` / `locators.py`** — pure deletion-style refactor; collapses
   the three OTP selector lists + the 7 OTP-submit fallbacks + the post-login probes into
   named constants. Prevents the "forgot one of the three copies" drift already observed.
4. **`PageKind` enum + `match` statement in `execute_login`** — catches typos at import
   time; ~20 LOC.
5. **`LoginStateMachine` over `PageDescriptor`s + `ScriptedDriver` tests** — the structural
   cure; makes "add a new variant" a 10-line data change with a test.

#### Incremental migration plan (4 non-breaking PRs)

| PR  | Scope                                                                                | Released as |
|-----|--------------------------------------------------------------------------------------|-------------|
| 1   | Add `DebugRecorder`, `Locator`/`Match`/`ResilientFinder`, `LoginDriver` protocol,    | 3.5.0       |
|     | evidence bundle, typed exceptions. No behaviour change.                              |             |
| 2   | Extract selectors into `locators.py`. Replace inline `EC.any_of` lists. Pure         | 3.5.1       |
|     | deletion diff.                                                                       |             |
| 3   | Add `descriptors.py`, `pages.py`, `flow.py` behind `login.use_state_machine: false`. | 3.6.0       |
|     | Parity tests per variant. Dog-food on maintainer accounts.                           |             |
| 4   | Flip default to state machine, delete legacy `execute_login`, promote `--diagnose`.  | 4.0.0       |

Safety net during migration: the new flow falls back to the legacy `execute_login` when it
cannot match a descriptor (and dumps evidence), so a missing variant never blocks the user.

#### Security constraints (must hold even in verbose mode)

- `self.browser.password` / `self.browser.totp` / computed OTP: never passed to the
  recorder; scoped to `execute_login` locals only.
- Input element `value=` for `passwd` / `passwordEntry` / `i0118` / `otc`: regex-scrubbed
  in HTML dumps before write.
- Auth cookies (`ESTSAUTH*`, `MSPAuth*`, `RPSAuth*`, `PPAuth*`, `WLSSC`, `_U`, `MUID`,
  `SRCHUID`, `MSCC`, `OIDI*`): store name + length only.
- `localStorage` / `sessionStorage` keys matching `token|auth|session|refresh|cred|nonce`:
  redacted value, keep key.
- JWT substrings anywhere: regex `eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+`
  -> `<redacted-jwt>`.
- Selenium-wire request bodies: off by default; if enabled, strip `Authorization` and
  `Cookie` headers.
- Artefact directory `logs/login_debug/` written with `os.umask(0o077)` / `chmod 0o600`.
  Email is never in the path (use `sha1(email)[:10]`). Gitignored.

#### Per-worker detailed findings

##### Worker 1 — complexity / convolutedness audit

Complexity metrics (rough per-method estimates):

| Method                           | Lines   | Cyclomatic | Cognitive | Notes                                  |
|----------------------------------|---------|------------|-----------|----------------------------------------|
| `login`                          | 12      | 4          | 4         | Thin wrapper; duplicates `close()`.    |
| `check_locked_user/banned_user`  | ~8 each | 2          | 2         | OK.                                    |
| `locked`/`banned`                | ~8 each | 3          | 3         | Duplicated pair.                       |
| **`execute_login`**              | ~218    | ~17        | ~28       | God function.                          |
| `_detect_post_password_state`    | 43      | ~9         | ~13       | Stringly typed; mixes substring + DOM. |
| `_wait_for_otp_input`            | 31      | ~3         | ~6        | Same 10-selector list duplicated 2x.   |
| `_submit_otp`                    | 16      | ~8         | ~8        | 7 strategies x 3 s = worst case 21 s.  |
| `_find_first_visible`            | 9       | ~5         | ~5        | Swallows bare `Exception`.             |
| **`_handle_post_login_dialogs`** | ~93     | ~15        | ~22       | 5 iterations x ~19 s worst case.       |

Full special-case inventory (43 branches / ~30 variants, with line numbers):

- **Email step (E1-E6)**: `usernameEntry`/`i0116`; no-field-passkey-enroll/RewardsPortal/
  raise; submit via `primaryButton` vs `idSIButton9`.
- **Post-email step (P1-P8)**: `idA_PWD_SwitchToCredPicker`, "Use your password" span,
  `passwd`, `passwordEntry`; after Flow A click: `aria-label`, span XPath, `passwd`,
  `passwordEntry`.
- **Password step (PW1-PW2)**: `passwd` / `passwordEntry`.
- **Post-password step (PP1-PP8)**: TOTP input (10 selectors), "Other ways to sign in",
  passkey URL, `kmsiForm`, `iPageTitle`, RewardsPortal, `80041032` error code substring,
  "Please enter the password" substring.
- **Auth-app picker (A1-A3)**: tileList span, `PhoneAppOTP`, "authenticator app" text.
- **OTP input (O1-O10)**: 10 duplicated selectors.
- **OTP submit (S1-S7)**: `idSubmit_SAOTCC_Continue`, `idSIButton9`, primaryButton,
  Verify/Next button XPath, value=Verify/Next input XPath, `button[type=submit]`,
  `input[type=submit]`.
- **Post-login dialogs (D1-D10)**: RewardsPortal exit, HTTP error re-nav, security info
  dialog, passkey enrollment via secondary/dismiss/primary button or navigate away,
  `kmsiForm`, generic primaryButton catch-all, "protect your account" prompt.
- **Lock/ban (LB1-LB2)**: `serviceAbuseLandingTitle` / `fraudErrorBody`.
- **2FA branch (F1-F3)**: TOTP auto-submit, visible-mode input() wait, AssertionError.

Specific code smells cited:

- Stringly-typed state machine with magic string comparisons (`"totp"` etc.).
- `requires_2fa` flag written from nested branches then read much later.
- Raw JSON substring match on `page_source` (`sErrorCode\":\"80041032`) — Microsoft's
  internal response shape is not a stable API.
- Catch-all `primaryButton` click can mask future regressions.
- `for _ in range(5)` with no backoff, no state, silent on loop exit.
- Inconsistent wait strategies and timeouts (10 s / 5 s / 3 s mixed with `time.sleep(5)`).
- `_find_first_visible` eats `StaleElementReferenceException` and anything else.
- Comment "Flow A/B/C" drift: dispatch keyed by `el_id`/`el_name`, not by flow label.

##### Worker 2 — debuggability / exception handling audit

Exception handling audit (abridged; full table in the investigation notes):

| Location                                | Current behaviour                                | Risk     | Recommendation                                            |
|-----------------------------------------|--------------------------------------------------|----------|-----------------------------------------------------------|
| `locked`/`banned` `close()`             | Closes the driver from inside the handler        | HIGH     | Drop `close()`; let `Browser.__exit__` own teardown.      |
| `login()` outer `except Exception`      | Logs, `close()`, re-raises                       | HIGH     | Drop `close()`; use `logging.exception()`; attach path.   |
| `execute_login` step 1 fallback         | URL substring `"passkey/enroll"`                 | MEDIUM   | Replace with page fingerprint.                            |
| `step 3` assert on field value          | `assert == self.browser.password`                | CRITICAL | Replace with explicit raise; never compare in the log.    |
| `step 4` substring `80041032`           | Raw JSON fragment of `$Config`                   | HIGH     | Read `window.$Config.sErrorCode` via `execute_script`.    |
| `_detect_post_password_state`           | Timeout returns silently                         | MEDIUM   | Log each probe at DEBUG; attach fingerprint on timeout.   |
| `_find_first_visible`                   | Bare `except Exception`                          | HIGH     | Narrow to `StaleElementReferenceException` et al.         |
| `_submit_otp`                           | 7 selectors, no log of which hit                 | LOW      | Log `[LOGIN] OTP submit via %s=%s` on success.            |
| `_handle_post_login_dialogs` loop       | 5 iterations, bare excepts, no per-iter log      | MEDIUM   | Track firing branch; raise `PostLoginError` on 5th miss.  |
| `assert CONFIG.browser.visible`+input() | Control-flow assert + interactive read           | CRITICAL | Raise typed errors; honour `CONFIG.login.interactive`.    |
| HTTP error detection                    | `"HTTP ERROR" in page_text`                      | MEDIUM   | Match on `chrome-error://` URL scheme and body selectors. |

Proposed `DebugRecorder` (see architecture above). CONFIG keys:

```yaml
debug:
  login:
    enabled: true
    mode: on_error           # always | on_error | on_unknown_state
    capture:
      page_source: true
      screenshot: true
      cookies: true          # scrubbed
      storage: true          # scrubbed
      performance: true
      js_globals: true       # $Config, ServerData, PROOF, BrsData, authenticationGateway
      seleniumwire_requests: false
    retention_days: 7
    max_page_size_kb: 2048
    redact_passwords: true
    dir: logs/login_debug
```

Directory layout:

```
logs/login_debug/
  <sha1(email)[:10]>/                 # 1 dir per account
    20260421T181723Z-desktop/         # 1 dir per login() call
      00_step1_email_pre.html
      00_step1_email_pre.png
      00_step1_email_pre.json
      ...
      99_failure.json
      manifest.json
```

Estimated disk usage: ~0 bytes on successful login (`on_error` mode). ~3-6 MB per failing
login. With `retention_days: 7` x 4 accounts x worst-case 1 failure/day ~ 200 MB cap.

Top 5 "must fix" debuggability gaps (ranked):

1. No page artefact on failure.
2. `self.webdriver.close()` inside handlers (double-close).
3. `assert` + `input()` for 2FA/protect fallbacks.
4. Substring matching for error codes / HTTP errors.
5. No fingerprint / step-transition debug trace.

##### Worker 3 — robustness / maintainability audit

Concrete code pattern from `execute_login` after `EC.any_of`:

```python
el_id   = result.get_attribute("id")   or ""
el_name = result.get_attribute("name") or ""
if el_id == "idA_PWD_SwitchToCredPicker":
    ...
elif el_name == "passwd" or el_id == "passwordEntry":
    ...
else:
    ...
```

This is a reverse lookup from "which locator matched" to "which page am I on" — every
variant requires (i) a new locator and (ii) a new `elif` branch.

Proposed `PageDescriptor` dataclass, state machine dispatcher, `Locator` + `ResilientFinder`
abstraction, and `LoginDriver` protocol (sketches in the architecture section above).

"Add a new variant in 10 lines" worked example (scenario: a new "Verify your identity"
post-password screen with a `data-testid="useAuthAppBtn"` button):

```python
# src/login/pages.py
VERIFY_IDENTITY = PageDescriptor(
    kind=PageKind.VERIFY_IDENTITY,
    locator_signals=(
        Locator("verify_id_title", By.XPATH, "//*[contains(.,'Verify your identity')]"),
        Locator("verify_id_auth",  By.CSS_SELECTOR, "[data-testid='useAuthAppBtn']"),
    ),
    next_states=frozenset({PageKind.OTP}),
    action=lambda ctx: (ctx.finder.find([
        Locator("verify_id_auth", By.CSS_SELECTOR, "[data-testid='useAuthAppBtn']")]
    ).click(), PageKind.OTP)[1],
)
DEFAULT_PAGES = (..., VERIFY_IDENTITY, ...)
```

Documentation recommendations:

- Add a `## Login flow (see docs/login-flow.md)` section to `AGENTS.md`:
  - NEVER add inline `if el_id == "..."` branches to `execute_login`.
  - New variants = edit `pages.py` only.
  - Every PR touching login must add a test under `test/test_login_flow.py` using
    `ScriptedDriver`.
  - First triage step for reported failures: enable `--diagnose` and attach the evidence
    bundle.
- New `docs/login-flow.md`:
  - Mermaid state diagram generated from `pages.py`.
  - Table of known page variants (signals + action + next_states).
  - Troubleshooting runbook for "unknown page" and "exceeded max_hops" errors.
  - Contribution recipe for a new variant.
- New `CONTRIBUTING.md` checklist for login PRs (test added? named locator? next_states
  listed? evidence bundle attached?).

Developer tooling to add:

- `uv run python -m src.login.diagnose --email foo --password bar` — live login with full
  per-step evidence capture, non-headless by default.
- `uv run python -m src.login.describe` — prints the state diagram as Mermaid.

#### Risks / trade-offs

- **Scope**: a full state-machine refactor is ~2x the current file. During the transition
  both must coexist behind `CONFIG.login.use_state_machine`.
- **Test coverage is weak today**: no unit tests for `login.py`. Before migration, land
  fixture-based tests (saved `page_source` snapshots per variant) so refactoring is not
  flying blind.
- **`undetected_chromedriver` quirks**: the current `webdriver.close()` calls may work
  around UC's `__exit__`/orphan-process issues. Any refactor must verify close/quit
  ordering.
- **Snapshot privacy**: default to `mode: on_error`, redact inputs, gitignore
  `logs/login_debug/`, auto-purge beyond `retention_days`.
- **Upstream churn**: Microsoft will keep changing the UI. This refactor reduces
  *maintenance cost per variant*, not *frequency of variants* — ROI scales with how often
  the file changes (5+ login-related commits in the last ~3 months).
