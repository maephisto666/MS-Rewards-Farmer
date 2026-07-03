# /recon — Rewards page recon

Run the recon harness to log in and capture evidence about the current state
of the Microsoft Rewards page.

## Usage

```
/recon [--email EMAIL] [--password PASS] [--totp SECRET] [--visible] [--out DIR]
```

Omit `--email`/`--password` to use the first account in `config.yaml`.
`--visible` opens a browser window (recommended when investigating login issues).

## What it does

1. Launches Chrome (via the existing `Browser` + `Login` stack)
2. Completes the full login flow
3. Probes `https://rewards.bing.com/` and `https://rewards.microsoft.com/`
4. For each URL, captures:
   - Final URL after any redirects
   - React / Next.js / Angular / Vue detection + version
   - Whether `window.dashboard` still exists (the old data source)
   - All non-asset network requests (JSON API calls filtered, auth redacted)
   - Full DOM dump and screenshot
5. Prints a terminal summary and writes full evidence to `logs/recon/<timestamp>/`

## Steps to run

Ask Claude Code to run this skill. It will execute:

```bash
uv run python -m src.recon [args]
```

## Interpreting results

Key things to look for in the output:

| Signal | Meaning |
|--------|---------|
| `React: YES` | Confirmed SPA — Selenium selectors likely ineffective |
| `window.dashboard: NOT FOUND` | Root cause of the July 2026 breakage confirmed |
| `Final URL` differs from probed URL | Bing → Microsoft redirect active |
| JSON API paths matching `/dapi/` | Old mobile API still reachable from desktop web |
| JSON API paths matching `/v1/`, `/api/`, `/graphql` | New API layer found |

After running, examine `logs/recon/<timestamp>/network_requests.json` for the
full list of API calls — these are the candidates for the new data layer.
