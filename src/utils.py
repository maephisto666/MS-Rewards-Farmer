import contextlib
import importlib
import json
import locale as pylocale
import logging
import random
import re
import shutil
import sys
import time
from argparse import Namespace, ArgumentParser, BooleanOptionalAction
from copy import deepcopy
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any, Self

import psutil
import pycountry
import requests
import yaml
from apprise import Apprise
from ipapi import ipapi
from ipapi.exceptions import RateLimited
from requests import Session, JSONDecodeError
from requests.adapters import HTTPAdapter
from selenium.common import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from urllib3 import Retry

from .constants import REWARDS_DASHBOARD_URL, REWARDS_EARN_URL, SEARCH_URL


class Config(dict):
    """
    A class that extends the built-in dict class to provide additional functionality
    (such as nested dictionaries and lists, YAML loading, and attribute access)
    to make it easier to work with configuration data.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = self.__class__(value)
            if isinstance(value, list):
                for i, v in enumerate(value):
                    if isinstance(v, dict):
                        value[i] = self.__class__(v)

    def __or__(self, other):
        new = deepcopy(self)
        for key in other:
            if key in new:
                if isinstance(new[key], dict) and isinstance(other[key], dict):
                    new[key] = new[key] | other[key]
                    continue
            if isinstance(other[key], dict):
                new[key] = self.__class__(other[key])
                continue
            if isinstance(other[key], list):
                new[key] = self.configifyList(other[key])
                continue
            new[key] = other[key]
        return new

    def __getattribute__(self, item):
        if item in self:
            return self[item]
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            value = self.__class__(value)
        if isinstance(value, list):
            value = self.configifyList(value)
        self[key] = value

    def __getitem__(self, item):
        if not isinstance(item, str) or not "." in item:
            return super().__getitem__(item)
        item: str
        items = item.split(".")
        found = super().__getitem__(items[0])
        for child_items in items[1:]:
            found = found.__getitem__(child_items)
        return found

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = self.__class__(value)
        if isinstance(value, list):
            value = self.configifyList(value)
        if not isinstance(key, str) or not "." in key:
            super().__setitem__(key, value)
            return
        item: str
        items = key.split(".")
        found = super().__getitem__(items[0])
        for item in items[1:-1]:
            found = found.__getitem__(item)
        found.__setitem__(items[-1], value)

    @classmethod
    def fromYaml(cls, path: Path) -> Self:
        if not path.exists() or not path.is_file():
            return cls()
        with open(path, encoding="utf-8") as f:
            yamlContents = yaml.safe_load(f)
            if not yamlContents:
                return cls()
            return cls(yamlContents)

    @classmethod
    def configifyList(cls, listToConvert: list) -> list:
        new = [None] * len(listToConvert)
        for index, item in enumerate(listToConvert):
            if isinstance(item, dict):
                new[index] = cls(item)
                continue
            if isinstance(item, list):
                new[index] = cls.configifyList(item)
                continue
            new[index] = item
        return new

    @classmethod
    def dictifyList(cls, listToConvert: list) -> list:
        new = [None] * len(listToConvert)
        for index, item in enumerate(listToConvert):
            if isinstance(item, cls):
                new[index] = item.toDict()
                continue
            if isinstance(item, list):
                new[index] = cls.dictifyList(item)
                continue
            new[index] = item
        return new

    def get(self, item, default=None):
        if not isinstance(item, str) or not "." in item:
            return super().get(item, default)
        item: str
        keys = item.split(".")
        found = super().get(keys[0], default)
        for key in keys[1:]:
            found = found.get(key, default)
        return found

    def toDict(self) -> dict:
        new = {}
        for key, value in self.items():
            if isinstance(value, self.__class__):
                new[key] = value.toDict()
                continue
            if isinstance(value, list):
                new[key] = self.dictifyList(value)
                continue
            new[key] = value
        return new


DEFAULT_CONFIG: Config = Config(
    {
        "apprise": {
            "enabled": True,
            "notify": {
                "incomplete-activity": True,
                "uncaught-exception": True,
                "login-code": True,
            },
            "summary": "ON_ERROR",
            "urls": [],
        },
        "browser": {
            "geolocation": None,
            "language": None,
            "visible": False,
            "proxy": None,
        },
        "logging": {
            "format": "%(asctime)s [%(levelname)s] %(message)s",
            "level": "INFO",
        },
        "retries": {"backoff-factor": 120, "max": 4, "strategy": "EXPONENTIAL"},
        "cooldown": {"min": 300, "max": 600},
        "channel": {
            "desktop": {"enabled": True},
            "mobile": {"enabled": True},
        },
        "accounts": [],
    }
)


class Utils:
    """
    A class that provides utility functions for Selenium WebDriver interactions.
    """

    def __init__(self, webdriver: WebDriver):
        self.webdriver = webdriver
        with contextlib.suppress(Exception):
            locale = pylocale.getlocale()[0]
            pylocale.setlocale(pylocale.LC_NUMERIC, locale)

    def waitUntilVisible(
        self, by: str, selector: str, timeToWait: float = 10
    ) -> WebElement:
        return WebDriverWait(self.webdriver, timeToWait).until(
            expected_conditions.visibility_of_element_located((by, selector))
        )

    def waitUntilClickable(
        self, by: str, selector: str, timeToWait: float = 10
    ) -> WebElement:
        return WebDriverWait(self.webdriver, timeToWait).until(
            expected_conditions.element_to_be_clickable((by, selector))
        )

    def checkIfTextPresentAfterDelay(self, text: str, timeToWait: float = 10) -> bool:
        time.sleep(timeToWait)
        text_found = re.search(text, self.webdriver.page_source)
        return text_found is not None

    def resetTabs(self) -> None:
        curr = self.webdriver.current_window_handle

        for handle in self.webdriver.window_handles:
            if handle != curr:
                self.webdriver.switch_to.window(handle)
                time.sleep(0.5)
                self.webdriver.close()
                time.sleep(0.5)

        self.webdriver.switch_to.window(curr)
        time.sleep(0.5)
        self.goToRewards()

    def goToRewards(self) -> None:
        self.webdriver.get(REWARDS_DASHBOARD_URL)
        # The page may redirect: rewards.bing.com/ → rewards.bing.com/dashboard
        assert self.webdriver.current_url.startswith(
            "https://rewards.bing.com/"
        ), f"Unexpected URL after navigating to Rewards: {self.webdriver.current_url}"
        self.dismissCookieBanner()

    def goToEarn(self) -> None:
        self.webdriver.get(REWARDS_EARN_URL)
        assert self.webdriver.current_url.startswith(
            "https://rewards.bing.com/"
        ), f"Unexpected URL after navigating to Earn: {self.webdriver.current_url}"
        self.dismissCookieBanner()

    def getEarnData(self):
        """Navigate to the /earn page and parse its RSC payload — this is where
        the 'Keep earning' activity cards live (issue #37)."""
        from src.rsc import parse_dashboard  # local import: avoids circular deps
        self.goToEarn()
        return parse_dashboard(self.webdriver.page_source)

    def dismissCookieBanner(self) -> None:
        """Dismiss the cookie consent banner if present."""
        selectors = [
            (By.CSS_SELECTOR, "#wcpConsentBannerCtrl button:first-child"),
            (By.CSS_SELECTOR, "#cookieConsentContainer button:first-child"),
            (By.ID, "bnp_btn_accept"),
        ]
        for by, value in selectors:
            try:
                buttons = self.webdriver.find_elements(by=by, value=value)
                if buttons:
                    logging.debug(f"[COOKIE BANNER] Found banner element with selector: {value}")
                    buttons[0].click()
                    logging.info("[COOKIE BANNER] Successfully dismissed cookie banner")
                    return
            except (ElementNotInteractableException, ElementClickInterceptedException) as e:
                logging.warning(f"[COOKIE BANNER] Found banner but failed to dismiss: {e}")
            except (NoSuchElementException, TimeoutException):
                pass
        logging.debug("[COOKIE BANNER] No cookie banner found")

    def goToSearch(self) -> None:
        self.webdriver.get(SEARCH_URL)

    def ensureBingSearchAuth(self) -> None:
        """Ensure www.bing.com is authenticated for search rewards (issue #36).

        On some accounts/sessions www.bing.com stays signed-out even though
        rewards.bing.com is logged in — searches then earn nothing and the
        PCSearch counter never appears. Opening the Bing Rewards flyout (and
        clicking 'Get Started' if the account isn't enrolled yet) re-authenticates
        www.bing.com. Whether it's needed is non-deterministic (Microsoft-side),
        so this checks the isRewardsUser signal and only acts when it's False.

        Never raises: on any failure searches simply proceed with the fallback,
        exactly as before.
        """
        try:
            self.webdriver.get("https://www.bing.com/")
            if self._isBingRewardsAuthenticated():
                logging.debug("[BING AUTH] www.bing.com already authenticated for search.")
                return

            logging.info(
                "[BING AUTH] www.bing.com not authenticated for search — opening "
                "Rewards flyout to re-authenticate..."
            )
            pill = self._findFirstVisible([
                (By.ID, "id_rc"),
                (By.CSS_SELECTOR, "[aria-label*='Reward']"),
                (By.CSS_SELECTOR, "a[href*='rewards']"),
            ])
            if pill is None:
                logging.warning(
                    "[BING AUTH] Rewards pill not found on www.bing.com "
                    "(e.g. mobile layout) — skipping; searches use the fallback."
                )
                return
            ActionChains(self.webdriver).move_to_element(pill).click().perform()
            time.sleep(4)

            # Unenrolled accounts show 'Get Started' in the flyout; already-enrolled
            # accounts show their points and just opening the flyout is enough.
            getStarted = self._findGetStarted()
            if getStarted is not None:
                logging.info("[BING AUTH] Clicking 'Get Started' to enrol...")
                ActionChains(self.webdriver).move_to_element(getStarted).click().perform()
                time.sleep(6)
                self.webdriver.switch_to.default_content()

            # Confirm the flip.
            self.webdriver.get("https://www.bing.com/")
            if self._isBingRewardsAuthenticated():
                logging.info("[BING AUTH] www.bing.com is now authenticated for search.")
            else:
                logging.warning(
                    "[BING AUTH] www.bing.com still not authenticated after opening the "
                    "flyout — searches may not count this run."
                )
        except Exception as exc:  # never break the search flow
            logging.warning("[BING AUTH] ensureBingSearchAuth failed (%s) — continuing.", exc)
            with contextlib.suppress(Exception):
                self.webdriver.switch_to.default_content()

    def _isBingRewardsAuthenticated(self) -> bool:
        try:
            return bool(self.getBingRewardsInfo().get("isRewardsUser"))
        except Exception:
            return False

    def _findFirstVisible(self, selectors):
        for by, sel in selectors:
            for el in self.webdriver.find_elements(by, sel):
                try:
                    if el.is_displayed():
                        return el
                except Exception:
                    continue
        return None

    def _findGetStarted(self):
        """Find a visible 'Get started' control in the main document or any iframe.
        The driver is left switched into the frame that owns the returned element
        (so the caller can click it); callers must switch_to.default_content()
        afterwards. Returns to default content when nothing is found."""
        xpath = (
            "//*[self::button or self::a or @role='button']"
            "[contains(normalize-space(.), 'et started')]"
        )
        self.webdriver.switch_to.default_content()
        for el in self.webdriver.find_elements(By.XPATH, xpath):
            if el.is_displayed():
                return el
        for frame in self.webdriver.find_elements(By.TAG_NAME, "iframe"):
            try:
                self.webdriver.switch_to.default_content()
                self.webdriver.switch_to.frame(frame)
                for el in self.webdriver.find_elements(By.XPATH, xpath):
                    if el.is_displayed():
                        return el
            except Exception:
                continue
        self.webdriver.switch_to.default_content()
        return None

    def getDashboardData(self):
        """
        Navigate to the Rewards dashboard and parse the RSC wire-format payload
        embedded in the page HTML. Returns a DashboardData object.

        The old window.dashboard global is gone as of the 2026 revamp (Next.js
        App Router). All data now arrives server-rendered in
        self.__next_f.push() inline scripts.
        """
        from src.rsc import parse_dashboard, DashboardData  # local import: avoids circular deps
        self.goToRewards()
        return parse_dashboard(self.webdriver.page_source)

    def getActivities(self):
        """Return today's daily-set items from the RSC dashboard.

        Only today's items have clickable anchors; future days are in the RSC
        payload but not rendered as links until their date arrives.
        """
        return self.getDashboardData().todays_daily_set()

    def getBingRewardsInfo(self) -> Any:
        session = makeRequestsSession()
        retries = CONFIG.retries.max
        backoff_factor = CONFIG.get("retries.backoff-factor")

        for cookie in self.webdriver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])

        for attempt in range(retries):
            try:
                response = session.get(
                    "https://www.bing.com/rewards/panelflyout/getuserinfo"
                )
                assert (
                    response.status_code == requests.codes.ok
                )  # pylint: disable=no-member
                # Bing sometimes sends UTF-8 JSON without a usable charset header.
                # Decode it explicitly so localized goal titles are not mojibake.
                response.encoding = "utf-8"
                data = response.json()
                logging.debug(
                    "getBingRewardsInfo: isRewardsUser=%s userInfo.balance=%s flyoutResult.userStatus.availablePoints=%s",
                    data.get("isRewardsUser"),
                    data.get("userInfo", {}).get("balance"),
                    data.get("flyoutResult", {}).get("userStatus", {}).get("availablePoints"),
                )
                return data
            except (JSONDecodeError, AssertionError) as e:
                logging.info(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    sleep_time = backoff_factor * (2**attempt)
                    logging.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    # noinspection PyUnboundLocalVariable
                    logging.debug(response)
                    raise

    def isLoggedIn(self) -> bool:
        try:
            if self.getBingRewardsInfo()["isRewardsUser"]:
                return True
        except Exception:
            pass
        # Fallback: navigate and check for dashboard redirect
        self.webdriver.get("https://rewards.bing.com/")
        with contextlib.suppress(TimeoutException):
            WebDriverWait(self.webdriver, 10).until(
                lambda d: "/dashboard" in d.current_url or "welcome" in d.current_url
            )
        return "/dashboard" in self.webdriver.current_url

    def getAccountPoints(self) -> int:
        # RSC balance is always accurate; getBingRewardsInfo may return 0 in some regions.
        # getDashboardData() navigates to /dashboard and parses the RSC payload.
        return self.getDashboardData().balance

    def getGoalPoints(self) -> int:
        try:
            return self.getBingRewardsInfo()["flyoutResult"]["userGoal"]["price"]
        except (KeyError, TypeError):
            return 0

    def getGoalTitle(self) -> str:
        try:
            return self.getBingRewardsInfo()["flyoutResult"]["userGoal"]["title"]
        except (KeyError, TypeError):
            return ""

    def tryDismissAllMessages(self) -> None:
        byValues = [
            (By.ID, "iLandingViewAction"),
            (By.ID, "iShowSkip"),
            (By.ID, "iNext"),
            (By.ID, "iLooksGood"),
            (By.ID, "idSIButton9"),
            (By.ID, "bnp_btn_accept"),
            (By.ID, "acceptButton"),
            (By.CLASS_NAME, "dashboardPopUpPopUpSelectButton"),  # seems to be unclickable
            (By.CSS_SELECTOR, "#cookie-banner button:first-child"),
            (By.CSS_SELECTOR, "#wcpConsentBannerCtrl button:first-child"),
        ]
        dismissButtons = []
        for by, value in byValues:
            with contextlib.suppress(NoSuchElementException, TimeoutException):
                dismissButtons.extend(self.webdriver.find_elements(by=by, value=value))
        for dismissButton in dismissButtons:
            try:
                dismissButton.click()
                logging.debug(f"[DISMISS] Dismissed an element by clicking on {dismissButton.get_attribute('outerHTML')}")
            except (ElementNotInteractableException, ElementClickInterceptedException, TimeoutException):
                logging.warning(f"[DISMISS] Can't dismiss an element by clicking on {dismissButton.get_attribute('outerHTML')}")

    def switchToNewTab(self, timeToWait: float = 10, closeTab: bool = False) -> None:
        time.sleep(timeToWait)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[1])
        if closeTab:
            self.closeCurrentTab()

    def closeCurrentTab(self) -> None:
        self.webdriver.close()
        time.sleep(0.5)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[0])
        time.sleep(0.5)

    def click(self, element: WebElement) -> None:
        try:
            WebDriverWait(self.webdriver, 10).until(
                expected_conditions.element_to_be_clickable(element)
            ).click()
        except (
            TimeoutException,
            ElementClickInterceptedException,
            ElementNotInteractableException,
        ):
            self.tryDismissAllMessages()
            with contextlib.suppress(TimeoutException):
                WebDriverWait(self.webdriver, 10).until(
                    expected_conditions.element_to_be_clickable(element)
                )
            try:
                element.click()
            except ElementClickInterceptedException:
                logging.debug("[CLICK] Element intercepted, using JavaScript click")
                self.webdriver.execute_script("arguments[0].click();", element)


