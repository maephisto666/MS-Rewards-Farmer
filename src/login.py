import logging

from pyotp import TOTP
from selenium.common import TimeoutException
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import Chrome

from src.browser import Browser
from src.utils import CONFIG, APPRISE


class LoginError(Exception):
    """
    Custom exception for login errors.
    """


class Login:
    """
    Class to handle login to MS Rewards.
    """
    browser: Browser
    webdriver: Chrome

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver
        self.utils = browser.utils

    def check_locked_user(self):
        try:
            element = self.webdriver.find_element(
                By.XPATH, "//div[@id='serviceAbuseLandingTitle']"
            )
            self.locked(element)
        except NoSuchElementException:
            pass

    def check_banned_user(self):
        try:
            element = self.webdriver.find_element(By.XPATH, '//*[@id="fraudErrorBody"]')
            self.banned(element)
        except NoSuchElementException:
            pass

    def locked(self, element):
        try:
            if element.is_displayed():
                logging.critical("This Account is Locked!")
                self.webdriver.close()
                raise LoginError("Account locked, moving to the next account.")
        except (ElementNotInteractableException, NoSuchElementException):
            pass

    def banned(self, element):
        try:
            if element.is_displayed():
                logging.critical("This Account is Banned!")
                self.webdriver.close()
                raise LoginError("Account banned, moving to the next account.")
        except (ElementNotInteractableException, NoSuchElementException):
            pass

    def login(self) -> None:
        try:
            if self.utils.isLoggedIn():
                logging.info("[LOGIN] Already logged-in")
            else:
                logging.info("[LOGIN] Logging-in...")
                self.execute_login()
                assert self.utils.isLoggedIn()
                logging.info("[LOGIN] Logged-in successfully!")
            self.check_locked_user()
            self.check_banned_user()
        except Exception as e:
            logging.error(f"Error during login: {e}")
            self.webdriver.close()
            raise

    def execute_login(self) -> None:
        self.webdriver.get("https://rewards.bing.com/Signin/")

        wait = WebDriverWait(self.webdriver, 10)

        # =====================================================================
        # STEP 1: Email entry
        #
        # Two known login forms:
        #   - New form: email field has id="usernameEntry", submit via primaryButton
        #   - Old form: email field has id="i0116", submit via idSIButton9
        #
        # Use EC.any_of to detect whichever form appears, avoiding sequential
        # timeouts that would slow down login.
        # =====================================================================
        try:
            emailField = wait.until(EC.any_of(
                EC.visibility_of_element_located((By.ID, "usernameEntry")),
                EC.visibility_of_element_located((By.ID, "i0116")),
            ))
        except TimeoutException:
            logging.debug(f"[LOGIN] No email field found. URL: {self.webdriver.current_url}, Title: {self.webdriver.title}")
            # Session might be partially active - check if we landed on a
            # post-login screen (passkey enrollment, stay signed in, etc.)
            current_url = self.webdriver.current_url.lower()
            if "passkey/enroll" in current_url:
                logging.info("[LOGIN] Landed on post-login screen, handling dialogs...")
                self._handle_post_login_dialogs(wait)
                return
            # Check if already on RewardsPortal
            try:
                self.utils.waitUntilVisible(
                    By.CSS_SELECTOR, 'html[data-role-name="RewardsPortal"]', 5
                )
                logging.info("[LOGIN] Already on RewardsPortal after redirect.")
                return
            except TimeoutException:
                raise TimeoutException(
                    f"[LOGIN] No email field and not on a known page. URL: {self.webdriver.current_url}"
                )

        is_new_login_form = emailField.get_attribute("id") == "usernameEntry"
        logging.debug(f"[LOGIN] {'New' if is_new_login_form else 'Old'} login form detected.")

        logging.info("[LOGIN] Entering email...")
        emailField.click()
        emailField.send_keys(self.browser.email)
        assert emailField.get_attribute("value") == self.browser.email
        if is_new_login_form:
            self.utils.waitUntilClickable(By.CSS_SELECTOR, "[data-testid='primaryButton']").click()
        else:
            self.utils.waitUntilClickable(By.ID, "idSIButton9").click()

        # =====================================================================
        # STEP 2: Post-email screen - navigate to password entry
        #
        # After submitting the email, different screens may appear:
        #
        #   Flow A (passkey-enabled accounts):
        #     Passkey screen with "Sign in another way" link
        #     (idA_PWD_SwitchToCredPicker) -> click it -> then click
        #     "Use your password"
        #
        #   Flow B (Outlook-app-enabled accounts):
        #     "Check your Outlook app" screen with "Use your password"
        #     directly available
        #
        #   Flow C (standard):
        #     Password field (name="passwd" or id="passwordEntry") directly
        #     available
        #
        # Use EC.any_of to detect whichever element appears first, avoiding
        # sequential timeouts that would slow down login.
        # =====================================================================
        logging.info("[LOGIN] Navigating to password screen...")
        try:
            result = wait.until(
                EC.any_of(
                    EC.element_to_be_clickable((By.ID, "idA_PWD_SwitchToCredPicker")),
                    EC.element_to_be_clickable((By.XPATH, "//span[@role='button' and contains(text(), 'Use your password')]")),
                    EC.element_to_be_clickable((By.NAME, "passwd")),
                    EC.visibility_of_element_located((By.ID, "passwordEntry")),
                )
            )
        except TimeoutException:
            raise TimeoutException(
                f"[LOGIN] Unknown post-email screen. URL: {self.webdriver.current_url}, Title: {self.webdriver.title}"
            )

        el_id = result.get_attribute("id") or ""
        el_name = result.get_attribute("name") or ""

        if el_id == "idA_PWD_SwitchToCredPicker":
            # Flow A: passkey screen -> click "Sign in another way" -> then "Use your password"
            logging.debug("[LOGIN] Passkey screen detected, clicking 'Sign in another way'...")
            result.click()
            use_password = wait.until(
                EC.any_of(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label="Use your password"]')),
                    EC.element_to_be_clickable((By.XPATH, "//span[@role='button' and contains(text(), 'Use your password')]")),
                )
            )
            use_password.click()
        elif el_name == "passwd" or el_id == "passwordEntry":
            # Flow C: password field directly available
            logging.debug("[LOGIN] Password field directly available.")
        else:
            # Flow B: "Use your password" already clickable (e.g. Outlook app screen)
            logging.debug("[LOGIN] 'Use your password' directly available, clicking...")
            result.click()

        # =====================================================================
        # STEP 3: Password entry
        #
        # Two known password fields:
        #   - New form: id="passwordEntry"
        #   - Old form: name="passwd"
        #
        # Submit is always via primaryButton (works for both forms).
        # =====================================================================
        passwordField = wait.until(EC.any_of(
            EC.element_to_be_clickable((By.NAME, "passwd")),
            EC.element_to_be_clickable((By.ID, "passwordEntry")),
        ))
        logging.info("[LOGIN] Entering password...")
        passwordField.click()
        passwordField.send_keys(self.browser.password)
        assert passwordField.get_attribute("value") == self.browser.password
        self.utils.waitUntilClickable(By.CSS_SELECTOR, "[data-testid='primaryButton']").click()

        # =====================================================================
        # STEP 4: Post-password 2FA - navigate to TOTP entry
        #
        # After password submission, different 2FA screens may appear:
        #
        #   Flow A: TOTP screen directly (OneTimeCodeViewForm)
        #     -> proceed to enter OTP
        #
        #   Flow B: "Approve sign-in request" screen
        #     -> click "Other ways to sign in" button
        #     -> click "Enter a code from an authenticator app"
        #     -> TOTP screen (OneTimeCodeViewForm)
        #
        # The "Approve sign-in request" screen has a 1-minute timeout,
        # so we must detect it quickly and not waste time on sequential waits.
        # =====================================================================
        logging.info("[LOGIN] Checking for 2FA...")
        result = wait.until(
            EC.any_of(
                EC.visibility_of_element_located((By.NAME, "OneTimeCodeViewForm")),
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Other ways to sign in')]")),
            )
        )

        if result.get_attribute("name") != "OneTimeCodeViewForm":
            # Flow B: "Approve sign-in request" -> navigate to TOTP
            logging.debug("[LOGIN] 'Approve sign-in request' detected, navigating to TOTP...")
            result.click()
            # The "Almost there" page shows auth options as cards in a
            # data-testid="tileList". Each card is a div[data-testid="tile"]
            # with an aria-label. Click the first tile (authenticator app).
            auth_app_option = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='tileList'] [data-testid='tile'] span[role='button']"))
            )
            auth_app_option.click()
            self.utils.waitUntilVisible(By.NAME, "OneTimeCodeViewForm", 10)

        # =====================================================================
        # STEP 5: TOTP entry
        #
        # The OTP input field has a dynamic ID (e.g. floatingLabelInput5,
        # floatingLabelInput13) depending on the account/flow. Instead of
        # hardcoding an ID, we find the visible text input inside the
        # OneTimeCodeViewForm.
        # =====================================================================
        if self.browser.totp is not None:
            logging.info("[LOGIN] Entering OTP...")
            otp = TOTP(self.browser.totp.replace(" ", "")).now()
            otp_form = self.utils.waitUntilVisible(By.NAME, "OneTimeCodeViewForm", 10)
            otpField = otp_form.find_element(By.CSS_SELECTOR, "input[type='text']")
            otpField.send_keys(otp)
            assert otpField.get_attribute("value") == otp
            self.utils.waitUntilClickable(By.CSS_SELECTOR, "[data-testid='primaryButton']").click()
        else:
            assert CONFIG.browser.visible, (
                "[LOGIN] 2FA detected, provide TOTP token or run in visible mode to handle login."
            )
            print("[LOGIN] 2FA detected, handle prompts and press enter when done.")
            input()

        # =====================================================================
        # STEP 6: Post-login dialogs
        #
        # After successful authentication, various optional dialogs may appear:
        #   - "Is your security info still accurate?" (looks good)
        #   - "Stay signed in?" (primaryButton)
        #   - "Creating a passkey..." (passkey enrollment prompt)
        #   - "Keep me signed in" form (kmsiForm / acceptButton)
        #   - "Protect your account" prompt
        #   - HTTP error pages (504, timeout)
        #
        # We handle each one if it appears, dismissing or confirming as needed.
        # =====================================================================
        logging.info("[LOGIN] Handling post-login dialogs...")
        self._handle_post_login_dialogs(wait)

    def _handle_post_login_dialogs(self, wait) -> None:
        self.check_locked_user()
        self.check_banned_user()

        for _ in range(5):
            try:
                self.utils.waitUntilVisible(
                    By.CSS_SELECTOR, 'html[data-role-name="RewardsPortal"]', 5
                )
                return
            except TimeoutException:
                pass

            # HTTP error page (e.g. 504 from failed OIDC redirect)
            page_text = self.webdriver.page_source
            if "HTTP ERROR" in page_text or "ERR_TIMED_OUT" in page_text or "isn't working" in page_text:
                logging.warning(f"[LOGIN] Error page detected (URL: {self.webdriver.current_url}). Retrying navigation...")
                self.webdriver.get("https://rewards.bing.com/")
                continue

            # "Is your security info still accurate?" dialog (old form, uses element IDs)
            try:
                self.webdriver.find_element(By.ID, "iPageTitle")
                logging.info("[LOGIN] Dismissing 'looks good' dialog...")
                self.webdriver.find_element(By.ID, "iLooksGood").click()
                continue
            except NoSuchElementException:
                pass

            # Passkey enrollment page
            if "passkey/enroll" in self.webdriver.current_url:
                logging.info("[LOGIN] Dismissing passkey dialog...")
                try:
                    self.utils.waitUntilClickable(By.CSS_SELECTOR, "[data-testid='secondaryButton']", 3).click()
                    continue
                except TimeoutException:
                    pass
                try:
                    self.utils.waitUntilClickable(By.CSS_SELECTOR, "[data-testid='dismissIcon']", 3).click()
                    continue
                except TimeoutException:
                    pass
                try:
                    self.utils.waitUntilClickable(By.CSS_SELECTOR, "[data-testid='primaryButton']", 5).click()
                    continue
                except TimeoutException:
                    pass
                logging.warning("[LOGIN] Could not dismiss passkey dialog, navigating away...")
                self.webdriver.get("https://rewards.bing.com/")
                continue

            # "Keep me signed in" form (old login form)
            try:
                self.webdriver.find_element(By.NAME, "kmsiForm")
                logging.info("[LOGIN] Dismissing 'Keep me signed in' form...")
                self.utils.waitUntilClickable(By.ID, "acceptButton").click()
                continue
            except NoSuchElementException:
                pass

            # Generic primaryButton (catch-all for "Stay signed in?", etc.)
            try:
                btn = self.webdriver.find_element(By.CSS_SELECTOR, "[data-testid='primaryButton']")
                if btn.is_displayed():
                    logging.info("[LOGIN] Clicking primaryButton to advance...")
                    btn.click()
                    continue
            except NoSuchElementException:
                pass

        # Final check for "Protect your account" prompt
        isAskingToProtect = self.utils.checkIfTextPresentAfterDelay("protect your account", 5)
        if isAskingToProtect:
            assert CONFIG.browser.visible, (
                "Account protection detected, run in visible mode to handle login"
            )
            print("Account protection detected, handle prompts and press enter when on rewards page")
            input()

        self.utils.waitUntilVisible(
            By.CSS_SELECTOR, 'html[data-role-name="RewardsPortal"]'
        )
