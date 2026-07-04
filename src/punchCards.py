import logging

from src.browser import Browser


class PunchCards:
    """
    Class to handle punch cards in MS Rewards.
    """

    def __init__(self, browser: Browser):
        self.browser = browser

    def completePunchCards(self):
        # Punch cards are not exposed in the new Next.js RSC data model (July 2026
        # redesign). Skip until a new extraction path is identified.
        logging.info("[PUNCH CARDS] Skipped — punch card data not available in new dashboard")

    def completePromotionalItems(self):
        # Promotional items are not exposed in the new Next.js RSC data model.
        pass