def argumentParser() -> Namespace:
    parser = ArgumentParser(
        description="A simple bot that uses Selenium to farm M$ Rewards in Python",
        epilog="At least one account should be specified,"
        " either using command line arguments or a configuration file."
        "\nAll specified arguments will override the configuration file values.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="Specify the configuration file path",
    )
    parser.add_argument(
        "-C",
        "--create-config",
        action="store_true",
        help="Create a fillable configuration file with basic settings"
        " and given ones if none exists",
    )
    parser.add_argument(
        "-v",
        "--visible",
        action="store_true",
        help="Visible browser (Disable headless mode)",
    )
    parser.add_argument(
        "-l",
        "--lang",
        type=str,
        default=None,
        help="Language (ex: en)"
        "\nsee https://serpapi.com/google-languages for options",
    )
    parser.add_argument(
        "-g",
        "--geo",
        type=str,
        default=None,
        help="Searching geolocation (ex: US)"
        "\nsee https://serpapi.com/google-trends-locations for options (should be uppercase)",
    )
    parser.add_argument(
        "-em",
        "--email",
        type=str,
        default=None,
        help="Email address of the account to run. Only used if a password is given.",
    )
    parser.add_argument(
        "-pw",
        "--password",
        type=str,
        default=None,
        help="Password of the account to run. Only used if an email is given.",
    )
    parser.add_argument(
        "-totp",
        "--totp",
        type=str,
        default=None,
        help="TOTP secret for 2FA. Only used if email and password are given.",
    )
    parser.add_argument(
        "-p",
        "--proxy",
        type=str,
        default=None,
        help="Global Proxy, supports http/https/socks4/socks5"
        " (overrides config per-account proxies)"
        "\n`(ex: http://user:pass@host:port)`",
    )
    parser.add_argument(
        "--desktop-channel",
        action=BooleanOptionalAction,
        default=None,
        help="Enable or disable the desktop channel",
    )
    parser.add_argument(
        "--mobile-channel",
        action=BooleanOptionalAction,
        default=None,
        help="Enable or disable the mobile Read-to-Earn channel",
    )
    parser.add_argument(
        "-da",
        "--disable-apprise",
        action="store_true",
        help="Disable Apprise notifications, useful when developing",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Set the logging level to DEBUG",
    )
    parser.add_argument(
        "-r",
        "--reset",
        action="store_true",
        help="Delete the session folder and temporary files and kill"
        " all chrome processes. Can help resolve issues.",
    )
    return parser.parse_args()


