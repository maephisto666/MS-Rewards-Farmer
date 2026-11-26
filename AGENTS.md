# AGENTS.md

## Project overview

MS-Rewards-Farmer is a Python automation tool that uses Selenium to farm Microsoft Rewards points. It performs several tasks (e.g., Bing searches on web/mobile, completes daily activities, punch cards, and read-to-earn, etc.) across one or more Microsoft accounts.

## Tech stack

- **Python 3.12** (pinned in `.python-version`)
- **uv** for dependency management (`pyproject.toml` + `uv.lock`)
- **Selenium** with `undetected-chromedriver` for browser automation
- **Apprise** for notifications
- **PyYAML** for configuration
- **Docker** support via `Dockerfile` and `docker-compose.yml`

## Project structure

```
main.py                  # Entry point: account loop, logging setup, CSV export
src/
  browser.py             # Selenium browser setup (desktop/mobile), session management
  login.py               # Microsoft account login with TOTP and virtual authenticator
  searches.py            # Bing search automation
  trends.py              # Trending keyword pool for searches: CSV/RSS sources, JSON cache, back-off
  activities.py          # Daily set activities (dashboard card click → new tab wait)
  bonusPoints.py         # Streak bonus + banner bonus claiming
  punchCards.py          # Punch card stub (skipped — not exposed in RSC data model)
  quests.py              # Quests section of /earn: one step per quest and run (monthly quest, found by offer id)
  readToEarn.py          # Read-to-earn task completion
  rsc.py                 # Next.js RSC wire-format parser: DashboardData, DailySetItem, QuestPage
  utils.py               # Config class (YAML), CLI arg parsing, Selenium helpers, Apprise wrapper
  constants.py           # REWARDS_URL, SEARCH_URL
  userAgentGenerator.py  # User-agent string generation
  loggingColoredFormatter.py  # Colored terminal log formatter
localized_activities/    # Per-language activity definitions (en, es, fr, it)
test/                    # Unit tests (unittest + parameterized)
```

## Commit messages

