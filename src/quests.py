import logging

from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from src.browser import Browser
from src.constants import REWARDS_QUEST_URL
from src.rsc import QuestPage, QuestStep, parse_quest_cards, parse_quest_page
from src.utils import cooldown

VERIFY_TIMEOUT = 30
VERIFY_POLL = 4
"""
How long (seconds) and how often the quest page is reloaded after a click to see
the step as done: the server registers it a few seconds after the page opens.
"""

IGNORED_QUESTS = ("Spotify",)
"""
Fragments of the offer ids of the quests that are not handled: the Spotify
promotion. Whatever else is in the Quests section of the /earn page is the monthly
quest, whose title changes every month, or the weekly quest of the Rewards desktop app.
Quests are recognized by their offer id and never by their title.
"""

APP_QUEST = "RewardsApp"
"""
Fragment of the offer id of the weekly quest of the Rewards desktop app (the week is
part of the id, so it is never matched in full). Its steps are only unlocked for the
requests that look like they come from the app.
"""


class Quests:
    """
    Class to handle the quests of the /earn page of MS Rewards.

    A quest is made of a few steps, each one a button that opens a page in a new
    tab. Only the first unfinished step is available: the next one unlocks 24
    hours after it, so at most one step per quest is done per run. The weekly quest
    of the Rewards desktop app has one step per day of the week instead, and only
    today's one is available: it is done with the browser presented as the app.
    """

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver

    def _questOfferIds(self) -> list[str]:
        self.browser.utils.goToEarn()
        offerIds = parse_quest_cards(self.webdriver.page_source)
        return [o for o in offerIds if not any(i in o for i in IGNORED_QUESTS)]

    def _loadQuest(self, offerId: str) -> QuestPage:
        # A full page load (not a client-side navigation) is needed: only then
        # the step data is embedded in the page.
        self.webdriver.get(REWARDS_QUEST_URL + offerId)
        assert self.webdriver.current_url.startswith(
            "https://rewards.bing.com/"
        ), f"Unexpected URL after navigating to a quest: {self.webdriver.current_url}"
        self.browser.utils.dismissCookieBanner()
        return parse_quest_page(self.webdriver.page_source)

    def _clickStep(self, step: QuestStep) -> bool:
        """
        Click the button of the step and let the page it opens load.
        Returns False if the button is not found or no page was opened.
        """
        # The step's button is a React Aria link: it needs a real pointer click,
        # a JS click is silently ignored.
        try:
            WebDriverWait(self.webdriver, 10).until(
                lambda d: self._findStepAnchor(step) is not None
            )
        except TimeoutException:
            logging.warning("[QUESTS] Button for '%s' not in DOM", step.aria_label)
            return False

        anchor = self._findStepAnchor(step)
        self.webdriver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", anchor
        )
        mainHandle = self.webdriver.current_window_handle
        ActionChains(self.webdriver).move_to_element(anchor).click().perform()
        logging.info("[QUESTS] Clicked '%s'", step.aria_label)

        # The step is registered while the new page loads: let it finish, then
        # the page itself is of no interest and is closed.
        try:
            WebDriverWait(self.webdriver, 12).until(
                lambda d: len(d.window_handles) > 1
            )
        except TimeoutException:
            logging.warning("[QUESTS] No page opened for '%s'", step.aria_label)
            return False

        self.webdriver.switch_to.window(self.webdriver.window_handles[-1])
        try:
            WebDriverWait(self.webdriver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            logging.debug("[QUESTS] The opened page did not finish loading")
        for handle in self.webdriver.window_handles:
            if handle != mainHandle:
                self.webdriver.switch_to.window(handle)
                self.webdriver.close()
        self.webdriver.switch_to.window(mainHandle)
        return True

    def _findStepAnchor(self, step: QuestStep):
        for anchor in self.webdriver.find_elements(
            By.XPATH, "//a[@target='_blank'][@aria-label]"
        ):
            if anchor.get_attribute("aria-label") == step.aria_label:
                return anchor
        return None

    def _completeQuest(self, offerId: str) -> bool:
        """Returns True if a step was clicked, False if there was nothing to do."""
        if APP_QUEST not in offerId:
            return self._completeNextStep(offerId)
        # The page has to be loaded, clicked and reloaded to verify with the same
        # identity, or the step would be locked again.
        logging.info("[QUESTS] %s: presenting the browser as the Rewards app", offerId)
        with self.browser.rewardsAppIdentity():
            return self._completeNextStep(offerId)

    def _completeNextStep(self, offerId: str) -> bool:
        page = self._loadQuest(offerId)
        step = page.next_step()
        if step is None:
            logging.info(
                "[QUESTS] %s: no step available now (%s)", offerId, page.progress or "?"
            )
            return False

        if not self._clickStep(step):
            return False

        # The page only reflects the new state after a reload, and the server
        # needs a few seconds to register the step: reload until the step that
        # was done is no longer offered.
        after = page

        def stepDone(_) -> bool:
            nonlocal after
            after = self._loadQuest(offerId)
            return not any(
                s.offer_id == step.offer_id and s.is_actionable for s in after.steps
            )

        try:
            WebDriverWait(
                self.webdriver, VERIFY_TIMEOUT, poll_frequency=VERIFY_POLL
            ).until(stepDone)
        except TimeoutException:
            logging.warning(
                "[QUESTS] %s: step %s is still open %d s after the click",
                offerId, step.offer_id, VERIFY_TIMEOUT,
            )
            return True
        logging.info(
            "[QUESTS] %s: step done (%s -> %s)",
            offerId, page.progress or "?", after.progress or "?",
        )
        return True

    def completeQuests(self) -> None:
        """
        Never raises: this is an extra source of points and must not prevent
        the rest of the run (the searches) from happening.
        """
        logging.info("[QUESTS] Trying to complete the quests...")
        try:
            offerIds = self._questOfferIds()
            if not offerIds:
                logging.info("[QUESTS] No quest to do.")
                return

            for offerId in offerIds:
                # Only an actual click is spaced out, not a quest with nothing to do.
                if self._completeQuest(offerId):
                    cooldown()
        except Exception:
            logging.exception("[QUESTS] Failed to complete the quests")
            return
        logging.info("[QUESTS] Done")