def getProjectRoot() -> Path:
    return Path(__file__).parent.parent


def commandLineArgumentsAsConfig(args: Namespace) -> Config:
    config = Config()
    if args.visible:
        config.browser = Config()
        config.browser.visible = True
    if args.lang:
        if "browser" not in config:
            config.browser = Config()
        config.browser.language = args.lang
    if args.geo:
        if "browser" not in config:
            config.browser = Config()
        config.browser.geolocation = args.geo
    if args.proxy:
        if "browser" not in config:
            config.browser = Config()
        config.browser.proxy = args.proxy
    if args.disable_apprise:
        config.apprise = Config()
        config.apprise.enabled = False
    if args.debug:
        config.logging = Config()
        config.logging.level = "DEBUG"
    if args.desktop_channel is not None:
        config.channel = Config()
        config.channel.desktop = Config(enabled=args.desktop_channel)
    if args.mobile_channel is not None:
        if "channel" not in config:
            config.channel = Config()
        config.channel.mobile = Config(enabled=args.mobile_channel)
    if args.email and args.password:
        account = Config(
            email=args.email,
            password=args.password,
        )
        if args.totp:
            account.totp = args.totp
        config.accounts = [account]

    return config


def setupAccounts(config: Config) -> Config:
    def validEmail(email: str) -> bool:
        """Validate Email."""
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email))

    loadedAccounts = []
    for account in config.accounts:
        if (
            "email" not in account
            or not isinstance(account.email, str)
            or not validEmail(account.email)
        ):
            logging.warning(
                f"[CREDENTIALS] Invalid email '{account.get('email', 'No email provided')}',"
                f" skipping this account"
            )
            continue
        if "password" not in account or not isinstance(account["password"], str):
            logging.warning("[CREDENTIALS] Invalid password, skipping this account")
            continue
        logging.info(f"[CREDENTIALS] Account loaded {account.email}")
        loadedAccounts.append(account)

    if not loadedAccounts:
        noAccountsNotice = """
        [ACCOUNT] No valid account provided.
        [ACCOUNT] Please provide a valid account, either using command line arguments or a configuration file.
        [ACCOUNT] For command line, please use the following arguments (change the email and password):
        [ACCOUNT]   `--email youremail@domain.com --password yourpassword` 
        [ACCOUNT] For configuration file, please generate a configuration file using the `-C` argument,
        [ACCOUNT]   then edit the generated file by replacing the email and password using yours. 
        """
        logging.error(noAccountsNotice)
        sys.exit(1)

    random.shuffle(loadedAccounts)
    config.accounts = loadedAccounts
    return config


