# AGENTS.md

## Project overview

MS-Rewards-Farmer is a Python automation tool that uses Selenium to farm Microsoft Rewards points. It performs Bing searches (desktop and mobile), completes daily activities, punch cards, and read-to-earn tasks across one or more Microsoft accounts.

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
  __init__.py            # Public API: Browser, Login, PunchCards, Searches, ReadToEarn
  browser.py             # Selenium browser setup (desktop/mobile), session management
  login.py               # Microsoft account login with TOTP and virtual authenticator
  searches.py            # Bing search automation
  activities.py          # Daily activities completion
  punchCards.py          # Punch card completion
  readToEarn.py          # Read-to-earn task completion
  utils.py               # Config class (YAML), CLI arg parsing, Selenium helpers, Apprise wrapper
  constants.py           # REWARDS_URL, SEARCH_URL, VERSION
  remainingSearches.py   # Remaining searches data class
  userAgentGenerator.py  # User-agent string generation
  loggingColoredFormatter.py  # Colored terminal log formatter
localized_activities/    # Per-language activity definitions (en, es, fr, it)
test/                    # Unit tests (unittest + parameterized)
```

## Branching rules

- Always create a separate branch for code changes (e.g. `fix/`, `feat/`).
- Exceptions: documentation updates and version bumps can be committed directly to `main`.
- **Cleanup after merge**: PRs are **squash-merged**, and the remote branch is deleted
  automatically (`delete_branch_on_merge`). The local branch is left behind and, because
  squash-merging rewrites history, `git branch --merged` will **not** list it — so delete it
  with `git branch -D <branch>` (force), not `-d`. Then `git fetch --prune` to drop stale
  remote-tracking refs. Never delete `origin/feat/better-activities` (a kept reference branch).

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
  patch, `feat!:`/`BREAKING CHANGE` → major. `docs:`/`chore:`/`ci:`/etc. are hidden and do not
  trigger a release.
- **The repo is squash-merge only**, so a merged PR becomes a single commit whose subject is the
  **PR title**. That means the PR title's conventional prefix is what determines the release —
  keep PR titles conventional (e.g. `feat: ...`, `fix: ...`).

## Key conventions

- Configuration is loaded from `config.yaml` via the `Config` dict subclass in `src/utils.py`. `CONFIG` and `APPRISE` are module-level singletons.
- The `Browser` class is used as a context manager (`with Browser(...) as b:`).
- Searches is also a context manager.
- Logging uses Python's built-in `logging` module with a colored terminal formatter and a timed rotating file handler writing to `logs/`.
- Points data is tracked in `logs/points_data.csv` and `logs/previous_points_data.json`.

## Running the project

```sh
uv sync          # install all dependencies (add --no-dev to skip dev deps)
uv run python main.py          # run the bot
uv run python main.py -h       # show CLI help
uv run python main.py -C       # generate a config.yaml template
```

## Testing

```sh
uv run python -m pytest test/
```

Tests use `unittest` with `unittest.mock` and the `parameterized` library (dev dependency).

## Linting

Flake8 is configured in `.flake8` (max line length 88, compatible with Black formatting).
Pylint configuration is in `.pylintrc`.
