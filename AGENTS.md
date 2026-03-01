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