def createEmptyConfig(configPath: Path, config: Config) -> None:
    if configPath.is_file():
        logging.error(f"[CONFIG] A file already exists at '{configPath}'")
        sys.exit(1)

    emptyConfig = Config(
        {
            "accounts": [
                {
                    "email": "Your Email 1",
                    "password": "Your Password 1",
                    "totp": "0123 4567 89ab cdef",
                    "proxy": "http://user:pass@host1:port",
                },
                {
                    "email": "Your Email 2",
                    "password": "Your Password 2",
                    "totp": "0123 4567 89ab cdef",
                    "proxy": "http://user:pass@host2:port",
                },
            ],
            "cooldown": {
                "min": 5,
                "max": 30,
            },
            "browser": {
                "language": "en-US",
                "geolocation": "US",
            },
            "retries": {
                "backoff-factor": 20,
                "max": 4,
                "strategy": "CONSTANT",
            },
        }
    )
    with open(configPath, "w", encoding="utf-8") as configFile:
        yaml.dump((emptyConfig | config).toDict(), configFile)
    print(f"A configuration file was created at '{configPath}'")
    sys.exit()


def resetBot():
    """
    Delete the session folder and temporary files and kill all chrome processes.
    """

    sessionPath = getProjectRoot() / "sessions"
    if sessionPath.exists():
        print(f"Deleting sessions folder '{sessionPath}'")
        shutil.rmtree(sessionPath)

    filesToDeletePaths = (
        getProjectRoot() / "google_trends.bak",
        getProjectRoot() / "google_trends.dat",
        getProjectRoot() / "google_trends.dir",
        getProjectRoot() / "logs" / "previous_points_data.json",
    )
    for path in filesToDeletePaths:
        print(f"Deleting file '{path}'")
        path.unlink(missing_ok=True)

    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] == "chrome.exe":
            proc.kill()

    print("All chrome processes killed")
    sys.exit()


