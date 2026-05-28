import logging

from selenium.common import TimeoutException
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
        try:
            container = self.webdriver.find_elements(By.ID, "user-pointclaim-container")
            if not container:
                logging.info("[BONUS POINTS] No bonus points banner found")
                return

            claim_button = container[0].find_elements(
                By.XPATH, ".//button[contains(@aria-label, 'Claim')]"
            )
            if not claim_button:
                logging.info("[BONUS POINTS] Banner present but no Claim button (already claimed?)")
                return

            logging.info("[BONUS POINTS] Bonus points available, clicking Claim...")
            claim_button[0].click()

            WebDriverWait(self.webdriver, 10).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "#user-pointclaim .title"), "claimed"
                )
            )
            title = self.webdriver.find_element(
                By.CSS_SELECTOR, "#user-pointclaim .title"
            ).text
            logging.info(f"[BONUS POINTS] {title}")

        except TimeoutException:
            logging.warning("[BONUS POINTS] Clicked Claim but could not verify success")
        except Exception:
            logging.error("[BONUS POINTS] Error claiming bonus points", exc_info=True)
