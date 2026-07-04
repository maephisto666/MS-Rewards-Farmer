import contextlib
import logging
from random import randint
from time import sleep

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from src.browser import Browser
from src.constants import REWARDS_URL
from src.rsc import DailySetItem
from src.utils import (
    CONFIG,
    APPRISE,
    getAnswerCode,
    cooldown,
    IGNORED_ACTIVITIES,
)


class Activities:
    """
    Class to handle activities in MS Rewards.
    """

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver

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

    def _click_activity_anchor(self, item: DailySetItem) -> bool:
        """
        Find and JS-click the dashboard card anchor for item.
        Returns True if found and clicked, False if the anchor is not in the
        current slide's DOM (caller must advance the carousel and retry).
        """
        token = item.url_selector_token
        anchors = self.webdriver.find_elements(
            By.XPATH, f"//a[contains(@href, '{token}')]"
        )
        if not anchors:
            return False

        anchor = anchors[0]
        self.webdriver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", anchor
        )
        sleep(1)
        self.webdriver.execute_script("arguments[0].click();", anchor)
        logging.info(
            "[ACTIVITY] [%s] Clicked '%s'",
            item.activity_type, cleanupActivityTitle(item.title),
        )
        # Let the destination page register the credit, then close any new tab
        sleep(8)
        self.browser.utils.resetTabs()
        cooldown()
        return True

    def completeActivities(self):
        logging.info("[ACTIVITIES] Trying to complete all activities...")

        # Read dashboard RSC — only today's items have clickable anchors.
        # The RSC payload includes 3 days of items (today + 2 future days).
        dashboard = self.browser.utils.getDashboardData()
        items = dashboard.todays_daily_set()

        todo = []
        for item in items:
            title = cleanupActivityTitle(item.title)
            atype = item.activity_type
            if item.is_completed:
                continue
            if item.is_locked:
                continue
            if item.points == 0:
                continue
            if title in IGNORED_ACTIVITIES:
                continue
            if atype == "REFERRAL":
                logging.info("[ACTIVITY] Skipping '%s' (REFERRAL)", title)
                continue
            if not item.destination:
                logging.warning("[ACTIVITY] No destination for '%s', skipping", title)
                continue
            todo.append(item)

        if not todo:
            logging.info("[ACTIVITIES] Nothing to do today.")
            logging.info("[ACTIVITIES] Done")
            return

        logging.info("[ACTIVITIES] %d items to complete today", len(todo))

        # All today's cards are on the first (visible) slide — no carousel navigation needed.
        for item in todo:
            clicked = self._click_activity_anchor(item)
            if clicked:
                self.browser.utils.goToRewards()
                sleep(3)
            else:
                logging.warning(
                    "[ACTIVITY] No anchor found for '%s' (token=%r) — skipping",
                    cleanupActivityTitle(item.title), item.url_selector_token,
                )

        logging.info("[ACTIVITIES] Done")

        if CONFIG.get("apprise.notify.incomplete-activity"):
            items_after = self.browser.utils.getActivities()
            incomplete = [
                cleanupActivityTitle(i.title)
                for i in items_after
                if not i.is_completed and not i.is_locked
                and cleanupActivityTitle(i.title) not in IGNORED_ACTIVITIES
                and i.activity_type != "REFERRAL"
            ]
            if incomplete:
                logging.info("incompleteActivities: %s", incomplete)
                APPRISE.notify(
                    '"' + '", "'.join(incomplete) + '"\n' + REWARDS_URL,
                    f"We found some incomplete activities for {self.browser.email}",
                )


def cleanupActivityTitle(activityTitle: str) -> str:
    return activityTitle.replace("\u200b", "").replace("\xa0", " ")
