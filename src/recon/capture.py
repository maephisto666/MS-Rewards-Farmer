"""
Framework-agnostic evidence capture and report logic.

This module has NO automation library imports (no Selenium, no Playwright).
It receives plain Python values (strings, dicts, bytes) and produces reports.
Switching the automation layer (Selenium → Playwright) requires only changing
__main__.py — this module stays untouched.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable


# ---------------------------------------------------------------------------
# JS fingerprint — injected via execute_script / page.evaluate
# The function signature: execute_js(js_string) -> Any
# ---------------------------------------------------------------------------

JS_FINGERPRINT = """
return (function() {
    var hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
    var reactVersion = null;
    if (hook && hook.renderers && hook.renderers.size > 0) {
        hook.renderers.forEach(function(r) {
            if (!reactVersion && r.version) reactVersion = r.version;
        });
    }
    if (!reactVersion && window.React) reactVersion = window.React.version;

    var isNext = !!(window.__NEXT_DATA__ || window.next);
    var nextVersion = (window.next && window.next.version) || null;

    var dashboardExists = typeof window.dashboard !== 'undefined';
    var dashboardPreview = null;
    if (dashboardExists) {
        try { dashboardPreview = JSON.stringify(window.dashboard).slice(0, 2000); }
        catch(e) { dashboardPreview = '[error: ' + e.message + ']'; }
    }

    var configExists = typeof window.$Config !== 'undefined';
    var configPreview = null;
    if (configExists) {
        try { configPreview = JSON.stringify(window.$Config).slice(0, 500); }
        catch(e) { configPreview = '[error]'; }
    }

    var interesting = [];
    var pat = /^(reward|dashboard|\\$Config|ServerData|__NEXT|__APP|brs|ms_rewards)/i;
    try {
        Object.keys(window).forEach(function(k) {
            if (pat.test(k)) interesting.push(k);
        });
    } catch(e) {}

    return {
        react:    { detected: !!(reactVersion || (hook && hook.renderers && hook.renderers.size > 0)), version: reactVersion },
        next_js:  { detected: isNext, version: nextVersion },
        angular:  { detected: !!(window.ng || window.angular) },
        vue:      { detected: !!(window.Vue || window.__vue_app__) },
        dashboard_global: { exists: dashboardExists, preview: dashboardPreview },
        dollar_config:    { exists: configExists,   preview: configPreview },
        interesting_globals: interesting,
        page_title:           document.title,
        page_url:             window.location.href,
        document_ready_state: document.readyState
    };
})()
"""

# ---------------------------------------------------------------------------
# Network request processing
# ---------------------------------------------------------------------------

# Static asset extensions to skip — we only want API calls
_ASSET_EXTS = frozenset(
    ".js .css .woff .woff2 .ttf .otf .eot .png .jpg .jpeg .gif .ico .svg .webp .map".split()
)

# Known CDN / telemetry domains to skip
_SKIP_DOMAIN_FRAGMENTS = (
    "cdn.", "fonts.googleapis", "fonts.gstatic", "doubleclick", "google-analytics",
    "googletagmanager", "clarity.ms", "bat.bing", "c.clarity", "adservice",
)

# Cookie names that must be redacted (value replaced with <redacted:N>)
_AUTH_COOKIE_PAT = re.compile(
    r"^(ESTSAUTH|MSPAuth|RPSAuth|PPAuth|WLSSC|_U$|MUID|SRCHUID|MSCC|OIDI)",
    re.IGNORECASE,
)

# Header names whose values are always redacted
_REDACT_HEADERS = frozenset(
    ["authorization", "cookie", "set-cookie", "x-ms-request-root", "x-ms-client-session-id"]
)

# JWT pattern to scrub from response bodies
_JWT_PAT = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")


def _is_asset_url(url: str) -> bool:
    path = url.split("?")[0].lower()
    return any(path.endswith(ext) for ext in _ASSET_EXTS)


def _is_skippable_domain(url: str) -> bool:
    return any(frag in url.lower() for frag in _SKIP_DOMAIN_FRAGMENTS)


def redact_headers(headers: dict) -> dict:
    """Replace sensitive header values with <redacted>."""
    return {
        k: "<redacted>" if k.lower() in _REDACT_HEADERS else v
        for k, v in (headers or {}).items()
    }


def _try_decode_body(body: bytes, content_type: str) -> str | None:
    """Decode response body only for small JSON responses; skip everything else."""
    if not body or "json" not in content_type.lower():
        return None
    if len(body) > 100_000:
        return f"<truncated: {len(body)} bytes>"
    try:
        text = body.decode("utf-8", errors="replace")
        text = _JWT_PAT.sub("<redacted-jwt>", text)
        return text[:5000] if len(text) > 5000 else text
    except Exception:
        return None


def process_network_requests(raw_requests: Iterable[Any]) -> list[dict]:
    """
    Filter and redact a collection of captured network requests.

    raw_requests must be iterable objects with attributes:
        .url (str), .method (str), .headers (dict),
        .response (object with .status_code int, .headers dict, .body bytes) | None

    This shape matches selenium-wire Request objects.  When switching to
    Playwright, wrap page events in a compatible namedtuple/dataclass before
    calling this function — the logic here stays unchanged.
    """
    out = []
    for req in raw_requests:
        url = getattr(req, "url", "") or ""
        if _is_asset_url(url) or _is_skippable_domain(url):
            continue

        resp = getattr(req, "response", None)
        content_type = ""
        body_text = None
        status = None
        if resp:
            status = getattr(resp, "status_code", None)
            resp_headers = getattr(resp, "headers", {}) or {}
            content_type = resp_headers.get("Content-Type", resp_headers.get("content-type", ""))
            body_text = _try_decode_body(getattr(resp, "body", b"") or b"", content_type)

        out.append({
            "url": url,
            "method": getattr(req, "method", "?"),
            "request_headers": redact_headers(getattr(req, "headers", {}) or {}),
            "status": status,
            "content_type": content_type,
            "body": body_text,
        })
    return out


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------

def write_evidence(
    out_dir: Path,
    url: str,
    page_source: str,
    screenshot_bytes: bytes | None,
    fingerprint: dict | None,
    network_requests: list[dict],
) -> None:
    """Write all captured evidence to out_dir (created with restrictive perms)."""
    old_mask = os.umask(0o077)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    finally:
        os.umask(old_mask)

    manifest = {
        "url": url,
        "fingerprint": fingerprint,
        "network_summary": _network_summary(network_requests),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )

    if page_source:
        source_path = out_dir / "page_source.html"
        source_path.write_text(page_source[:2_000_000], encoding="utf-8")

    if screenshot_bytes:
        (out_dir / "screenshot.png").write_bytes(screenshot_bytes)

    if network_requests:
        (out_dir / "network_requests.json").write_text(
            json.dumps(network_requests, indent=2, default=str), encoding="utf-8"
        )


def _network_summary(reqs: list[dict]) -> dict:
    domains: dict[str, int] = {}
    api_paths: list[str] = []
    for r in reqs:
        url = r.get("url", "")
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            domains[domain] = domains.get(domain, 0) + 1
            if "json" in (r.get("content_type") or "").lower() or r.get("body"):
                api_paths.append(parsed.path)
        except Exception:
            pass
    return {
        "total_requests": len(reqs),
        "domains": domains,
        "json_api_paths": api_paths[:50],
    }


# ---------------------------------------------------------------------------
# Terminal summary
# ---------------------------------------------------------------------------

def write_recon_summary_md(
    path: Path,
    account_email: str,
    login_ok: bool,
    results: list[dict],
    rsc_data,           # DashboardData | None  (avoid importing src.rsc here)
    rsc_errors: list[str],
) -> None:
    """Write a human-readable SUMMARY.md to path."""
    from datetime import datetime, timezone

    lines: list[str] = []
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines += [
        "# MS Rewards Recon Summary",
        "",
        f"**Date:** {ts}  ",
        f"**Account:** {account_email}  ",
        f"**Login:** {'OK' if login_ok else 'FAILED'}  ",
        "",
    ]

    # --- Framework fingerprint from first probed URL ---
    first = next((r for r in results if r.get("fingerprint")), None)
    if first:
        fp = first["fingerprint"]
        lines += ["## Framework", ""]
        lines += ["| | |", "|---|---|"]
        r_info = fp.get("react", {})
        nj_info = fp.get("next_js", {})
        dg_info = fp.get("dashboard_global", {})
        lines.append(f"| React | {'YES' if r_info.get('detected') else 'NO'} (v{r_info.get('version') or '?'}) |")
        lines.append(f"| Next.js | {'YES' if nj_info.get('detected') else 'NO'} (v{nj_info.get('version') or '?'}) |")
        lines.append(f"| window.dashboard | {'YES' if dg_info.get('exists') else 'NO'} |")
        interesting = fp.get("interesting_globals", [])
        if interesting:
            lines.append(f"| Interesting globals | `{'`, `'.join(interesting[:10])}` |")
        lines.append(f"| Page title | {fp.get('page_title', '')} |")
        lines.append(f"| Final URL | {first['final_url']} |")
        lines.append("")

    # --- RSC Dashboard data ---
    lines += ["## Dashboard (RSC)", ""]
    if rsc_errors:
        for err in rsc_errors:
            lines.append(f"> ⚠️ {err}")
        lines.append("")
        lines.append("Check `page_source.html` in the evidence directory for the raw HTML.")
        lines.append("")
    if rsc_data is not None:
        lines += ["| Field | Value |", "|---|---|"]
        lines.append(f"| Balance | {rsc_data.balance:,} pts |")
        lines.append(f"| Level | {rsc_data.level} |")
        lines.append(
            f"| Activities | {rsc_data.activities_remaining} remaining "
            f"/ {rsc_data.activities_requirement} required "
            f"(progress: {rsc_data.activities_progress}) |"
        )
        claim_cell = f"**{rsc_data.point_claim_points} pts — ready to claim**" if rsc_data.point_claim_points else "none"
        lines.append(f"| Streak bonus | {claim_cell} |")
        lines.append("")

        if rsc_data.daily_set_items:
            lines += ["## Daily Set Items", ""]
            from datetime import date as _date
            today_str = _date.today().strftime("%m/%d/%Y")
            lines += [
                "| # | Date | Type | Title | Pts | Done | Locked | Notes |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for i, item in enumerate(rsc_data.daily_set_items, 1):
                done = "✓" if item.is_completed else ""
                locked = "🔒" if item.is_locked else ""
                title = item.title or item.offer_id or f"item-{i}"
                atype = item.activity_type
                date_cell = item.date
                if item.date == today_str:
                    date_cell = f"**{item.date}** ← today"
                if atype == "BING_QUIZ":
                    notes = f"`{item.quiz_key}`" if item.quiz_key else f"form={item.form_code}"
                elif atype == "REFERRAL":
                    notes = "skip — no automation"
                else:
                    notes = f"form=`{item.form_code}`" if item.form_code else ""
                lines.append(
                    f"| {i} | {date_cell} | {atype} | {title} | {item.points} | {done} | {locked} | {notes} |"
                )
            lines.append("")
        else:
            lines += ["## Daily Set Items", "", "_No items parsed._", ""]

    # --- URL probes ---
    lines += ["## URL Probes", ""]
    for r in results:
        arrow = f" → {r['final_url']}" if r.get("redirected") else ""
        lines.append(f"- `{r['probed_url']}`{arrow}")
    lines.append("")

    # --- Issues ---
    issues: list[str] = []
    if not login_ok:
        issues.append("Login failed — evidence captured at login_failure/")
    issues.extend(rsc_errors)
    if issues:
        lines += ["## Issues", ""]
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(url: str, fingerprint: dict | None, network_requests: list[dict], out_dir: Path) -> None:
    def _yn(v: bool) -> str:
        return "YES" if v else "NO"

    print()
    print("=" * 60)
    print("  RECON SUMMARY")
    print("=" * 60)
    print(f"  Final URL      : {url}")

    if fingerprint:
        r = fingerprint.get("react", {})
        print(f"  React          : {_yn(r.get('detected', False))}  version={r.get('version') or 'unknown'}")
        nj = fingerprint.get("next_js", {})
        print(f"  Next.js        : {_yn(nj.get('detected', False))}  version={nj.get('version') or 'N/A'}")
        dg = fingerprint.get("dashboard_global", {})
        print(f"  window.dashboard: {_yn(dg.get('exists', False))}", end="")
        if dg.get("exists") and dg.get("preview"):
            print(f"  (first 80 chars: {dg['preview'][:80]})")
        else:
            print()
        print(f"  Interesting globals: {fingerprint.get('interesting_globals', [])}")
        print(f"  Page title     : {fingerprint.get('page_title', '')}")

    summary = _network_summary(network_requests)
    print(f"  Network API calls: {summary['total_requests']} captured (assets excluded)")
    if summary["domains"]:
        for domain, count in sorted(summary["domains"].items(), key=lambda x: -x[1])[:8]:
            print(f"    {count:3}  {domain}")
    if summary["json_api_paths"]:
        print(f"  JSON API paths ({len(summary['json_api_paths'])}):")
        for p in summary["json_api_paths"][:20]:
            print(f"    {p}")

    print(f"  Evidence dir   : {out_dir}")
    print("=" * 60)
    print()
