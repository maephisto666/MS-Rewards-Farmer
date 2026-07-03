"""
Recon harness (Selenium adapter): log in and capture evidence about the
current state of the Rewards page.

Phase 2 target questions:
  1. Is the new page a React SPA? What version?
  2. What API backs the dashboard? Same dapi, new API, or GraphQL?
  3. What URL does rewards.bing.com redirect to?
  4. Does window.dashboard still exist?
  5. Are the existing Bing info / dapi endpoints still reachable?

Usage:
    uv run python -m src.recon [OPTIONS]

NOTE — automation layer:
    This file is the Selenium-specific integration layer.  All evidence
    capture and report logic lives in capture.py and has NO automation
    imports.  When switching to Playwright, replace only this file and
    keep capture.py unchanged.
"""

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import click

# ---------------------------------------------------------------------------
# All src imports are LAZY (inside command functions).
# This avoids triggering src.utils.loadConfig() → argumentParser().parse_args()
# before click has processed its own args.
# ---------------------------------------------------------------------------

PROBE_URLS = [
    "https://rewards.bing.com/",
    "https://rewards.microsoft.com/",
]

SPA_SETTLE_SECONDS = 6


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="[RECON] %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _out_dir(base: str | None) -> Path:
    if base:
        return Path(base)
    # Import here to avoid module-level src import
    from src.utils import getProjectRoot
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return getProjectRoot() / "logs" / "recon" / ts


def _save_login_failure(driver, out_dir: Path) -> None:
    """Capture page state at the moment of login failure for diagnosis."""
    failure_dir = out_dir / "login_failure"
    failure_dir.mkdir(parents=True, exist_ok=True)
    try:
        png = driver.get_screenshot_as_png()
        (failure_dir / "screenshot.png").write_bytes(png)
        logging.info(f"Login-failure screenshot saved to {failure_dir}/screenshot.png")
    except Exception as exc:
        logging.warning(f"Could not take login-failure screenshot: {exc}")
    try:
        source = driver.page_source or ""
        (failure_dir / "page_source.html").write_text(source[:500_000], encoding="utf-8")
    except Exception as exc:
        logging.warning(f"Could not capture login-failure page source: {exc}")
    try:
        url = driver.current_url
        (failure_dir / "url.txt").write_text(url, encoding="utf-8")
        logging.info(f"Login failure URL: {url}")
    except Exception:
        pass


def _probe_url(driver, url: str, out_dir: Path) -> dict:
    """Navigate to url, wait for the SPA, and capture all evidence."""
    from src.recon.capture import JS_FINGERPRINT, process_network_requests, write_evidence

    logging.info(f"Navigating to {url} ...")

    # Clear previously captured requests (selenium-wire specific)
    try:
        del driver.requests
    except AttributeError:
        pass

    try:
        driver.get(url)
    except Exception as exc:
        logging.warning(f"driver.get({url}) raised: {exc}")

    final_url = driver.current_url
    if final_url != url:
        logging.info(f"  Redirected → {final_url}")

    logging.info(f"Waiting {SPA_SETTLE_SECONDS}s for SPA to settle ...")
    time.sleep(SPA_SETTLE_SECONDS)

    final_url = driver.current_url  # re-read after client-side redirects

    fingerprint = None
    try:
        fingerprint = driver.execute_script(JS_FINGERPRINT)
    except Exception as exc:
        logging.warning(f"JS fingerprint failed: {exc}")

    page_source = ""
    try:
        page_source = driver.page_source or ""
    except Exception as exc:
        logging.warning(f"page_source failed: {exc}")

    screenshot_bytes = None
    try:
        screenshot_bytes = driver.get_screenshot_as_png()
    except Exception as exc:
        logging.warning(f"Screenshot failed: {exc}")

    # Network requests (selenium-wire specific — replaceable with Playwright network events)
    raw_requests = []
    try:
        raw_requests = list(driver.requests)
    except AttributeError:
        logging.warning("driver.requests unavailable (selenium-wire not active?)")

    network = process_network_requests(raw_requests)

    slug = url.replace("https://", "").replace("/", "_").strip("_")
    evidence_dir = out_dir / slug
    write_evidence(evidence_dir, final_url, page_source, screenshot_bytes, fingerprint, network)

    return {
        "probed_url": url,
        "final_url": final_url,
        "redirected": final_url != url,
        "fingerprint": fingerprint,
        "network": network,
        "evidence_dir": evidence_dir,
    }


@click.command()
@click.option("--email",    "-e",  default=None, help="Account email (overrides config.yaml)")
@click.option("--password", "-p",  default=None, help="Account password (overrides config.yaml)")
@click.option("--totp",            default=None, help="TOTP secret for 2FA")
@click.option("--visible",  "-v",  is_flag=True, help="Show browser window (recommended)")
@click.option("--out",             default=None, help="Output directory (default: logs/recon/<ts>)")
@click.option("--config",   "-c",  default=None, help="config.yaml path")
@click.option("--debug",    "-d",  is_flag=True, help="Enable debug logging")
def main(email: str | None, password: str | None, totp: str | None,
         visible: bool, out: str | None, config: str | None, debug: bool) -> None:
    """Log in to Microsoft Rewards and capture evidence about the current page structure."""
    _setup_logging(debug)

    # All src imports happen here — after click has parsed its args
    from src.browser import Browser
    from src.login import Login, LoginError
    from src.recon.capture import print_summary
    from src.utils import CONFIG

    # Override config path if given
    if config:
        import os
        os.environ["MSRF_CONFIG"] = config  # not used yet; placeholder for future

    # Build a minimal account-like object from CLI args or fall back to config
    account = None
    if email and password:
        from src.utils import Config
        account = Config({"email": email, "password": password})
        if totp:
            account.totp = totp
    else:
        accounts = getattr(CONFIG, "accounts", []) or []
        if accounts:
            account = accounts[0]

    if account is None:
        click.echo(
            "No account found. Provide --email/--password or add an account to config.yaml.",
            err=True,
        )
        sys.exit(1)

    if visible:
        CONFIG.browser.visible = True

    out_dir = _out_dir(out)
    logging.info(f"Starting recon for {account.email}")
    logging.info(f"Output directory: {out_dir}")

    with Browser(mobile=False, account=account) as browser:
        driver = browser.webdriver

        logging.info("Running login flow ...")
        login_ok = False
        try:
            Login(browser).login()
            login_ok = True
        except Exception as exc:
            # The driver is still alive (login.py no longer closes it on error).
            # Capture a screenshot now so we can see exactly what state the page is in,
            # then continue with URL probes — we may actually be authenticated even if
            # the post-login verification selector is gone (e.g. after the July 2026 redesign).
            logging.warning(f"Login raised an exception: {exc}")
            logging.warning("Capturing login-failure screenshot and continuing with URL probes ...")
            _save_login_failure(driver, out_dir)

        if not login_ok:
            logging.info("Attempting URL probes despite login exception (may still be authenticated) ...")

        logging.info("Starting URL probes ...")

        results = []
        for url in PROBE_URLS:
            try:
                findings = _probe_url(driver, url, out_dir)
                results.append(findings)
            except Exception as exc:
                logging.error(f"Probe of {url} failed: {exc}")

        for r in results:
            print_summary(
                url=r["final_url"],
                fingerprint=r.get("fingerprint"),
                network_requests=r.get("network", []),
                out_dir=r["evidence_dir"],
            )


if __name__ == "__main__":
    main()
