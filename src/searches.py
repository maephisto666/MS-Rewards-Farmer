import json
import logging
import random
import shelve
import time
from datetime import date, timedelta
from enum import Enum, auto
from itertools import cycle

import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from src.browser import Browser
from src.utils import Utils, RemainingSearches

LOAD_DATE = "loadDate"


class AttemptsStrategy(Enum):
    exponential = auto()
    constant = auto()


class Searches:
    config = Utils.loadConfig()
    maxAttempts: int = config.get("attempts", {}).get("max", 6)
    baseDelay: int = config.get("attempts", {}).get("base_delay_in_seconds", 60)
    attemptsStrategy = AttemptsStrategy[
        config.get("attempts", {}).get("strategy", AttemptsStrategy.constant.name)
    ]
    searchTerms: list[str] | None = None

    def __init__(self, browser: Browser, searches: RemainingSearches):
        self.browser = browser
        self.webdriver = browser.webdriver

        self.googleTrendsShelf: shelve.Shelf = shelve.open("google_trends")
        loadDate: date | None = None
        if LOAD_DATE in self.googleTrendsShelf:
            loadDate = self.googleTrendsShelf[LOAD_DATE]

        if loadDate is None or loadDate != date.today():
            self.googleTrendsShelf.clear()
            self.googleTrendsShelf[LOAD_DATE] = date.today()
            trends = self.getGoogleTrends(searches.getTotal())
            random.shuffle(trends)
            for trend in trends:
                self.googleTrendsShelf[trend] = None

    def getGoogleTrends(self, wordsCount: int) -> list[str]:
        # Function to retrieve Google Trends search terms
        searchTerms: list[str] = []
        i = 0
        while len(searchTerms) < wordsCount:
            i += 1
            # Fetching daily trends from Google Trends API
            r = requests.get(
                f"https://trends.google.com/trends/api/dailytrends?hl={self.browser.localeLang}"
                f'&ed={(date.today() - timedelta(days=i)).strftime("%Y%m%d")}&geo={self.browser.localeGeo}&ns=15'
            )
            trends = json.loads(r.text[6:])
            for topic in trends["default"]["trendingSearchesDays"][0][
                "trendingSearches"
            ]:
                searchTerms.append(topic["title"]["query"].lower())
                searchTerms.extend(
                    relatedTopic["query"].lower()
                    for relatedTopic in topic["relatedQueries"]
                )
            searchTerms = list(set(searchTerms))
        del searchTerms[wordsCount : (len(searchTerms) + 1)]
        return searchTerms

    def getRelatedTerms(self, word: str) -> list[str]:
        # Function to retrieve related terms from Bing API
        try:
            r = requests.get(
                f"https://api.bing.com/osjson.aspx?query={word}",
                headers={"User-agent": self.browser.userAgent},
            )
            return r.json()[1]
        except Exception:  # pylint: disable=broad-except
            logging.warning("", exc_info=True)
            return [word]

    def bingSearches(self, numberOfSearches: int, pointsCounter: int = 0):
        # Function to perform Bing searches
        logging.info(
            f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches..."
        )

        self.webdriver.get("https://bing.com")

        for searchCount in range(1, numberOfSearches + 1):
            logging.info(f"[BING] {searchCount}/{numberOfSearches}")
            searchTerm = list(self.googleTrendsShelf.keys())[0]
            pointsCounter = self.bingSearch(searchTerm)
            if not Utils.isDebuggerAttached():
                time.sleep(random.randint(10, 15))

        logging.info(
            f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches !"
        )
        self.googleTrendsShelf.close()
        return pointsCounter

    def bingSearch(self, word: str) -> int:
        # Function to perform a single Bing search
        bingAccountPointsBefore: int = self.browser.utils.getBingAccountPoints()

        wordsCycle: cycle[str] = cycle(self.getRelatedTerms(word))
        baseDelay = Searches.baseDelay
        originalWord = word

        for i in range(self.maxAttempts):
            try:
                searchbar: WebElement
                for _ in range(100):  # todo make configurable
                    self.browser.utils.waitUntilClickable(By.ID, "sb_form_q")
                    searchbar = self.webdriver.find_element(By.ID, "sb_form_q")
                    searchbar.clear()
                    word = next(wordsCycle)
                    logging.debug(f"word={word}")
                    searchbar.send_keys(word)
                    typed_word = searchbar.get_attribute("value")
                    if typed_word == word:
                        break
                    logging.debug(f"typed_word != word, {typed_word} != {word}")
                    self.browser.webdriver.refresh()
                else:
                    raise Exception("Problem sending words to searchbar")

                searchbar.submit()
                time.sleep(2)  # wait a bit for search to complete

                bingAccountPointsNow: int = self.browser.utils.getBingAccountPoints()
                if bingAccountPointsNow > bingAccountPointsBefore:
                    del self.googleTrendsShelf[originalWord]
                    return bingAccountPointsNow

                raise TimeoutException

            except TimeoutException:
                # todo
                # if i == (maxAttempts / 2):
                #     logging.info("[BING] " + "TIMED OUT GETTING NEW PROXY")
                #     self.webdriver.proxy = self.browser.giveMeProxy()
                self.browser.utils.tryDismissAllMessages()

                baseDelay += random.randint(1, 10)  # add some jitter
                logging.debug(
                    f"[BING] Search attempt failed {i + 1}/{Searches.maxAttempts}, retrying after sleeping {baseDelay}"
                    f" seconds..."
                )
                if not Utils.isDebuggerAttached():
                    time.sleep(baseDelay)

                if Searches.attemptsStrategy == AttemptsStrategy.exponential:
                    baseDelay *= 2
        # todo debug why we get to this point occasionally even though searches complete
        logging.error("[BING] Reached max search attempt retries")
        return bingAccountPointsBefore