def loadConfig(configFilename="config.yaml") -> Config:
    args = argumentParser()
    if args.config:
        configFile = Path(args.config)
    else:
        configFile = getProjectRoot() / configFilename

    args_config = commandLineArgumentsAsConfig(args)

    if args.create_config:
        createEmptyConfig(configFile, args_config)

    if args.reset:
        resetBot()

    config = DEFAULT_CONFIG | Config.fromYaml(configFile) | args_config

    return config


def initApprise() -> Apprise:
    apprise = Apprise()

    urls = []
    if CONFIG.apprise.enabled:
        urls: list[str] = CONFIG.apprise.urls
        if not urls:
            logging.info("No apprise urls found, not sending notification")

    apprise.add(urls)
    return apprise


def formatNumber(number, num_decimals=0) -> str:
    return pylocale.format_string(f"%10.{num_decimals}f", number, grouping=True).strip()


def getBrowserConfig(sessionPath: Path) -> dict | None:
    configFile = sessionPath / "config.json"
    if not configFile.exists():
        return None
    with open(configFile, encoding="utf-8") as f:
        return json.load(f)


def saveBrowserConfig(sessionPath: Path, config: dict) -> None:
    configFile = sessionPath / "config.json"
    with open(configFile, "w", encoding="utf-8") as f:
        json.dump(config, f)


