import contextlib
import logging
import random
from random import randint
from time import sleep

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.browser import Browser
from src.constants import REWARDS_URL
from src.rsc import DailySetItem
from src.utils import (
    CONFIG,
    APPRISE,
    getAnswerCode,
    cooldown,
    ACTIVITY_TITLES_TO_QUERIES,
    IGNORED_ACTIVITIES,
)


class Activities:
    """
    Class to handle activities in MS Rewards.
    """

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver
        self.unmapped_activities: list[str] = []

    def completeSearch(self):
        # Simulate completing a search activity
        pass

    def completeSurvey(self):
        # Simulate completing a survey activity
        # noinspection SpellCheckingInspection
        self.browser.utils.waitUntilClickable(By.ID, f"btoption{randint(0, 1)}").click()

    def completeQuiz(self):
        # Simulate completing a quiz activity
        with contextlib.suppress(
            TimeoutException
        ):  # Handles in case quiz was started in previous run
            startQuiz = self.browser.utils.waitUntilQuizLoads()
            self.browser.utils.click(startQuiz)
        self.browser.utils.waitUntilVisible(By.ID, "overlayPanel", 5)
        maxQuestions = self.webdriver.execute_script(
            "return _w.rewardsQuizRenderInfo.maxQuestions"
        )
        numberOfOptions = self.webdriver.execute_script(
            "return _w.rewardsQuizRenderInfo.numberOfOptions"
        )
        while True:
            correctlyAnsweredQuestionCount: int = self.webdriver.execute_script(
                "return _w.rewardsQuizRenderInfo.CorrectlyAnsweredQuestionCount"
            )

            if correctlyAnsweredQuestionCount == maxQuestions:
                return

            self.browser.utils.waitUntilQuestionRefresh()

            sleep(10)

            if numberOfOptions == 8:
                answers = []
                for i in range(numberOfOptions):
                    isCorrectOption = self.webdriver.find_element(
                        By.ID, f"rqAnswerOption{i}"
                    ).get_attribute("iscorrectoption")
                    if isCorrectOption and isCorrectOption.lower() == "true":
                        answers.append(f"rqAnswerOption{i}")
                for answer in answers:
                    element = self.webdriver.find_element(By.ID, answer)
                    self.browser.utils.click(element)
            elif numberOfOptions in [2, 3, 4]:
                correctOption = self.webdriver.execute_script(
                    "return _w.rewardsQuizRenderInfo.correctAnswer"
                )
                for i in range(numberOfOptions):
                    if (
                        self.webdriver.find_element(
                            By.ID, f"rqAnswerOption{i}"
                        ).get_attribute("data-option")
                        == correctOption
                    ):
                        correctAnswer = self.browser.utils.waitUntilClickable(
                            By.ID, f"rqAnswerOption{i}"
                        )
                        self.browser.utils.click(correctAnswer)
                        break

    def completeABC(self):
        # Simulate completing an ABC activity
        counter = self.webdriver.find_element(
            By.XPATH, '//*[@id="QuestionPane0"]/div[2]'
        ).text[:-1][1:]
        numberOfQuestions = max(int(s) for s in counter.split() if s.isdigit())
        for question in range(numberOfQuestions):
            element = self.webdriver.find_element(
                By.ID, f"questionOptionChoice{question}{randint(0, 2)}"
            )
            self.browser.utils.click(element)
            sleep(randint(10, 15))
            element = self.webdriver.find_element(By.ID, f"nextQuestionbtn{question}")
            self.browser.utils.click(element)
            sleep(randint(10, 15))

    def completeThisOrThat(self):
        # Simulate completing a This or That activity
        with contextlib.suppress(
            TimeoutException
        ):  # Handles in case quiz was started in previous run
            startQuiz = self.browser.utils.waitUntilQuizLoads()
            self.browser.utils.click(startQuiz)
        self.browser.utils.waitUntilQuestionRefresh()
        for _ in range(10):
            correctAnswerCode = self.webdriver.execute_script(
                "return _w.rewardsQuizRenderInfo.correctAnswer"
            )
            answer1, answer1Code = self.getAnswerAndCode("rqAnswerOption0")
            answer2, answer2Code = self.getAnswerAndCode("rqAnswerOption1")
            answerToClick: WebElement
            if answer1Code == correctAnswerCode:
                answerToClick = answer1
            elif answer2Code == correctAnswerCode:
                answerToClick = answer2

            self.browser.utils.click(answerToClick)
            sleep(randint(10, 15))

    def getAnswerAndCode(self, answerId: str) -> tuple[WebElement, str]:
        # Helper function to get answer element and its code
        answerEncodeKey = self.webdriver.execute_script("return _G.IG")
        answer = self.webdriver.find_element(By.ID, answerId)
        answerTitle = answer.get_attribute("data-option")
        return (
            answer,
            getAnswerCode(answerEncodeKey, answerTitle),
        )

    def completeActivity(self, item: DailySetItem) -> None:
        title = cleanupActivityTitle(item.title)
        logging.debug("completeActivity: title=%r destination=%r points=%d", title, item.destination, item.points)

        if item.is_completed:
            logging.debug("Already completed, skipping")
            return
        if item.is_locked:
            logging.debug("Locked, skipping")
            return
        if item.points == 0:
            logging.debug("Zero points, skipping")
            return
        if title in IGNORED_ACTIVITIES:
            logging.debug("Ignored activity, skipping: %r", title)
            return
        if "puzzle" in title.lower() or title == "Windows search":
            logging.info("[ACTIVITY] Skipping '%s' (not supported)", title)
            return

        if title not in ACTIVITY_TITLES_TO_QUERIES and title not in self.unmapped_activities:
            self.unmapped_activities.append(title)

        if not item.destination:
            logging.warning("[ACTIVITY] No destination URL for '%s', skipping", title)
            return

        try:
            logging.info("[ACTIVITY] Starting '%s' → %s", title, item.destination)
            self.webdriver.get(item.destination)

            # Wait for the destination page to settle
            sleep(3)

            # Detect page type by what's present on the destination page
            # and handle accordingly.

            # Quiz page (rewardsQuizRenderInfo global present)
            try:
                max_questions = self.webdriver.execute_script(
                    "return typeof _w !== 'undefined' && _w.rewardsQuizRenderInfo "
                    "? _w.rewardsQuizRenderInfo.maxQuestions : null"
                )
                num_options = self.webdriver.execute_script(
                    "return typeof _w !== 'undefined' && _w.rewardsQuizRenderInfo "
                    "? _w.rewardsQuizRenderInfo.numberOfOptions : null"
                )
                if max_questions is not None:
                    logging.info("[ACTIVITY] Quiz detected (maxQuestions=%s options=%s)", max_questions, num_options)
                    if num_options == 8 or num_options in [2, 3, 4]:
                        self.completeQuiz()
                    else:
                        self.completeThisOrThat()
                    return
            except Exception:
                pass

            # Poll / survey page (btoption elements)
            with contextlib.suppress(Exception):
                if self.webdriver.find_elements(By.ID, "btoption0"):
                    logging.info("[ACTIVITY] Poll detected")
                    self.completeSurvey()
                    return

            # ABC-style quiz (QuestionPane0 present)
            with contextlib.suppress(Exception):
                if self.webdriver.find_elements(By.XPATH, '//*[@id="QuestionPane0"]'):
                    logging.info("[ACTIVITY] ABC quiz detected")
                    self.completeABC()
                    return

            # Search / URL-reward: try to interact with the searchbar if present,
            # otherwise just navigating to the destination URL is sufficient.
            searchbar = None
            with contextlib.suppress(TimeoutException):
                searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=10)

            if searchbar is not None:
                self.browser.utils.click(searchbar)
                searchbar.clear()
                if title in ACTIVITY_TITLES_TO_QUERIES:
                    query = random.choice(ACTIVITY_TITLES_TO_QUERIES[title])
                else:
                    # Use the search term already embedded in the destination URL if possible
                    import urllib.parse
                    qs = urllib.parse.urlparse(item.destination).query
                    params = urllib.parse.parse_qs(qs)
                    query = (params.get("q") or params.get("query") or [title])[0]
                searchbar.send_keys(query)
                searchbar.submit()
                with contextlib.suppress(TimeoutException):
                    WebDriverWait(self.webdriver, 10).until(
                        EC.presence_of_element_located((By.ID, "b_results"))
                    )
                logging.info("[ACTIVITY] Search submitted for '%s' with query '%s'", title, query)
            else:
                # Pure URL-reward: navigation to destination is the activity.
                logging.info("[ACTIVITY] URL-reward navigation complete for '%s'", title)

        except Exception:
            logging.error("[ACTIVITY] Error completing '%s'", title, exc_info=True)
            return
        finally:
            self.browser.utils.resetTabs()
        cooldown()

    def completeActivities(self):
        logging.info("[ACTIVITIES] Trying to complete all activities...")
        items = self.browser.utils.getActivities()
        for item in items:
            self.completeActivity(item)
        if self.unmapped_activities:
            logging.info(
                "[ACTIVITIES] Activities with no mapped query (destination URL used as fallback): %s",
                ", ".join(repr(t) for t in self.unmapped_activities),
            )
        logging.info("[ACTIVITIES] Done")

        if CONFIG.get("apprise.notify.incomplete-activity"):
            items_after = self.browser.utils.getActivities()
            incomplete = [
                cleanupActivityTitle(i.title)
                for i in items_after
                if not i.is_completed and not i.is_locked
                and cleanupActivityTitle(i.title) not in IGNORED_ACTIVITIES
            ]
            if incomplete:
                logging.info("incompleteActivities: %s", incomplete)
                APPRISE.notify(
                    '"' + '", "'.join(incomplete) + '"\n' + REWARDS_URL,
                    f"We found some incomplete activities for {self.browser.email}",
                )


def cleanupActivityTitle(activityTitle: str) -> str:
    return activityTitle.replace("\u200b", "").replace("\xa0", " ")
