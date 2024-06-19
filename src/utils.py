import contextlib
import json
import locale as pylocale
import logging
import time
import urllib.parse
from pathlib import Path
from typing import NamedTuple, Any

import requests
import yaml
from apprise import Apprise
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from .constants import BASE_URL


class VerifyAccountException(Exception):
    pass


class RemainingSearches(NamedTuple):
    desktop: int
    mobile: int

    def getTotal(self) -> int:
        return self.desktop + self.mobile


class Utils:
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
        apprise = Apprise()
        urls: list[str] = Utils.loadConfig().get("apprise", {}).get("urls", [])
        for url in urls:
            apprise.add(url)
        apprise.notify(body=body, title=title)

    def waitUntilVisible(self, by: str, selector: str, timeToWait: float = 10) -> None:
        WebDriverWait(self.webdriver, timeToWait).until(
            ec.visibility_of_element_located((by, selector))
        )

    def waitUntilClickable(
        self, by: str, selector: str, timeToWait: float = 10
    ) -> None:
        WebDriverWait(self.webdriver, timeToWait).until(
            ec.element_to_be_clickable((by, selector))
        )

    def waitForMSRewardElement(self, by: str, selector: str) -> None:
        loadingTimeAllowed = 5
        refreshesAllowed = 5

        checkingInterval = 0.5
        checks = loadingTimeAllowed / checkingInterval

        tries = 0
        refreshCount = 0
        while True:
            try:
                self.webdriver.find_element(by, selector)
                return
            except NoSuchElementException:
                logging.warning("", exc_info=True)
                if tries < checks:
                    tries += 1
                    time.sleep(checkingInterval)
                elif refreshCount < refreshesAllowed:
                    self.webdriver.refresh()
                    refreshCount += 1
                    tries = 0
                    time.sleep(5)
                else:
                    raise NoSuchElementException

    def waitUntilQuestionRefresh(self) -> None:
        return self.waitForMSRewardElement(By.CLASS_NAME, "rqECredits")

    def waitUntilQuizLoads(self) -> None:
        return self.waitForMSRewardElement(By.XPATH, '//*[@id="rqStartQuiz"]')

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
        self.goHome()

    def goHome(self) -> None:
        reloadThreshold = 5
        reloadInterval = 10
        targetUrl = urllib.parse.urlparse(BASE_URL)
        self.webdriver.get(BASE_URL)
        reloads = 0
        interval = 1
        intervalCount = 0
        while True:
            self.tryDismissCookieBanner()
            self.webdriver.find_element(By.ID, "more-activities")
            currentUrl = urllib.parse.urlparse(self.webdriver.current_url)
            if (
                currentUrl.hostname != targetUrl.hostname
            ) and self.tryDismissAllMessages():
                time.sleep(1)
                self.webdriver.get(BASE_URL)
            time.sleep(interval)
            if "proofs" in str(self.webdriver.current_url):
                raise VerifyAccountException
            intervalCount += 1
            if intervalCount >= reloadInterval:
                intervalCount = 0
                reloads += 1
                self.webdriver.refresh()
                if reloads >= reloadThreshold:
                    break

    @staticmethod
    def getAnswerCode(key: str, string: str) -> str:
        t = sum(ord(string[i]) for i in range(len(string)))
        t += int(key[-2:], 16)
        return str(t)

    def getDashboardData(self) -> dict:
        self.goHome()
        return self.webdriver.execute_script("return dashboard")

    def getBingInfo(self) -> Any:
        cookieJar = self.webdriver.get_cookies()
        cookies = {cookie["name"]: cookie["value"] for cookie in cookieJar}
        maxTries = 5
        for _ in range(maxTries):
            response = requests.get(
                "https://www.bing.com/rewards/panelflyout/getuserinfo",
                cookies=cookies,
            )
            if response.status_code == requests.codes.ok:
                return response.json()
            time.sleep(1)
        raise Exception

    def checkBingLogin(self) -> bool:
        return self.getBingInfo()["userInfo"]["isRewardsUser"]

    def getAccountPoints(self) -> int:
        return self.getDashboardData()["userStatus"]["availablePoints"]

    def getBingAccountPoints(self) -> int:
        return self.getBingInfo()["userInfo"]["balance"]

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

    def switchToNewTab(self, timeToWait: int = 0) -> None:
        time.sleep(0.5)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[1])
        if timeToWait > 0:
            time.sleep(timeToWait)

    def closeCurrentTab(self) -> None:
        self.webdriver.close()
        time.sleep(0.5)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[0])
        time.sleep(0.5)

    def visitNewTab(self, timeToWait: int = 0) -> None:
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