from typing import TypeVar

T = TypeVar("T", bound=Session)


def makeRequestsSession(session: T = requests.session()) -> T:
    retry = Retry(
        total=CONFIG.retries.max,
        backoff_factor=CONFIG.get("retries.backoff-factor"),
        status_forcelist=[
            500,
            502,
            503,
            504,
        ],
    )
    session.mount(
        "https://", HTTPAdapter(max_retries=retry)
    )  # See https://stackoverflow.com/a/35504626/4164390 to finetune
    session.mount(
        "http://", HTTPAdapter(max_retries=retry)
    )  # See https://stackoverflow.com/a/35504626/4164390 to finetune
    return session


def cooldown() -> None:
    if sys.gettrace():
        logging.info("[DEBUGGER] Debugger is attached, skipping cooldown.")
        return

    cooldownTime = random.randint(CONFIG.cooldown.min, CONFIG.cooldown.max)
    logging.info(f"[COOLDOWN] Waiting for {cooldownTime} seconds")
    time.sleep(cooldownTime)


def isValidCountryCode(countryCode: str) -> bool:
    """
    Verifies if the given country code is a valid alpha-2 code with or without a region.

    Args:
        countryCode (str): The country code to verify.

    Returns:
        bool: True if the country code is valid, False otherwise.
    """
    if "-" in countryCode:
        country, region = countryCode.split("-")
    else:
        country = countryCode
        region = None

    # Check if the country part is a valid alpha-2 code
    if not pycountry.countries.get(alpha_2=country):
        return False

    # If region is provided, check if it is a valid region code
    if region and not pycountry.subdivisions.get(code=f"{country}-{region}"):
        return False

    return True


