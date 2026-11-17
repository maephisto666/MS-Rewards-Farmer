import logging
from enum import Enum, auto
from random import random
from time import sleep
from typing import Final

from selenium.webdriver.common.by import By

from src.browser import Browser
from src.trends import TrendsCache
from src.utils import CONFIG, getProjectRoot, cooldown, COUNTRY


class RetriesStrategy(Enum):
    """
    method to use when retrying
    """

    EXPONENTIAL = auto()
    """
    an exponentially increasing `backoff-factor` between attempts
    """
    CONSTANT = auto()
    """
    the default; a constant `backoff-factor` between attempts
    """


class Searches:
    """
    Class to handle searches in MS Rewards.
    """

    maxRetries: Final[int] = CONFIG.retries.max
    """
    the max amount of retries to attempt
    """
    baseDelay: Final[float] = CONFIG.get("retries.backoff-factor")
    """
    how many seconds to delay
    """
    # retriesStrategy = Final[  # todo Figure why doesn't work with equality below
    retriesStrategy = RetriesStrategy[CONFIG.retries.strategy]

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver

        self.trends = TrendsCache(getProjectRoot() / "google_trends.json", COUNTRY)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def bingSearches(self) -> None:
        # Function to perform Bing searches
        logging.info(
            f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches..."
        )

        # Make sure www.bing.com is authenticated for search rewards before we
        # start — otherwise searches earn nothing and the counter never appears
        # (issue #36). No-op when already authenticated.
        self.browser.utils.ensureBingSearchAuth()

        self.browser.utils.goToSearch()

        while True:
            remainingSearches = self.browser.getRemainingSearches()
            logging.info(f"[BING] Remaining searches={remainingSearches}")
            if remainingSearches == 0:
                break

            self.trends.refresh(remainingSearches)

            result_search_counted = self.bingSearch()
            if not result_search_counted:
                logging.info(
                    f"[BING] Giving up on {self.browser.browserType.capitalize()} Edge Bing searches !"
                )
                return

        logging.info(
            f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches !"
        )

    def bingSearch(self) -> bool:
        # Function to perform a single Bing search
        pointsBefore = self.browser.utils.getAccountPoints()

        picked = self.trends.pick()
        if picked is None:
            logging.error("[BING] No trending keywords available to search for")
            return False
        trend, trendKeywords = picked
        logging.debug(f"trendKeywords={trendKeywords}")
        logging.debug(f"trend={trend}")
        baseDelay = Searches.baseDelay

        for i in range(self.maxRetries + 1):
            if i != 0:
                if not trendKeywords:
                    self.trends.markUsed(trend)
                    self.trends.refresh(1)

                    picked = self.trends.pick()
                    if picked is None:
                        logging.error("[BING] No trending keywords available to search for")
                        return False
                    trend, trendKeywords = picked

                sleepTime: int
                if Searches.retriesStrategy == Searches.retriesStrategy.EXPONENTIAL:
                    sleepTime = baseDelay * 2 ** (i - 1)
                elif Searches.retriesStrategy == Searches.retriesStrategy.CONSTANT:
                    sleepTime = baseDelay
                else:
                    raise AssertionError
                sleepTime = round(sleepTime + baseDelay * random())
                logging.info(
                    f"[BING] Search attempt not counted {i}/{Searches.maxRetries},"
                    f" sleeping {sleepTime}"
                    f" seconds..."
                )
                sleep(sleepTime)

            self.browser.utils.goToSearch()
            searchbar = self.browser.utils.waitUntilClickable(
                By.ID, "sb_form_q", timeToWait=40
            )
            searchbar.clear()
            trendKeyword = trendKeywords.pop(0)
            logging.debug(f"trendKeyword={trendKeyword}")
            sleep(1)
            searchbar.send_keys(trendKeyword)
            sleep(1)
            searchbar.submit()

            pointsAfter = self.browser.utils.getAccountPoints()
            if pointsBefore < pointsAfter:
                self.trends.markUsed(trend)
                cooldown()
                return True

            # todo
            # if i == (maxRetries / 2):
            #     logging.info("[BING] " + "TIMED OUT GETTING NEW PROXY")
            #     self.webdriver.proxy = self.browser.giveMeProxy()
        logging.error("[BING] Reached max search attempt retries")
        return False
