import logging
import time

from selenium.webdriver.common.by import By

from src.browser import Browser
from .activities import Activities
from .utils import Utils


# todo Rename MoreActivities?
class MorePromotions:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.activities = Activities(browser)

    def completeMorePromotions(self):
        # Function to complete More Promotions
        logging.info("[MORE PROMOS] " + "Trying to complete More Promotions...")
        morePromotions: list[dict] = self.browser.utils.getDashboardData()[
            "morePromotions"
        ]
        self.browser.utils.goToRewards()
        for promotion in morePromotions:
            try:
                promotionTitle = promotion["title"]
                logging.debug(f"promotionTitle={promotionTitle}")
                # Open the activity for the promotion
                if (
                    promotion["complete"] is not False
                    or promotion["pointProgressMax"] == 0
                ):
                    logging.debug("Already done, continuing")
                    # todo Handle special "Quote of the day" which is falsely complete
                    continue
                if "Mid-week puzzle" in promotionTitle:
                    Utils.sendNotification(
                        "Mid-week puzzle found",
                        "MS-Rewards-Farmer detected mid-week puzzle activity, which isn't supported."
                        " Please manually complete",
                    )
                    continue
                self.activities.openMorePromotionsActivity(
                    morePromotions.index(promotion)
                )
                # todo These and following are US-English specific, maybe there's a good way to internationalize
                if "Search the lyrics of a song" in promotionTitle:
                    self.browser.webdriver.get(
                        "https://www.bing.com/search?q=black+sabbath+supernaut+lyrics"
                    )
                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "Translate anything" in promotionTitle:
                    self.browser.webdriver.get(
                        "https://www.bing.com/search?q=translate+pencil+sharpener+to+spanish"
                    )
                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "Discover open job roles" in promotionTitle:
                    self.browser.webdriver.get(
                        "https://www.bing.com/search?q=walmart+open+job+roles"
                    )
                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "Plan a quick getaway" in promotionTitle:
                    self.browser.webdriver.get(
                        "https://www.bing.com/search?q=flights+nyc+to+paris"
                    )
                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "You can track your package" in promotionTitle:
                    self.browser.webdriver.get(
                        "https://www.bing.com/search?q=usps+tracking"
                    )
                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "Find somewhere new to explore" in promotionTitle:
                    self.browser.webdriver.get(
                        "https://www.bing.com/search?q=directions+to+new+york"
                    )
                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "Too tired to cook tonight?" in promotionTitle:
                    searchbar = self.browser.utils.waitUntilClickable(
                        By.ID, "sb_form_q", timeToWait=20
                    )
                    searchbar.click()
                    searchbar.send_keys("pizza delivery near me")
                    searchbar.submit()

                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "Quickly convert your money" in promotionTitle:
                    searchbar = self.browser.utils.waitUntilClickable(
                        By.ID, "sb_form_q", timeToWait=20
                    )
                    searchbar.click()
                    searchbar.send_keys("convert 374 usd to yen")
                    searchbar.submit()

                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif "Learn to cook a new recipe" in promotionTitle:
                    searchbar = self.browser.utils.waitUntilClickable(
                        By.ID, "sb_form_q", timeToWait=20
                    )
                    searchbar.click()
                    searchbar.send_keys("how cook pierogi")
                    searchbar.submit()

                    time.sleep(2)
                    self.browser.utils.closeCurrentTab()
                elif promotion["promotionType"] == "urlreward":
                    # Complete search for URL reward
                    self.activities.completeSearch()
                elif (
                    promotion["promotionType"] == "quiz"
                    and promotion["pointProgress"] == 0
                ):
                    # Complete different types of quizzes based on point progress max
                    if promotion["pointProgressMax"] == 10:
                        self.activities.completeABC()
                    elif promotion["pointProgressMax"] in [30, 40]:
                        self.activities.completeQuiz()
                    elif promotion["pointProgressMax"] == 50:
                        self.activities.completeThisOrThat()
                else:
                    # Default to completing search
                    self.activities.completeSearch()
            except Exception:  # pylint: disable=broad-except
                logging.error("[MORE PROMOS] Error More Promotions", exc_info=True)
                # Reset tabs in case of an exception
                self.browser.utils.resetTabs()
                continue
        logging.info("[MORE PROMOS] Exiting")