All commits **must** follow [Conventional Commits](https://www.conventionalcommits.org/).
This is required — release-please derives version bumps and the CHANGELOG directly from commit
types and footers.

| Prefix | When to use | Release impact |
|---|---|---|
| `feat:` | New user-visible feature | minor bump |
| `fix:` | Bug fix | patch bump |
| `feat!:` / `fix!:` | Breaking change (or add `BREAKING CHANGE:` footer) | major bump |
| `refactor:` | Code restructure with no behaviour change | patch bump |
| `perf:` | Performance improvement | patch bump |
| `deps:` | **Every** change to the shipped dependencies: upgrades, pins, Dependabot PRs, manual or automated | patch bump |
| `revert:` | Revert a previous change | patch bump |
| `docs:` | Documentation only | none |
| `chore:` | Tooling, dependency, config updates | none |
| `ci:` | CI/CD pipeline changes | none |
| `build:` / `style:` / `test:` | Build tweaks, formatting, test additions or fixes | none |

Which types release is defined by `changelog-sections` in `release-please-config.json`: every
type that is not marked `"hidden": true` there lands in the CHANGELOG and opens (or updates)
a release PR. Keep this table in sync with that file.

**Format:**
```
<type>[optional scope]: <short imperative summary>

[optional body]

[optional footers, e.g. Co-Authored-By:]
```

Rules:
- Subject line: imperative mood, no capital first letter, no trailing period, ≤72 chars.
- Body/footers separated by a blank line.
- `BREAKING CHANGE: <description>` footer (or `!` suffix) triggers a major version bump.
- `docs:` / `chore:` / `ci:` / `build:` / `style:` / `test:` commits are hidden in the CHANGELOG
  and do **not** trigger a release by themselves. `refactor:`, `perf:`, `deps:` and `revert:`
  commits **do** (patch bump), even when the behaviour is unchanged.
- **Dependency changes always use `deps:`** (no scope, not `fix(deps):`), whoever makes them:
  Dependabot is configured to do the same, so the CHANGELOG stays consistent. Only dependencies
  used by development tooling use `chore:`. Both `deps:` and `fix(deps):` release, but
  `fix(deps):` files the entry under "Fixed" with a `**deps:**` scope, while `deps:` files it
  under "Changed" (`deps` and `refactor` share that section in `release-please-config.json`).
  Mention in the PR body when a dependency change fixes a security advisory.
- **Never commit or push unless explicitly asked.** Wait for the user to say "commit" or "push".

## Branching rules

- Always create a separate branch for every change (e.g. `fix/`, `feat/`, `docs/`, `ci/`).
- **`main` is protected by rulesets** (no bypass actors): the `dependency-review` check is
  required, and the branch cannot be deleted or force-pushed. A direct push to `main` is
  rejected, so documentation updates go through a PR as well (version bumps are made by
  release-please PRs). The check can take about two minutes to start after a push: wait for it
  before merging. If the check infrastructure itself is broken, an admin has to disable the
  `require-dependency-review` ruleset temporarily.
- **Cleanup after merge**: PRs are **squash-merged**, and the remote branch is deleted
  automatically (`delete_branch_on_merge`). The local branch is left behind and, because
  squash-merging rewrites history, `git branch --merged` will **not** list it — so delete it
  with `git branch -D <branch>` (force), not `-d`. Then `git fetch --prune` to drop stale
  remote-tracking refs.

## GitHub and pull requests

- The GitHub remote for this project is `git@github.com:maephisto666/MS-Rewards-Farmer.git`
  (the `origin` remote). Use the `gh` CLI to interact with it (issues, PRs, releases, tags).
- **This repository is a fork** of the archived upstream `klept0/MS-Rewards-Farmer`. Because
  of that, `gh` commands default to the *upstream parent*, not this fork.
- When opening a pull request, the branch **must merge into `main` on
  `maephisto666/MS-Rewards-Farmer`** — never the upstream parent. Always pass the repo and
  base explicitly so the PR is not accidentally opened against `klept0`:

  ```sh
  gh pr create --repo maephisto666/MS-Rewards-Farmer \
    --base main --head maephisto666:<branch> --title "..." --body "..."
  ```

- Likewise, scope read commands to this fork explicitly when ambiguity matters, e.g.
  `gh issue list --repo maephisto666/MS-Rewards-Farmer`. Git tags are visible via `git tag`
  or `gh api repos/maephisto666/MS-Rewards-Farmer/tags`; GitHub Releases via `gh release list`.

## Releases (automated via release-please)

Versioning, `CHANGELOG.md`, version bumps (`pyproject.toml`, `uv.lock`), git tags, and GitHub
Releases are all managed automatically by [release-please](https://github.com/googleapis/release-please)
(`.github/workflows/release-please.yml`). **Do not** edit `CHANGELOG.md` or bump versions by
hand — release-please derives them from [Conventional Commit](https://www.conventionalcommits.org/)
history.

How it works:

- On every push to `main`, release-please maintains a standing **release PR** that accumulates
  the next version bump and changelog. Merging that PR cuts the tag and GitHub Release.
- The version is derived from commit types since the last release: `feat:` → minor, `fix:` →
  patch (as are `refactor:`, `perf:`, `deps:` and `revert:`), `feat!:`/`BREAKING CHANGE` →
  major. `docs:`/`chore:`/`ci:`/`build:`/`style:`/`test:` are hidden and do not trigger a
  release.
- **The repo is squash-merge only**, so a merged PR becomes a single commit whose subject is the
  **PR title**. That means the PR title's conventional prefix is what determines the release —
  keep PR titles conventional (e.g. `feat: ...`, `fix: ...`).
- **release-please runs with the `RELEASE_PLEASE_TOKEN` repository secret** (a fine-grained
  personal access token limited to this repo, with Contents and Pull requests read/write),
  falling back to `GITHUB_TOKEN` if the secret is missing. PRs and pushes made with
  `GITHUB_TOKEN` do not start `pull_request` workflows on their own: they sit in
  `action_required` until someone clicks "Approve workflows to run", and are closed as failed
  when the PR is merged. With the token, the release PR is authored by the token owner and
  Dependency Review runs automatically on open and on every update. The token expires: rotate
  it with `gh secret set RELEASE_PLEASE_TOKEN --repo maephisto666/MS-Rewards-Farmer`.
- **Dependabot** (`.github/dependabot.yml`) is configured for the `uv` ecosystem against `main`.
  - **This repo is a fork, so Dependabot version updates must be enabled in the repository
    settings** (Settings > Advanced Security > Dependabot version updates). While they are
    off, GitHub does not apply `dependabot.yml` at all, not even to security updates: no
    ignores, no `deps:` prefix, no grouping.
  - **Version updates** run weekly, at most 3 open PRs at a time (`open-pull-requests-limit`),
    with minor and patch updates grouped into one PR. Titles start with `deps:` (or `chore:`
    for dev dependencies) so they follow the conventional-commit rules above; a merged `deps:`
    PR triggers a patch release.
  - **Security updates are not subject to that limit.** They have their own fixed limit of 10
    open PRs, so many can appear at once (7 on the first run). The `commit-message` and `ignore`
    settings also apply to them once the config is active: new security PRs carry the `deps:`
    prefix. The first security PRs, opened before the config was active, kept the default
    `chore(deps):` title and have to be retitled or closed.
  - **Ignores** (`dependency-name` and `versions` keys; `update-types` only affects version
    updates): `blinker`, `selenium-wire` and `undetected-chromedriver` (all versions, exact
    pins that `selenium-wire` depends on), `pyopenssl` >= 26.2, `cryptography` >= 48 and
    `setuptools` >= 81. They stop Dependabot from opening PRs for those versions, both
    version and security updates. They do **not** dismiss alerts: the alerts stay open until
    dismissed by hand, which was done for `cryptography` and `setuptools` ("tolerable risk"),
    tracked in #80 and #81.
  - Dependabot comment commands (`@dependabot ignore ...`) were not processed on some PRs
    (for example a minor-update PR). If a command gets no reply, report it instead of closing
    the PR by hand.
  - There is no test workflow on PRs yet, so check a dependency PR by hand (real login and a
    search) before merging it.
- Tags and releases created with that token would trigger tag-based workflows, so
  `build_push_docker_image.yml` is **manual only** (`workflow_dispatch`): it needs the
  `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets, which do not exist yet. Re-add its
  `push: tags` trigger once the Docker publishing is fixed.

## Key conventions

- Configuration is loaded from `config.yaml` via the `Config` dict subclass in `src/utils.py`. `CONFIG` and `APPRISE` are module-level singletons.
- The `Browser` class is used as a context manager (`with Browser(...) as b:`).
- `Searches` is also a context manager.
- Logging uses Python's built-in `logging` module with a colored terminal formatter and a timed rotating file handler writing to `logs/`.
- Points data is tracked in `logs/points_data.csv` and `logs/previous_points_data.json`.
- **Dashboard data** is read via `browser.utils.getDashboardData()` which calls `src/rsc.py` to parse the Next.js RSC wire format embedded in the page HTML. The result is a `DashboardData` dataclass (balance, level, daily set items, streak bonus points). Never hard-code IDs or selectors for data that is available in the RSC payload.
- **`pyopenssl` is pinned `<26.2`** because `selenium-wire` 5.1.0 (unmaintained) calls `OpenSSL.crypto.X509.get_extension`, which pyOpenSSL removed in 26.2.0. With a newer version its MITM proxy crashes on every HTTPS connection and Chrome fails with `net::ERR_CONNECTION_CLOSED`, so login never works. Do not lift the pin without replacing `selenium-wire` or re-testing a real login.
- **Chrome location**: `undetected_chromedriver` only looks for Chrome in the standard install folders. `browser.chrome-path` (or `--chrome-path`) overrides that, and `Browser.getChromeVersion()` reads the version from that same binary, so the chromedriver patch matches the browser that is launched.
- **Timing**: always use `WebDriverWait` on a concrete DOM/JS condition. Never use `time.sleep()` unless there is genuinely no observable condition and a comment explains why.
- **React Aria buttons** (`data-react-aria-pressable="true"`) require `ActionChains(driver).move_to_element(el).click().perform()`. A plain JS `execute_script("arguments[0].click()")` bypasses pointer-event handlers and will silently do nothing.

## Running the project

```sh
uv sync          # install all dependencies (add --no-dev to skip dev deps)
uv run python main.py          # run the bot
uv run python main.py -h       # show CLI help
uv run python main.py -C       # generate a config.yaml template
```

## Testing

```sh
uv run python -m unittest        # runs the whole suite via auto-discovery
```

Tests use `unittest` with `unittest.mock` and the `parameterized` library (dev dependency).
`pytest` is **not** a project dependency — `uv run python -m pytest test/` fails with
`No module named pytest`.

> **Never pass arguments to `unittest`.** `src/utils.py` builds `CONFIG` at import time by
> calling `argumentParser().parse_args()`, which reads the real `sys.argv`. Any extra
> argument is therefore swallowed by the bot's own CLI parser, which rejects it and calls
> `sys.exit(2)`:
>
> | Command | Result |
> |---|---|
> | `uv run python -m unittest` | 13 tests run |
> | `uv run python -m unittest discover -s test -v` | `SystemExit: 2` while importing each test module, reported as 2 errors |
> | `uv run python -m unittest test.test_utils` | argparse rejects `test.test_utils`, exits 2, no tests run |
>
> To run a subset, use `unittest.main(argv=[...])` inside a test module rather than the CLI.

## Linting

Flake8 is configured in `.flake8` (max line length 88, compatible with Black formatting).
Pylint configuration is in `.pylintrc`.
