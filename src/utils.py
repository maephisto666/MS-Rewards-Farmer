import contextlib
import json
import locale as pylocale
import random
import time
import urllib.parse
from pathlib import Path

import requests
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from .constants import BASE_URL


class Utils:
    def __init__(self, webdriver: WebDriver):
        self.webdriver = webdriver
        with contextlib.suppress(Exception):
            locale = pylocale.getdefaultlocale()[0]
            pylocale.setlocale(pylocale.LC_NUMERIC, locale)

    def waitUntilVisible(self, by: str, selector: str, timeToWait: float = 10):
        # Wait until the element is visible on the page
        WebDriverWait(self.webdriver, timeToWait).until(
            ec.visibility_of_element_located((by, selector))
        )

    def waitUntilClickable(self, by: str, selector: str, timeToWait: float = 10):
        # Wait until the element is clickable
        WebDriverWait(self.webdriver, timeToWait).until(
            ec.element_to_be_clickable((by, selector))
        )

    def waitForMSRewardElement(self, by: str, selector: str):
        # Wait for an element related to MS Rewards
        loadingTimeAllowed = 5
        refreshsAllowed = 5

        checkingInterval = 0.5
        checks = loadingTimeAllowed / checkingInterval

        tries = 0
        refreshCount = 0
        while True:
            try:
                self.webdriver.find_element(by, selector)
                return True
            except Exception:
                if tries < checks:
                    tries += 1
                    time.sleep(checkingInterval)
                elif refreshCount < refreshsAllowed:
                    self.webdriver.refresh()
                    refreshCount += 1
                    tries = 0
                    time.sleep(5)
                else:
                    return False

    def waitUntilQuestionRefresh(self):
        # Wait until the question in the quiz is refreshed
        return self.waitForMSRewardElement(By.CLASS_NAME, "rqECredits")

    def waitUntilQuizLoads(self):
        # Wait until the quiz is loaded
        return self.waitForMSRewardElement(By.XPATH, '//*[@id="rqStartQuiz"]')

    def waitUntilJS(self, jsSrc: str):
        # Wait until a JavaScript condition is met
        loadingTimeAllowed = 5
        refreshsAllowed = 5

        checkingInterval = 0.5
        checks = loadingTimeAllowed / checkingInterval

        tries = 0
        refreshCount = 0
        while True:
            elem = self.webdriver.execute_script(jsSrc)
            if elem:
                return elem

            if tries < checks:
                tries += 1
                time.sleep(checkingInterval)
            elif refreshCount < refreshsAllowed:
                self.webdriver.refresh()
                refreshCount += 1
                tries = 0
                time.sleep(5)
            else:
                return elem

    def resetTabs(self):
        # Reset browser tabs by closing extra tabs and navigating to the home page
        try:
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
        except Exception:
            self.goHome()

    def goHome(self):
        # Navigate to the home page
        reloadThreshold = 5
        reloadInterval = 10
        targetUrl = urllib.parse.urlparse(BASE_URL)
        self.webdriver.get(BASE_URL)
        reloads = 0
        interval = 1
        intervalCount = 0
        while True:
            self.tryDismissCookieBanner()
            with contextlib.suppress(Exception):
                self.webdriver.find_element(By.ID, "more-activities")
                break
            currentUrl = urllib.parse.urlparse(self.webdriver.current_url)
            if (
                currentUrl.hostname != targetUrl.hostname
            ) and self.tryDismissAllMessages():
                time.sleep(1)
                self.webdriver.get(BASE_URL)
            time.sleep(interval)
            if "proofs" in str(self.webdriver.current_url):
                return "Verify"
            intervalCount += 1
            if intervalCount >= reloadInterval:
                intervalCount = 0
                reloads += 1
                self.webdriver.refresh()
                if reloads >= reloadThreshold:
                    break

    def getAnswerCode(self, key: str, string: str) -> str:
        # Generate an answer code based on a key and a string
        t = sum(ord(string[i]) for i in range(len(string)))
        t += int(key[-2:], 16)
        return str(t)

    def getDashboardData(self) -> dict:
        # Get the dashboard data using JavaScript execution
        return self.webdriver.execute_script("return dashboard")

    def getBingInfo(self):
        # Get Bing information using cookies
        cookieJar = self.webdriver.get_cookies()
        cookies = {cookie["name"]: cookie["value"] for cookie in cookieJar}
        maxTries = 5
        for _ in range(maxTries):
            with contextlib.suppress(Exception):
                response = requests.get(
                    "https://www.bing.com/rewards/panelflyout/getuserinfo",
                    cookies=cookies,
                )
                if response.status_code == requests.codes.ok:
                    return response.json()
            time.sleep(1)
        return None

    def checkBingLogin(self):
        # Check if the user is logged in to Bing
        if data := self.getBingInfo():
            return data["userInfo"]["isRewardsUser"]
        else:
            return False

    def getAccountPoints(self) -> int:
        # Get the available points from the dashboard data
        return self.getDashboardData()["userStatus"]["availablePoints"]

    def getBingAccountPoints(self) -> int:
        # Get the Bing account points from the Bing info
        return data["userInfo"]["balance"] if (data := self.getBingInfo()) else 0

    def getGoalPoints(self) -> int:
        # Get the redemption goal points from the dashboard data
        return self.getDashboardData()["userStatus"]["redeemGoal"]["price"]

    def getGoalTitle(self) -> str:
        # Get the redemption goal title from the dashboard data
        return self.getDashboardData()["userStatus"]["redeemGoal"]["title"]

    def tryDismissAllMessages(self):
        # Try to dismiss various messages using different buttons
        buttons = [
            (By.ID, "iLandingViewAction"),
            (By.ID, "iShowSkip"),
            (By.ID, "iNext"),
            (By.ID, "iLooksGood"),
            (By.ID, "idSIButton9"),
            (By.CSS_SELECTOR, ".ms-Button.ms-Button--primary"),
            (By.ID, "bnp_btn_accept"),
            (By.ID, "acceptButton")
        ]
        result = False
        for button in buttons:
            try:
                elements = self.webdriver.find_elements(button[0], button[1])
                try:
                    for element in elements:
                        element.click()
                except Exception:
                    continue
                result = True
            except Exception:
                continue
        return result

    def tryDismissCookieBanner(self):
        # Try to dismiss the cookie banner
        with contextlib.suppress(Exception):
            self.webdriver.find_element(By.ID, "cookie-banner").find_element(
                By.TAG_NAME, "button"
            ).click()
            time.sleep(2)

    def tryDismissBingCookieBanner(self):
        # Try to dismiss the Bing cookie banner
        with contextlib.suppress(Exception):
            self.webdriver.find_element(By.ID, "bnp_btn_accept").click()
            time.sleep(2)

    def switchToNewTab(self, timeToWait: int = 0):
        # Switch to a new tab and optionally wait for a specified time
        time.sleep(0.5)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[1])
        if timeToWait > 0:
            time.sleep(timeToWait)

    def closeCurrentTab(self):
        # Close the current tab
        self.webdriver.close()
        time.sleep(0.5)
        self.webdriver.switch_to.window(window_name=self.webdriver.window_handles[0])
        time.sleep(0.5)

    def visitNewTab(self, timeToWait: int = 0):
        # Visit a new tab and close the current tab
        self.switchToNewTab(timeToWait)
        self.closeCurrentTab()

    def getRemainingSearches(self):
        # Get the remaining searches from the dashboard data
        dashboard = self.getDashboardData()
        searchPoints = 1
        counters = dashboard["userStatus"]["counters"]

        if "pcSearch" not in counters:
            return 0, 0

        progressDesktop = counters["pcSearch"][0]["pointProgress"]
        targetDesktop = counters["pcSearch"][0]["pointProgressMax"]
        if len(counters["pcSearch"]) >= 2:
            progressDesktop = progressDesktop + counters["pcSearch"][1]["pointProgress"]
            targetDesktop = targetDesktop + counters["pcSearch"][1]["pointProgressMax"]
        if targetDesktop in [30, 90, 102]:
            # Level 1 or 2 EU/South America
            searchPoints = 3
        elif targetDesktop == 50 or targetDesktop >= 170 or targetDesktop == 150:
            # Level 1 or 2 US
            searchPoints = 5
        remainingDesktop = int((targetDesktop - progressDesktop) / searchPoints)
        remainingMobile = 0
        if dashboard["userStatus"]["levelInfo"]["activeLevel"] != "Level1":
            progressMobile = counters["mobileSearch"][0]["pointProgress"]
            targetMobile = counters["mobileSearch"][0]["pointProgressMax"]
            remainingMobile = int((targetMobile - progressMobile) / searchPoints)
        return remainingDesktop, remainingMobile

    def formatNumber(self, number, num_decimals=2):
        # Format a number with the specified number of decimals
        return pylocale.format_string(
            f"%10.{num_decimals}f", number, grouping=True
        ).strip()

    def randomSeconds(self, max_value):
        # Generate a random time interval in seconds
        random_number = random.uniform(self, max_value)
        return round(random_number, 3)

    @staticmethod
    def getBrowserConfig(sessionPath: Path) -> dict:
        # Get the browser configuration from a JSON file
        configFile = sessionPath.joinpath("config.json")
        if configFile.exists():
            with open(configFile, "r") as f:
                return json.load(f)
        else:
            return {}

    @staticmethod
    def saveBrowserConfig(sessionPath: Path, config: dict):
        # Save the browser configuration to a JSON file
        configFile = sessionPath.joinpath("config.json")
        with open(configFile, "w") as f:
            json.dump(config, f)
