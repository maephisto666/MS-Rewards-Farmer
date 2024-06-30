import argparse
import contextlib
import logging
from argparse import Namespace

from selenium.common import TimeoutException
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

    def login(self) -> None:
        if self.utils.isLoggedIn():
            logging.info("[LOGIN] Already logged-in")
        else:
            logging.info("[LOGIN] Logging-in...")
            self.executeLogin()
            logging.info("[LOGIN] Logged-in successfully !")

        assert self.utils.isLoggedIn()

    def executeLogin(self) -> None:
        self.utils.waitUntilVisible(By.ID, "i0116")

        emailField = self.utils.waitUntilClickable(By.NAME, "loginfmt")
        logging.info("[LOGIN] Entering email...")
        emailField.send_keys(self.browser.username)
        assert emailField.get_attribute("value") == self.browser.username
        self.utils.waitUntilClickable(By.ID, "idSIButton9").click()

        # noinspection PyUnusedLocal
        isTwoFactorEnabled: bool = False
        with contextlib.suppress(TimeoutException):
            self.utils.waitUntilVisible(By.ID, "pushNotificationsTitle")
            isTwoFactorEnabled = True
        logging.debug(f"isTwoFactorEnabled = {isTwoFactorEnabled}")

        if isTwoFactorEnabled:
            # todo - Handle 2FA when running headless
            assert (
                self.args.visible
            ), "2FA detected, run in visible mode to handle login"
            print(
                "2FA detected, handle prompts and press enter when on keep me signed in page"
            )
            input()

            with contextlib.suppress(TimeoutException):  # In case user clicked stay signed in
                self.utils.waitUntilVisible(
                    By.NAME, "kmsiForm"
                )  # kmsi = keep me signed form
                self.utils.waitUntilClickable(By.ID, "acceptButton").click()
        else:
            passwordField = self.utils.waitUntilClickable(By.NAME, "passwd")
            logging.info("[LOGIN] Entering password...")
            passwordField.send_keys(self.browser.password)
            assert passwordField.get_attribute("value") == self.browser.password
            self.utils.waitUntilClickable(By.ID, "idSIButton9").click()

            self.utils.waitUntilVisible(
                By.NAME, "kmsiForm"
            )  # kmsi = keep me signed form
            self.utils.waitUntilClickable(By.ID, "acceptButton").click()

        isAskingToProtect = self.utils.checkIfTextPresentAfterDelay('protect your account')
        logging.debug(f"isAskingToProtect = {isAskingToProtect}")

        if isAskingToProtect:
            assert (
                self.args.visible
            ), "Account protection detected, run in visible mode to handle login"
            print(
                "Account protection detected, handle prompts and press enter when on rewards page"
            )
            input()

        self.utils.waitUntilVisible(
            By.CSS_SELECTOR, 'html[data-role-name="RewardsPortal"]'
        )
