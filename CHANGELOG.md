# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.0](https://github.com/maephisto666/MS-Rewards-Farmer/compare/4.0.1...5.0.0) (2026-08-30)


### ⚠ BREAKING CHANGES

* reworked for the redesigned Microsoft Rewards site — dashboard data is now read from the Next.js RSC payload and the login flow targets the new sign-in pages.

### Added

* adapt automation to the 2026 Microsoft Rewards redesign ([60c196b](https://github.com/maephisto666/MS-Rewards-Farmer/commit/60c196be65d69438967fd2ab9c4c154da36424c2))
* add --totp CLI parameter for 2FA ([3c9fde0](https://github.com/maephisto666/MS-Rewards-Farmer/commit/3c9fde06098bf54523c01ee4c36d79281f4f53cb))
* add --totp CLI parameter for 2FA ([bc527d8](https://github.com/maephisto666/MS-Rewards-Farmer/commit/bc527d888dba2406754ed5e32ebba8c68a389212))
* add reset functionality to delete session files and kill chrome processes ([70631b8](https://github.com/maephisto666/MS-Rewards-Farmer/commit/70631b87f4617c1fa62ba4b48c7c12c57f2ceaa9))
* add virtual authenticator to bypass passkey dialogs (v3.2.0) ([d25089b](https://github.com/maephisto666/MS-Rewards-Farmer/commit/d25089b7ce4ba8cafab25f5263e27ab3b584b0ef))
* add virtual authenticator to bypass passkey dialogs (v3.2.0) ([a5ae398](https://github.com/maephisto666/MS-Rewards-Farmer/commit/a5ae39892707de77a6d12d0bb69379acfb9c4108))
* added explicit registry for Python dependencies ([ec7dcff](https://github.com/maephisto666/MS-Rewards-Farmer/commit/ec7dcff8cb78142f7f332628ffd50bf0e446eafb))
* auto-claim bonus points banner on rewards page ([2ca4e30](https://github.com/maephisto666/MS-Rewards-Farmer/commit/2ca4e307e11d122882193bf593a4a163a6f301bd))
* auto-claim bonus points banner on rewards page ([9e539a5](https://github.com/maephisto666/MS-Rewards-Farmer/commit/9e539a5a8cf0b28502ec22895b25d5a3228381a7))
* complete 'Keep earning' activity cards on the /earn page ([#37](https://github.com/maephisto666/MS-Rewards-Farmer/issues/37)) ([ff26528](https://github.com/maephisto666/MS-Rewards-Farmer/commit/ff26528a2bbf5c42768b1dcf09ecd1410f1ae401))
* read dashboard data from the Next.js RSC wire format ([c6c914d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/c6c914da2207b9693025a8e15d70376fc87422d1))
* register Windows scheduled task via PowerShell instead of XML ([#30](https://github.com/maephisto666/MS-Rewards-Farmer/issues/30)) ([c965a29](https://github.com/maephisto666/MS-Rewards-Farmer/commit/c965a29b0f964d257e32e6bc07ee3a32578006ae))
* rework the login flow for the redesigned Microsoft sign-in ([fdd39a0](https://github.com/maephisto666/MS-Rewards-Farmer/commit/fdd39a0fec00ab367c8134db9aa1192196c9ddfd))
* rewrite login flow with EC.any_of for faster, locale-independen… ([711e7e8](https://github.com/maephisto666/MS-Rewards-Farmer/commit/711e7e83058e63dafa926ed892697cdf6c9a03d0))
* rewrite login flow with EC.any_of for faster, locale-independent detection ([0c72466](https://github.com/maephisto666/MS-Rewards-Farmer/commit/0c724661c24e084edc9d8fd2bda3f3a447ca6354))
* support multiple queries per activity with title fallback ([9686a65](https://github.com/maephisto666/MS-Rewards-Farmer/commit/9686a651f2fe98a10587eee004ea05de9ecd2e47))
* support multiple queries per activity with title fallback ([ab8133a](https://github.com/maephisto666/MS-Rewards-Farmer/commit/ab8133a339c639ce93d534017bec47431b1f6665)), closes [#25](https://github.com/maephisto666/MS-Rewards-Farmer/issues/25)


### Fixed

* 280 ([608f48c](https://github.com/maephisto666/MS-Rewards-Farmer/commit/608f48cff044c392391526aa915a24d822858c9f))
* add search effectiveness tracking and readToEarn stuck detection ([963d7fa](https://github.com/maephisto666/MS-Rewards-Farmer/commit/963d7faf540f724402c207b5b9cf98497ca7ebaf))
* allow browser language to be set independently of geolocation ([e1a3619](https://github.com/maephisto666/MS-Rewards-Farmer/commit/e1a36196715124bb65bea808c4f6783309f0eb9e))
* allow browser language to be set independently of geolocation ([0f1770e](https://github.com/maephisto666/MS-Rewards-Farmer/commit/0f1770e9524a4b8e1eb73752c5211f8c667b67e7))
* **ci:** configure release group title ([#44](https://github.com/maephisto666/MS-Rewards-Farmer/issues/44)) ([a03e8bf](https://github.com/maephisto666/MS-Rewards-Farmer/commit/a03e8bfa9f15c5513de23774aa4eb75f414e8a03))
* clean up login() method - deduplicate locked/banned checks, move assert after execute_login ([ac1910d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/ac1910d0d84e07123923323b8d3c7f2c42692cda))
* clean up login() method - deduplicate locked/banned checks, move… ([33c0a24](https://github.com/maephisto666/MS-Rewards-Farmer/commit/33c0a24c24a2cff9e95ebf8633fd5aa1db2448ae))
* format notification message for incomplete activities ([d2a6ebd](https://github.com/maephisto666/MS-Rewards-Farmer/commit/d2a6ebd00f6d39163896a214e4cccd4c65a555d3))
* format notification message for incomplete activities ([#272](https://github.com/maephisto666/MS-Rewards-Farmer/issues/272)) ([b43c741](https://github.com/maephisto666/MS-Rewards-Farmer/commit/b43c7411fb0c937b25a19f39aa3a0d46498df31c))
* handle additional white OTP and password-required pages ([4155a56](https://github.com/maephisto666/MS-Rewards-Farmer/commit/4155a56c0244f00bfd7861b5d005d364cb67c37f))
* handle login flow for accounts without 2FA enabled ([7214e2d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/7214e2dd3d322e7fac0dd800883d3148d5621e1b))
* handle login flow for accounts without 2FA enabled ([b5a88f4](https://github.com/maephisto666/MS-Rewards-Farmer/commit/b5a88f414f2df799bdb0e66588503837b2b22a2b))
* handle null promotionalItem in punch cards ([#17](https://github.com/maephisto666/MS-Rewards-Farmer/issues/17)) ([b2a7cc6](https://github.com/maephisto666/MS-Rewards-Farmer/commit/b2a7cc6b215bd60840a74036c900afda11773d1f))
* improve punch card CTA click reliability ([1ceb1a1](https://github.com/maephisto666/MS-Rewards-Farmer/commit/1ceb1a12fe809dc0558cf8311b1c9eec36ca477b))
* improve punch card CTA click reliability ([80916c7](https://github.com/maephisto666/MS-Rewards-Farmer/commit/80916c78291fa9d76bfbc0f9658bcc648cbfc7d8))
* login flow was failing due to an unmanaged redirect ([490c808](https://github.com/maephisto666/MS-Rewards-Farmer/commit/490c8083c5f18b9a113de0752399ddae2758c2dd))
* login flow was failing due to an unmanaged redirect ([9cee90d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/9cee90dad7f8ccbf922d4ae6001c5190a641fb0b))
* proactively dismiss cookie consent banner on rewards page ([9e25501](https://github.com/maephisto666/MS-Rewards-Farmer/commit/9e2550170f30983ab31fcb189b77d524c5d258d8))
* re-authenticate www.bing.com so Bing searches are counted ([#36](https://github.com/maephisto666/MS-Rewards-Farmer/issues/36)) ([9d39e81](https://github.com/maephisto666/MS-Rewards-Farmer/commit/9d39e8132724b5038de908de3bad5f8c82684efe))
* reload trends when shelf is exhausted during search retries ([4726e73](https://github.com/maephisto666/MS-Rewards-Farmer/commit/4726e73698306c1cd113534310a24edf05917a9d))
* reload trends when shelf is exhausted during search retries ([b1170ca](https://github.com/maephisto666/MS-Rewards-Farmer/commit/b1170ca02c24659df28d14000077d38e64a46ed0))
* remove redundant sleep between searches (cooldown already provid… ([08e3a8d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/08e3a8da55611efaa53d6d615825513b9aeadd16))
* remove redundant sleep between searches (cooldown already provides delay) ([24ed0e8](https://github.com/maephisto666/MS-Rewards-Farmer/commit/24ed0e808643dabf6f8c564763a785f873043d05))
* requirements.txt to reduce vulnerabilities ([19d5890](https://github.com/maephisto666/MS-Rewards-Farmer/commit/19d58903d1e640ba7106431a0b0848d87ff2eeaa))
* requirements.txt to reduce vulnerabilities ([b424c39](https://github.com/maephisto666/MS-Rewards-Farmer/commit/b424c3961c4eaa3af50cd680d9beea53b0e8d1a0))
* resolve KeyError in getEdgeVersions and bug in getLanguageCountry ([6f6a0c5](https://github.com/maephisto666/MS-Rewards-Farmer/commit/6f6a0c5b252706146c6b76856f3c363ff4862b8a))
* resolve KeyError in getEdgeVersions and bug in getLanguageCountry ([#237](https://github.com/maephisto666/MS-Rewards-Farmer/issues/237)) ([4f0eb3a](https://github.com/maephisto666/MS-Rewards-Farmer/commit/4f0eb3aeb95ade6f10d4071b7c4cdc348a9ddf0e))
* skip cooldown for unmapped search activities, replace sleep with explicit wait ([408463a](https://github.com/maephisto666/MS-Rewards-Farmer/commit/408463a9a2643b7ba2ae8e1ad97c9eb2a1675263))
* skip cooldown for unmapped search activities, replace sleep with explicit wait ([1674f46](https://github.com/maephisto666/MS-Rewards-Farmer/commit/1674f468325f182e5907ce6533c9a9b4f7cceb72))
* support both OTP page variants in login flow ([d994c81](https://github.com/maephisto666/MS-Rewards-Farmer/commit/d994c81e4722efd12af1f3a5a21d69780323bdc4))
* use dashboard data instead of Bing API (PREFER_BING_INFO=False), default formatNumber to 0 decimals ([b08f506](https://github.com/maephisto666/MS-Rewards-Farmer/commit/b08f50617b60352ef799726708ae5342f5bca22d))
* use dashboard data instead of Bing API (PREFER_BING_INFO=False),… ([1b609e9](https://github.com/maephisto666/MS-Rewards-Farmer/commit/1b609e9f1c1bc084e70587621e41c214768baae5))
* use JavaScript click as fallback when element is intercepted ([#18](https://github.com/maephisto666/MS-Rewards-Farmer/issues/18)) ([ad76ef9](https://github.com/maephisto666/MS-Rewards-Farmer/commit/ad76ef9bc3c2a61e5f9bb6772087c4cb7ff9dbc5))
* use rewards.bing.com/ instead of /Signin/ in isLoggedIn fallback ([9e3a92d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/9e3a92da588c3c0fd47dad552d72e3c10fe9d664))
* use rewards.bing.com/ instead of /Signin/ in isLoggedIn fallback ([584b811](https://github.com/maephisto666/MS-Rewards-Farmer/commit/584b811dcd97e85a5db5609eaeefe8a72e288775))


### Changed

* incompleteActivities ([e9d8b52](https://github.com/maephisto666/MS-Rewards-Farmer/commit/e9d8b52a3bf840e10a33d246441e6c83cd6c21d4))
* incompleteActivities ([#273](https://github.com/maephisto666/MS-Rewards-Farmer/issues/273)) ([77daa95](https://github.com/maephisto666/MS-Rewards-Farmer/commit/77daa95213ed8cc9f0deaeb9e52763126d1c5b32))
* remove `sendNotification` ([813d97d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/813d97d9ac38a9ef95269d3adea796cbfd0421a3))
* remove `sendNotification` ([#283](https://github.com/maephisto666/MS-Rewards-Farmer/issues/283)) ([bf56dfa](https://github.com/maephisto666/MS-Rewards-Farmer/commit/bf56dfa9d1e4ccb421ae64c07eec4d607322f67f)), closes [#186](https://github.com/maephisto666/MS-Rewards-Farmer/issues/186)
* remove obsolete Bing info preference ([#42](https://github.com/maephisto666/MS-Rewards-Farmer/issues/42)) ([f4b139f](https://github.com/maephisto666/MS-Rewards-Farmer/commit/f4b139f3bb1a23811a86cf1948a8e27223e71e22))

## [4.0.1](https://github.com/maephisto666/MS-Rewards-Farmer/compare/4.0.0...4.0.1) (2026-08-30)


### Changed

* remove obsolete Bing info preference ([#42](https://github.com/maephisto666/MS-Rewards-Farmer/issues/42)) ([f4b139f](https://github.com/maephisto666/MS-Rewards-Farmer/commit/f4b139f3bb1a23811a86cf1948a8e27223e71e22))

## [4.0.0](https://github.com/maephisto666/MS-Rewards-Farmer/compare/3.7.0...4.0.0) (2026-08-22)


### ⚠ BREAKING CHANGES

* reworked for the redesigned Microsoft Rewards site — dashboard data is now read from the Next.js RSC payload and the login flow targets the new sign-in pages.

### Added

* adapt automation to the 2026 Microsoft Rewards redesign ([60c196b](https://github.com/maephisto666/MS-Rewards-Farmer/commit/60c196be65d69438967fd2ab9c4c154da36424c2))
* complete 'Keep earning' activity cards on the /earn page ([#37](https://github.com/maephisto666/MS-Rewards-Farmer/issues/37)) ([ff26528](https://github.com/maephisto666/MS-Rewards-Farmer/commit/ff26528a2bbf5c42768b1dcf09ecd1410f1ae401))
* read dashboard data from the Next.js RSC wire format ([c6c914d](https://github.com/maephisto666/MS-Rewards-Farmer/commit/c6c914da2207b9693025a8e15d70376fc87422d1))
* rework the login flow for the redesigned Microsoft sign-in ([fdd39a0](https://github.com/maephisto666/MS-Rewards-Farmer/commit/fdd39a0fec00ab367c8134db9aa1192196c9ddfd))


### Fixed

* re-authenticate www.bing.com so Bing searches are counted ([#36](https://github.com/maephisto666/MS-Rewards-Farmer/issues/36)) ([9d39e81](https://github.com/maephisto666/MS-Rewards-Farmer/commit/9d39e8132724b5038de908de3bad5f8c82684efe))

## [3.7.0](https://github.com/maephisto666/MS-Rewards-Farmer/compare/3.6.0...3.7.0) (2026-06-28)


### Added

* register Windows scheduled task via PowerShell instead of XML ([#30](https://github.com/maephisto666/MS-Rewards-Farmer/issues/30)) ([c965a29](https://github.com/maephisto666/MS-Rewards-Farmer/commit/c965a29b0f964d257e32e6bc07ee3a32578006ae))

## [3.6.0] - 2026-05-28

### Added

- **Auto-claim bonus points**: New `BonusPoints` class detects and claims the bonus points banner on the rewards dashboard after login. Verifies the claim succeeded by waiting for the success message ([#27](https://github.com/maephisto666/MS-Rewards-Farmer/pull/27)).

## [3.5.0] - 2026-05-25

### Added

- **Multiple queries per activity**: Each activity title in localized activity files now maps to a list of query variants (3 per entry). A random query is picked on each run for variety ([#25](https://github.com/maephisto666/MS-Rewards-Farmer/issues/25), [#26](https://github.com/maephisto666/MS-Rewards-Farmer/pull/26)).
- **Title fallback for unmapped activities**: When an activity has no mapped query, the activity title itself is used as the search query instead of skipping it. No points are lost for unmapped activities.

### Changed

- Localized activity files (`en.py`, `es.py`, `fr.py`, `it.py`) converted from `str` to `list[str]` values.

## [3.4.8] - 2026-05-17

### Fixed

- Skip cooldown for unmapped search activities that have the `isExploreOnBingTask` attribute, avoiding wasted time on activities without a mapped query ([#21](https://github.com/maephisto666/MS-Rewards-Farmer/issues/21), [#24](https://github.com/maephisto666/MS-Rewards-Farmer/pull/24)).
- Replaced `sleep(2)` before search submission with an explicit `WebDriverWait` for the `b_results` element, making activity completion more reliable regardless of network conditions ([#19](https://github.com/maephisto666/MS-Rewards-Farmer/issues/19)).
- Added debug logging for activity attribute keys and summary log of unmapped activities at end of run.

## [3.4.7] - 2026-04-25

### Fixed

- Login flow now handles both OTP page variants (black and white) reported by users on different machines, including the `80041032` "password required" error and a wider set of OTP input/submit selectors ([#22](https://github.com/maephisto666/MS-Rewards-Farmer/pull/22)).

## [3.4.6] - 2026-04-03

### Changed

- Added explicit PyPI registry for Python dependencies in `pyproject.toml`.

## [3.4.5] - 2026-04-01

### Fixed

- Proactively dismiss cookie consent banner on rewards page before interacting with dashboard elements.
- Use JavaScript click as fallback when element click is intercepted ([#18](https://github.com/maephisto666/MS-Rewards-Farmer/pull/18)).

## [3.4.4] - 2026-03-25

### Fixed

- Fixed `TypeError: 'NoneType' object is not subscriptable` in punch cards when `promotionalItem` is null ([#17](https://github.com/maephisto666/MS-Rewards-Farmer/issues/17)).

## [3.4.3] - 2026-03-24

### Fixed

- Login flow now correctly handles accounts without 2FA by recognizing post-login dialogs right after password submission, preventing unnecessary timeouts.

## [3.4.2] - 2026-03-19

### Fixed

- Browser language and geolocation are now independent settings. The `-l` flag accepts any language code (`en`, `de`, `en-US`, `de-DE`, etc.) and is applied directly to Chrome's language preferences, without being concatenated with the geolocation. This allows combinations like English language in Netherlands (`-l en -g NL`).

## [3.4.1] - 2026-03-10

### Fixed

- Login flow was broken due to an unmanaged redirect.


## [3.4.0] - 2026-03-06

### Changed

- Updated README: project is now in a working state after 2+ weeks of testing.
- Updated `createEmptyConfig` template with sensible defaults (cooldown, browser language/geolocation,
  retries) and removed apprise URL placeholder.
- Used `rewards.bing.com/` instead of `/Signin/` in `isLoggedIn()` fallback.

### Removed

- Removed `.github/FUNDING.yml` (referenced upstream maintainers).

## [3.3.1] - 2026-03-01

### Fixed

- Removed redundant 10-15s sleep between searches (cooldown already provides delay).
- Fixed `IndexError` when trend shelf is exhausted during search retries; trends are now
  reloaded automatically via extracted `_loadTrends()` method.
- Rounded retry sleep times to whole seconds for cleaner log output.

## [3.3.0] - 2026-03-01

### Changed

- **Login flow rewrite**: Replaced sequential try/except blocks with `EC.any_of` for faster,
  locale-independent detection across all login steps (email, password, 2FA, post-login dialogs).
- **Post-login dialog handling**: New `_handle_post_login_dialogs` loop (up to 5 attempts)
  handles HTTP errors, passkey enrollment, "Keep me signed in", "Stay signed in?", and
  "Is your security info still accurate?" dialogs automatically.
- **Dynamic OTP field lookup**: Finds the TOTP input by CSS selector inside `OneTimeCodeViewForm`
  instead of hardcoding a dynamic element ID.
- **Search effectiveness tracking**: `bingSearch()` now returns a bool; `bingSearches()` gives
  up early when searches stop being counted instead of looping indefinitely.
- **ReadToEarn stuck detection**: OAuth login wait loop now raises after 10 seconds instead of
  looping forever.
- **PunchCards CTA reliability**: New `_visit_offer_cta()` navigates directly via href for
  urlreward (same tab, avoids new-tab issues). New `_click_offer_cta_new_tab()` scrolls CTA
  into view and forces `target="_blank"` for quizzes.
- Switched to dashboard data source (`PREFER_BING_INFO=False`) to fix `KeyError: 'PCSearch'`
  from unreliable Bing API endpoint.
- Default `formatNumber` decimals changed from 2 to 0 (points are whole numbers).
- Login cleanup: deduplicated `check_locked_user`/`check_banned_user` calls, moved assert
  after `execute_login()` only.

### Removed

- Removed passwordless login flow (unused).
- Removed `contextlib` import from `login.py`.
- Removed `.idea` directory from version control.

## [3.2.0] - 2026-02-25

### Added

- Virtual CTAP2 authenticator to bypass native WebAuthn/passkey dialogs. Prevents OS-level
  prompts like "Create a passkey" from interrupting the bot.

## [3.1.0] - 2026-02-23

### Added

- `-totp`/`--totp` CLI parameter to pass a TOTP secret for 2FA (optional, only used with `-em` and `-pw`).

### Changed

- **Migrated to [uv](https://docs.astral.sh/uv/)** as the package manager, replacing pip/venv.
- Added `pyproject.toml` and `uv.lock` for reproducible dependency management.
- Added `.python-version` (3.12).
- Updated Dockerfile to `python:3.12-slim` with uv instead of pip.
- Updated README.md with uv-based installation instructions.
- Pinned `setuptools<81` to preserve `pkg_resources` required by `selenium-wire`.

### Removed

- Removed `requirements.txt` and `requirements-dev.txt` (superseded by `pyproject.toml`).

## [3.0.0] - 2026-02-18

### Changed

- **Repository takeover**: The upstream [klept0/MS-Rewards-Farmer](https://github.com/klept0/MS-Rewards-Farmer) was
  archived in January 2026. This fork continues active development.
- **Branch consolidation**: Renamed `develop` to `main` and set it as the default branch.
  The old `master` branch has been deleted. All history is preserved in git.
- **Deleted stale branches**:
  - `hotfix/MS-Rewards-Farmer-180` -- 303 commits behind master, referenced code that no longer exists.
  - `dependabot/pip/develop/apprise-approx-eq-1.9.6` -- superseded by current dependency versions.
  - `dependabot/pip/develop/psutil-approx-eq-7.2.1` -- superseded by current dependency versions.
  - `camoufox-test` -- experimental Camoufox browser integration. Captured in [ROADMAP.md](ROADMAP.md) for future
    consideration.
- **Kept for reference**: `feat/better-activities` contains activity handling improvements to be evaluated. Captured
  in [ROADMAP.md](ROADMAP.md).
- Updated [README.md](README.md) with project history and simplified contributing guidelines.

## [2.0.0] - 2025-04-08

### Added

- Consolidated all language-specific data into a single dictionary for `localized_activities`, simplifying management and improving performance.
- New activity handling.
- Added country and language code validation functions and updated browser geolocation handling.
- Added configuration options in `config.yaml` for activity handling and error notifications:
  - `apprise.notify.incomplete-activity` for incomplete activity notifications.
  - `apprise.notify.login-code` for login with phone code notifications.
- Added reset functionality to delete session files and terminate Chrome processes.
- Added CODEOWNERS file for repository management.
- Added Docker build for easier deployment and execution.
- Added `run.ps1` script with the following features:
  - Automatic detection of Python installations or virtual environments.
  - Retry logic for running the main script with configurable maximum attempts.
  - Automatic cleanup of Chrome processes and session files on failure.
  - Support for updating the script via Git if in a Git repository.
  - Command-line options for customization, including Python path, script directory, and session folder.

### Changed

- Improved retry logic in `getBingInfo` and updated backoff factor configuration.
- Updated `config.yaml` to enhance logging and error reporting configurations.
- Refactored activity handling to use localized titles and queries.
- Improved logging for activity completion, error reporting, and localization warnings.
- Enhanced JSON response handling in `utils.py` and updated parameters in `run.ps1`.
- Replaced `accounts.json` with account information now stored in `config.yaml` for better configuration management.
- Adjusted cooldowns and wait times for better performance.

### Fixed

- Fixed issues with quiz completion logic for "This or That" and "ABC" activities.
- Addressed edge cases where activities were incorrectly marked as incomplete.
- Fixed activities containing non-breakable spaces in their names.
- Fixed Google Trends API integration and improved trend keyword handling.
- Fixed click handling in `activities.py` to use the correct answer element.
- Fixed issue related to mobile search for level 1 users.
- Fixed Apprise notification error.
- Fixed exit code to return `exit 1` on errors instead of `exit 0`.

### Removed

- Removed unused imports and deprecated classes for cleaner codebase.
- Removed `MS_reward.bat` in favor of the more robust `run.ps1` script.
- Removed `config-private.yaml` in favor of consolidating configurations into `config.yaml`.
- Removed password logging.

### Other

- Added locked/banned user detection.
- Skipped un-doable activities.

## [1.1.0] - 2024-08-30

### Added

- Promotions/More activities
  - Expand your vocabulary
  - What time is it?

## [1.0.1] - 2024-08-25

### Fixed

- [AssertionError from apprise.notify(title=str(title), body=str(body))](https://github.com/klept0/MS-Rewards-Farmer/issues)

## [1.0.0] - 2024-08-23

### Removed

- `apprise.urls` from [config.yaml](config.yaml)
  - This now lives in `config-private.yaml`, see [.template-config-private.yaml](.template-config-private.yaml) on how
    to configure
  - This prevents accidentally leaking sensitive information since `config-private.yaml` is .gitignore'd

### Added

- Support for automatic handling of logins with 2FA and for passwordless setups:
  - Passwordless login is supported in both visible and headless mode by displaying the code that the user has to select
    on their phone in the terminal window
  - 2FA login with TOTPs is supported in both visible and headless mode by allowing the user to provide their TOTP key
    in `accounts.json` which automatically generates the one time password
  - 2FA login with device-based authentication is supported in theory, BUT doesn't currently work as the undetected
    chromedriver for some reason does not receive the confirmation signal after the user approves the login
- Completing quizzes started but not completed in previous runs
- Promotions/More activities
  - Find places to stay
  - How's the economy?
  - Who won?
  - Gaming time

### Changed

- Incomplete promotions Apprise notifications
  - How incomplete promotions are determined
  - Batched into single versus multiple notifications
- Full exception is sent via Apprise versus just error message

### Fixed

- Promotions/More activities
  - Too tired to cook tonight?
- [Last searches always timing out](https://github.com/klept0/MS-Rewards-Farmer/issues/172)
- [Quizzes don't complete](https://github.com/klept0/MS-Rewards-Farmer/issues)

## [0.2.1] - 2024-08-13

### Fixed

- [Fix ElementNotInteractableException](https://github.com/klept0/MS-Rewards-Farmer/pull/176)

## [0.2.0] - 2024-08-09

### Added

- Initial release of the Python script:
  - Generates a Task Scheduler XML file
  - Allows users to choose between Miniconda, Anaconda, and Local Python
  - Prompts users to input the name of their environment (if using Miniconda or Anaconda)
  - Uses the script directory as the output path
  - Default trigger time is set to 6:00 AM on a specified day, with instructions to modify settings after importing to
    Task Scheduler
  - Includes a batch file (`MS_reward.bat`) for automatic execution of the Python script

### Fixed

- [Error when trends fail to load](https://github.com/klept0/MS-Rewards-Farmer/issues/163)

## [0.1.0] - 2024-07-27

### Added

- New [config.yaml](config.yaml) options
  - `retries`
    - `base-delay-in-seconds`: how many seconds to delay
    - `max`: the max amount of retries to attempt
    - `strategy`: method to use when retrying, can be either:
      - `CONSTANT`: the default; a constant `base-delay-in-seconds` between attempts
      - `EXPONENTIAL`: an exponentially increasing `base-delay-in-seconds` between attempts
  - `apprise.summary`: configures how results are summarized via Apprise, can be either:
    - `ALWAYS`: the default, as it was before, how many points were gained and goal percentage if set
    - `ON_ERROR`: only sends email if for some reason there's remaining searches
    - `NEVER`: never send summary
- Apprise notification if activity isn't completed/completable
- Support for more activities
- New arguments (see [readme](README.md#launch-arguments) for details)
- Some useful JetBrains config
- More logging
- Config to make `requests` more reliable
- More checks for bug report
- Me, cal4, as a sponsoree

### Changed

- More reliable searches and closer to human behavior
- When logger is set to debug, doesn't include library code now
- Line endings to LF

### Removed

- Calls to close all Chrome processes

### Fixed

- [Error when executing script from .bat file](https://github.com/klept0/MS-Rewards-Farmer/issues/113)
- [\[BUG\] AttributeError: 'Browser' object has no attribute 'giveMeProxy'](https://github.com/klept0/MS-Rewards-Farmer/issues/115)
- [\[BUG\] driver.quit causing previous issue of hanging process with heavy load on cpu](https://github.com/klept0/MS-Rewards-Farmer/issues/136)
- Login
- Errors when [config.yaml](config.yaml) doesn't exist
- General reliability and maintainability fixes

## [0.0.0] - 2023-03-05

### Added

- Farmer and lots of other things, but gotta start a changelog somewhere!