def isValidLanguageCode(languageCode: str) -> bool:
    """
    Verifies if the given language code is a valid ISO 639-1 or ISO 639-3 code,
    and optionally checks the region if provided.

    Args:
        languageCode (str): The language code to verify.

    Returns:
        bool: True if the language code is valid, False otherwise.
    """
    if "-" in languageCode:
        language, region = languageCode.split("-")
    else:
        language = languageCode
        region = None

    # Check if the language part is a valid ISO 639-1 or ISO 639-3 code
    if not (
        pycountry.languages.get(alpha_2=language)
        or pycountry.languages.get(alpha_3=language)
    ):
        return False

    # If region is provided, check if it is a valid country code
    if region and not pycountry.countries.get(alpha_2=region):
        return False

    return True


def getLanguageCountry() -> tuple[str, str]:
    country = CONFIG.browser.geolocation
    language = CONFIG.browser.language

    if country and not isValidCountryCode(country):
        logging.warning(
            f"Invalid country code {country}, attempting to determine country code from IP"
        )

    ipapiLocation = None
    if not country or not isValidCountryCode(country):
        try:
            ipapiLocation = ipapi.location()
            country = ipapiLocation["country"]
            regionCode = ipapiLocation["region_code"]
            if regionCode:
                country = country + "-" + regionCode
            assert isValidCountryCode(country)
        except RateLimited:
            logging.warning("Rate limited by ipapi")

    if language and not isValidLanguageCode(language):
        logging.warning(
            f"Invalid language code {language}, attempting to determine language code from IP"
        )

    if not language or not isValidLanguageCode(language):
        try:
            if ipapiLocation is None:
                ipapiLocation = ipapi.location()
            language = ipapiLocation["languages"].split(",")[0]
            assert isValidLanguageCode(language)
        except RateLimited:
            logging.warning("Rate limited by ipapi")

    if not language:
        language = "en-US"
        logging.warning(f"Not able to figure language returning default: {language}")

    if not country:
        country = "US"
        logging.warning(f"Not able to figure country returning default: {country}")

    return language, country


# todo Could remove this functionality in favor of https://pypi.org/project/translate/
# That's assuming all activity titles are in English
def load_localized_activities(language: str) -> ModuleType:
    try:
        search_module = importlib.import_module(f"localized_activities.{language}")
        return search_module
    except ModuleNotFoundError:
        logging.warning(f"No search queries found for language: {language}, defaulting to English (en)")
        return importlib.import_module("localized_activities.en")

CONFIG = loadConfig()
APPRISE = initApprise()
LANGUAGE, COUNTRY = getLanguageCountry()
localized_activities = load_localized_activities(
    LANGUAGE.split("-")[0] if "-" in LANGUAGE else LANGUAGE
)
ACTIVITY_TITLES_TO_QUERIES = localized_activities.title_to_query
IGNORED_ACTIVITIES = localized_activities.ignore
