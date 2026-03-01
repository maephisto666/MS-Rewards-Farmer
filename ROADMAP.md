# Roadmap

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
