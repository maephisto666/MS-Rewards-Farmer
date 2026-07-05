import logging
from selenium.common import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.browser import Browser


class BonusPoints:
    """
    Class to handle bonus points claiming in MS Rewards.
    """

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver

    def claimBonusPoints(self) -> None:
        logging.info("[BONUS POINTS] Checking for bonus points to claim...")
        self._claim_streak_bonus()
        self._claim_banner_bonus()

    def _wait_for_button_interactable(self, button, timeout: int) -> bool:
        """Return True when button has non-zero size and is partially in the viewport."""
        try:
            WebDriverWait(self.webdriver, timeout).until(
                lambda d: d.execute_script(
                    "var r=arguments[0].getBoundingClientRect();"
                    "return r.width>0 && r.height>0 && r.top>=0 && r.top<window.innerHeight;",
                    button,
                )
            )
            return True
        except TimeoutException:
            return False

    def _claim_streak_bonus(self) -> None:
        """Click the 'Ready to claim' streak card on the dashboard.

        The RSC payload includes a pointsclaim block when there are accumulated
        daily-set streak points ready to collect. We check that first to avoid
        unnecessary DOM interaction on days where nothing is claimable.
        """
        dashboard = self.browser.utils.getDashboardData()
        if not dashboard.point_claim_points:
            logging.info("[BONUS POINTS] No streak bonus available")
            return

        logging.info(
            "[BONUS POINTS] %d streak point(s) ready to claim",
            dashboard.point_claim_points,
        )

        # The button may render late on first page load. Retry once after
        # reloading the dashboard if it is not yet interactable.
        button = None
        for attempt in range(1, 3):
            buttons = self.webdriver.find_elements(
                By.XPATH, "//button[.//p[text()='Ready to claim']]"
            )
            if buttons:
                self.webdriver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", buttons[0]
                )
                if self._wait_for_button_interactable(buttons[0], timeout=15):
                    button = buttons[0]
                    break
            if attempt < 2:
                logging.info(
                    "[BONUS POINTS] Button not ready on attempt %d — reloading dashboard",
                    attempt,
                )
                self.browser.utils.goToRewards()

        if button is None:
            logging.warning(
                "[BONUS POINTS] Ready to claim button never became interactable — giving up"
            )
            return

        # React Aria buttons use pointer events — ActionChains generates the full
        # pointerdown/pointerup/click sequence that triggers the React handler.
        ActionChains(self.webdriver).move_to_element(button).click().perform()
        logging.info("[BONUS POINTS] Clicked streak bonus card")

        # Wait for the side panel to open (aria-expanded flips to "true")
        try:
            WebDriverWait(self.webdriver, 8).until(
                lambda d: button.get_attribute("aria-expanded") == "true"
            )
        except TimeoutException:
            logging.warning("[BONUS POINTS] Side panel did not open")
            return

        # Find the 'Claim points' button inside the panel and wait until clickable
        try:
            claim_btn = WebDriverWait(self.webdriver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[.//span[text()='Claim points']]")
                )
            )
        except TimeoutException:
            logging.warning("[BONUS POINTS] 'Claim points' button not found in panel")
            return

        self.webdriver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", claim_btn
        )
        if not self._wait_for_button_interactable(claim_btn, timeout=5):
            logging.warning("[BONUS POINTS] 'Claim points' button not in viewport — attempting click anyway")

        ActionChains(self.webdriver).move_to_element(claim_btn).click().perform()
        logging.info("[BONUS POINTS] Clicked 'Claim points' in panel")

        # Panel closes when claim is accepted (aria-expanded returns to "false")
        try:
            WebDriverWait(self.webdriver, 10).until(
                lambda d: button.get_attribute("aria-expanded") == "false"
            )
            logging.info("[BONUS POINTS] Streak bonus claimed successfully")
        except (TimeoutException, StaleElementReferenceException):
            logging.warning("[BONUS POINTS] Could not confirm panel closed after claim")

    def _claim_banner_bonus(self) -> None:
        """Claim the old-style bonus-points banner if present (user-pointclaim-container)."""
        try:
            container = self.webdriver.find_elements(By.ID, "user-pointclaim-container")
            if not container:
                return

            claim_button = container[0].find_elements(
                By.XPATH, ".//button[contains(@aria-label, 'Claim')]"
            )
            if not claim_button:
                logging.info("[BONUS POINTS] Banner present but no Claim button (already claimed?)")
                return

            logging.info("[BONUS POINTS] Bonus points banner found, clicking Claim...")
            claim_button[0].click()

            WebDriverWait(self.webdriver, 10).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "#user-pointclaim .title"), "claimed"
                )
            )
            title = self.webdriver.find_element(
                By.CSS_SELECTOR, "#user-pointclaim .title"
            ).text
            logging.info("[BONUS POINTS] %s", title)

        except TimeoutException:
            logging.warning("[BONUS POINTS] Clicked banner Claim but could not verify success")
        except Exception:
            logging.error("[BONUS POINTS] Error claiming banner bonus", exc_info=True)
