import contextlib
import logging
import random
import time

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from typing_extensions import deprecated

from src.browser import Browser
from .activities import Activities
from .utils import Utils, CONFIG

PROMOTION_TITLE_TO_SEARCH = {
    "Search the lyrics of a song": "black sabbath supernaut lyrics",
    "Translate anything": "translate pencil sharpener to spanish",
    "Let's watch that movie again!": "aliens movie",
    "Discover open job roles": "walmart open job roles",
    "Plan a quick getaway": "flights nyc to paris",
    "You can track your package": "usps tracking",
    "Find somewhere new to explore": "directions to new york",
    "Too tired to cook tonight?": "Pizza Hut near me",
    "Quickly convert your money": "convert 374 usd to yen",
    "Learn to cook a new recipe": "how cook pierogi",
    "Find places to stay": "hotels rome italy",
    "How's the economy?": "sp 500",
    "Who won?": "braves score",
    "Gaming time": "vampire survivors video game",
    "What time is it?": "china time",
    "Houses near you": "apartments manhattan",
    "Get your shopping done faster": "chicken tenders",
    "Expand your vocabulary": "define polymorphism",
    "Stay on top of the elections": "election news latest",
    "Prepare for the weather": "weather tomorrow",
}


@deprecated("Use Activities")
# todo Rename MoreActivities?
class MorePromotions:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.activities = Activities(browser)

    # todo Refactor so less complex
    def completeMorePromotions(self):
        # Function to complete More Promotions
        logging.info("[MORE PROMOS] " + "Trying to complete More Promotions...")
        morePromotions: list[dict] = self.browser.utils.getDashboardData()[
            "morePromotions"
        ]
        self.browser.utils.goToRewards()
        for promotion in morePromotions:
            try:
                promotionTitle = (
                    promotion["title"].replace("\u200b", "").replace("\xa0", " ")
                )
                logging.debug(f"promotionTitle={promotionTitle}")
                # Open the activity for the promotion
                if (
                    promotion["complete"] is not False
                    or promotion["pointProgressMax"] == 0
                ):
                    logging.debug("Already done, continuing")
                    continue
                self.activities.openMorePromotionsActivity(
                    morePromotions.index(promotion)
                )
                self.browser.webdriver.execute_script("window.scrollTo(0, 1080)")
                with contextlib.suppress(TimeoutException):
                    searchbar = self.browser.utils.waitUntilClickable(
                        By.ID, "sb_form_q"
                    )
                    self.browser.utils.click(searchbar)
                # todo These and following are US-English specific, maybe there's a good way to internationalize
                if promotionTitle in PROMOTION_TITLE_TO_SEARCH:
                    searchbar.send_keys(PROMOTION_TITLE_TO_SEARCH[promotionTitle])
                    searchbar.submit()
                elif promotion["promotionType"] == "urlreward":
                    # Complete search for URL reward
                    self.activities.completeSearch()
                elif promotion["promotionType"] == "quiz":
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
                self.browser.webdriver.execute_script("window.scrollTo(0, 1080)")
                time.sleep(random.randint(5, 10))

                self.browser.utils.resetTabs()
                time.sleep(2)
            except Exception:  # pylint: disable=broad-except
                logging.error("[MORE PROMOS] Error More Promotions", exc_info=True)
                # Reset tabs in case of an exception
                self.browser.utils.resetTabs()
                continue
        if CONFIG.get("apprise").get("notify").get("incomplete-activity"):
            incompletePromotions: list[tuple[str, str]] = []
            for promotion in self.browser.utils.getDashboardData()[
                "morePromotions"
            ]:  # Have to refresh
                if promotion["pointProgress"] < promotion["pointProgressMax"]:
                    incompletePromotions.append(
                        (promotion["title"], promotion["promotionType"])
                    )
            if incompletePromotions:
                Utils.sendNotification(
                    f"We found some incomplete promotions for {self.browser.username} to do!",
                    incompletePromotions,
                )
        logging.info("[MORE PROMOS] Exiting")
