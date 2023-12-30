import logging

from src.browser import Browser

from .activities import Activities


class MorePromotions:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.activities = Activities(browser)

    def completeMorePromotions(self):
        # Function to complete More Promotions
        logging.info("[MORE PROMOS] " + "Trying to complete More Promotions...")
        self.browser.utils.goHome()
        morePromotions = self.browser.utils.getDashboardData()["morePromotions"]
        i = 0
        for promotion in morePromotions:
            try:
                i += 1
                if (
                    promotion["complete"] is False
                    and promotion["pointProgressMax"] != 0
                ):
                    # Open the activity for the promotion
                    self.activities.openMorePromotionsActivity(i)
                    if promotion["promotionType"] == "urlreward":
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
                # Reset tabs in case of an exception
                self.browser.utils.resetTabs()
        logging.info("[MORE PROMOS] Completed More Promotions successfully !")
