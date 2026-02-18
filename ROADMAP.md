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
