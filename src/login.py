import argparse
import contextlib
import logging
import time
from argparse import Namespace

from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome

from src.browser import Browser


class Login:
    browser: Browser
    args: Namespace
    webdriver: Chrome

    def __init__(self, browser: Browser, args: argparse.Namespace):
        self.browser = browser
        self.webdriver = browser.webdriver
        self.utils = browser.utils
        self.args = args

    def login(self) -> int:
        if self.utils.isLoggedIn():
            logging.info("[LOGIN] Already logged-in")
        else:
            logging.info("[LOGIN] Logging-in...")
            self.executeLogin()
            logging.info("[LOGIN] Logged-in successfully !")

        assert self.utils.isLoggedIn()

        return self.utils.getAccountPoints()

    def executeLogin(self) -> None:
        self.utils.waitUntilVisible(By.ID, "i0116", 10)

        emailField = self.utils.waitUntilClickable(By.NAME, "loginfmt", 10)
        logging.info("[LOGIN] Entering email...")
        emailField.send_keys(self.browser.username)
        time.sleep(3)
        assert emailField.get_attribute("value") == self.browser.username
        self.webdriver.find_element(By.ID, "idSIButton9").click()

        isTwoFactorEnabled = False
        try:
            self.utils.waitUntilVisible(By.ID, "pushNotificationsTitle", 10)
            isTwoFactorEnabled = True
        except NoSuchElementException:
            logging.info("2FA not enabled")

        if isTwoFactorEnabled:
            # todo - Handle 2FA when running headless
            assert (
                self.args.visible
            ), "2FA detected, run in visible mode to handle login"
            while True:
                print(
                    "2FA detected, handle prompts and press enter when on rewards portal to continue"
                )
                input()
                with contextlib.suppress(TimeoutException):
                    self.utils.waitUntilVisible(
                        By.CSS_SELECTOR, 'html[data-role-name="RewardsPortal"]', 10
                    )
                    break
                print("Rewards portal not accessible, waiting until next attempt")
        else:
            passwordField = self.utils.waitUntilClickable(By.NAME, "passwd", 10)
            enterPasswordButton = self.utils.waitUntilClickable(
                By.ID, "idSIButton9", 10
            )
            logging.info("[LOGIN] Entering password...")
            passwordField.send_keys(self.browser.password)
            time.sleep(3)
            assert passwordField.get_attribute("value") == self.browser.password
            enterPasswordButton.click()

        self.utils.waitUntilVisible(
            By.CSS_SELECTOR, 'html[data-role-name="RewardsPortal"]', 10
        )
