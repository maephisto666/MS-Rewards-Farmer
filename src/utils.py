import contextlib
import json
import locale as pylocale
import logging
import time
from argparse import Namespace
from pathlib import Path
from typing import NamedTuple, Any

import requests
import yaml
from apprise import Apprise
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from .constants import REWARDS_URL
from .constants import SEARCH_URL


class RemainingSearches(NamedTuple):
    desktop: int
    mobile: int

    def getTotal(self) -> int:
        return self.desktop + self.mobile


class Utils:
    args: Namespace

    def __init__(self, webdriver: WebDriver):
        self.webdriver = webdriver
        with contextlib.suppress(Exception):
            locale = pylocale.getdefaultlocale()[0]
            pylocale.setlocale(pylocale.LC_NUMERIC, locale)

        self.config = self.loadConfig()

    @staticmethod
    def getProjectRoot() -> Path:
        return Path(__file__).parent.parent

    @staticmethod
    def loadConfig(config_file=getProjectRoot() / "config.yaml") -> dict:
        with open(config_file, "r") as file:
            return yaml.safe_load(file)

    @staticmethod
    def sendNotification(title, body) -> None:
        if Utils.args.disable_apprise:
            return
        apprise = Apprise()
        urls: list[str] = Utils.loadConfig().get("apprise", {}).get("urls", [])
        for url in urls:
            apprise.add(url)
        apprise.notify(body=body, title=title)

    def waitUntilVisible(
        self, by: str, selector: str, timeToWait: float = 10
    ) -> WebElement:
        return WebDriverWait(self.webdriver, timeToWait).until(
            ec.visibility_of_element_located((by, selector))
        )

    def waitUntilClickable(
        self, by: str, selector: str, timeToWait: float = 10
    ) -> WebElement:
        return WebDriverWait(self.webdriver, timeToWait).until(
            ec.element_to_be_clickable((by, selector))
        )

    def waitUntilQuestionRefresh(self) -> WebElement:
        return self.waitUntilVisible(By.CLASS_NAME, "rqECredits", timeToWait=20)

    def waitUntilQuizLoads(self) -> WebElement:
        return self.waitUntilVisible(By.XPATH, '//*[@id="rqStartQuiz"]')

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
        self.webdriver.get(REWARDS_URL)
        assert self.webdriver.current_url == REWARDS_URL

    def goToSearch(self) -> None:
        self.webdriver.get(SEARCH_URL)
        # assert self.webdriver.current_url == SEARCH_URL, f"{self.webdriver.current_url} {SEARCH_URL}"

    @staticmethod
    def getAnswerCode(key: str, string: str) -> str:
        t = sum(ord(string[i]) for i in range(len(string)))
        t += int(key[-2:], 16)
        return str(t)

    def getDashboardData(self) -> dict:
        self.goToRewards()
        return self.webdriver.execute_script("return dashboard")

    def getBingInfo(self) -> Any:
        cookieJar = WebDriverWait(self.webdriver, timeout=20).until(lambda d: d.get_cookies())
        cookies = {cookie["name"]: cookie["value"] for cookie in cookieJar}
        response = requests.get(
            "https://www.bing.com/rewards/panelflyout/getuserinfo",
            cookies=cookies,
        )
        assert response.status_code == requests.codes.ok
        return response.json()

    def isLoggedIn(self) -> bool:
        self.webdriver.get(
            "https://rewards.bing.com/Signin/"
        )  # changed site to allow bypassing when M$ blocks access to login.live.com randomly
        with contextlib.suppress(TimeoutException):
            self.waitUntilVisible(
                By.CSS_SELECTOR, 'html[data-role-name="RewardsPortal"]', 10
            )
            return True
        return False

    # todo - See if faster, but reliable, way to get this information that doesn't change page
    def getAccountPoints(self) -> int:
        return self.getDashboardData()["userStatus"]["availablePoints"]

    def getGoalPoints(self) -> int:
        return self.getDashboardData()["userStatus"]["redeemGoal"]["price"]

    def getGoalTitle(self) -> str:
        return self.getDashboardData()["userStatus"]["redeemGoal"]["title"]

    def tryDismissAllMessages(self) -> None:
        buttons = [
            (By.ID, "iLandingViewAction"),
            (By.ID, "iShowSkip"),
            (By.ID, "iNext"),
            (By.ID, "iLooksGood"),
            (By.ID, "idSIButton9"),
            (By.CSS_SELECTOR, ".ms-Button.ms-Button--primary"),
            (By.ID, "bnp_btn_accept"),
            (By.ID, "acceptButton"),
        ]
        for button in buttons:
            try:
                elements = self.webdriver.find_elements(by=button[0], value=button[1])
            except NoSuchElementException:  # Expected?
                logging.debug("", exc_info=True)
                continue
            for element in elements:
                element.click()

    def tryDismissCookieBanner(self) -> None:
        with contextlib.suppress(NoSuchElementException):  # Expected
            self.webdriver.find_element(By.ID, "cookie-banner").find_element(
                By.TAG_NAME, "button"
            ).click()
            time.sleep(2)

    def tryDismissBingCookieBanner(self) -> None:
        with contextlib.suppress(NoSuchElementException):  # Expected
            self.webdriver.find_element(By.ID, "bnp_btn_accept").click()
            time.sleep(2)

    def switchToNewTab(self, timeToWait: float = 0) -> None:
        time.sleep(0.5)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[1])
        if timeToWait > 0:
            time.sleep(timeToWait)

    def closeCurrentTab(self) -> None:
        self.webdriver.close()
        time.sleep(0.5)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[0])
        time.sleep(0.5)

    def visitNewTab(self, timeToWait: float = 0) -> None:
        self.switchToNewTab(timeToWait)
        self.closeCurrentTab()

    def getRemainingSearches(self) -> RemainingSearches:
        dashboard = self.getDashboardData()
        searchPoints = 1
        counters = dashboard["userStatus"]["counters"]

        progressDesktop = counters["pcSearch"][0]["pointProgress"]
        targetDesktop = counters["pcSearch"][0]["pointProgressMax"]
        if len(counters["pcSearch"]) >= 2:
            progressDesktop = progressDesktop + counters["pcSearch"][1]["pointProgress"]
            targetDesktop = targetDesktop + counters["pcSearch"][1]["pointProgressMax"]
        if targetDesktop in [30, 90, 102]:
            searchPoints = 3
        elif targetDesktop == 50 or targetDesktop >= 170 or targetDesktop == 150:
            searchPoints = 5
        remainingDesktop = int((targetDesktop - progressDesktop) / searchPoints)
        remainingMobile = 0
        if dashboard["userStatus"]["levelInfo"]["activeLevel"] != "Level1":
            progressMobile = counters["mobileSearch"][0]["pointProgress"]
            targetMobile = counters["mobileSearch"][0]["pointProgressMax"]
            remainingMobile = int((targetMobile - progressMobile) / searchPoints)
        return RemainingSearches(desktop=remainingDesktop, mobile=remainingMobile)

    @staticmethod
    def formatNumber(number, num_decimals=2) -> str:
        return pylocale.format_string(
            f"%10.{num_decimals}f", number, grouping=True
        ).strip()

    @staticmethod
    def getBrowserConfig(sessionPath: Path) -> dict | None:
        configFile = sessionPath / "config.json"
        if not configFile.exists():
            return
        with open(configFile, "r") as f:
            return json.load(f)

    @staticmethod
    def saveBrowserConfig(sessionPath: Path, config: dict) -> None:
        configFile = sessionPath / "config.json"
        with open(configFile, "w") as f:
            json.dump(config, f)
