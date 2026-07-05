import logging
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from src.browser import Browser
from src.constants import REWARDS_URL
from src.rsc import DailySetItem
from src.utils import (
    CONFIG,
    APPRISE,
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

        # Retry once: if the anchor has no size on first load, reload the dashboard
        # and look for it again. The card click is required — direct URL navigation
        # does not award points.
        for attempt in range(1, 3):
            anchor = anchors[0]
            self.webdriver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", anchor
            )
            try:
                WebDriverWait(self.webdriver, 5).until(
                    lambda d: d.execute_script(
                        "var r=arguments[0].getBoundingClientRect();"
                        "return r.width>0 && r.height>0;",
                        anchor,
                    )
                )
                break  # anchor is rendered, proceed to click
            except TimeoutException:
                if attempt < 2:
                    logging.info(
                        "[ACTIVITY] Anchor not rendered for '%s', reloading dashboard (attempt %d)",
                        cleanupActivityTitle(item.title), attempt,
                    )
                    self.browser.utils.goToRewards()
                    anchors = self.webdriver.find_elements(
                        By.XPATH, f"//a[contains(@href, '{token}')]"
                    )
                    if not anchors:
                        logging.warning(
                            "[ACTIVITY] Anchor for '%s' disappeared after reload",
                            cleanupActivityTitle(item.title),
                        )
                        return False
                else:
                    logging.warning(
                        "[ACTIVITY] Anchor for '%s' still has no size after reload — skipping",
                        cleanupActivityTitle(item.title),
                    )
                    return False

        self.webdriver.execute_script("arguments[0].click();", anchor)
        logging.info(
            "[ACTIVITY] [%s] Clicked '%s'",
            item.activity_type, cleanupActivityTitle(item.title),
        )
        # Wait for the destination tab to open and finish loading, then close it.
        # Points are registered server-side on page load; we just need to let it complete.
        try:
            WebDriverWait(self.webdriver, 12).until(
                lambda d: len(d.window_handles) > 1
            )
            self.webdriver.switch_to.window(self.webdriver.window_handles[-1])
            WebDriverWait(self.webdriver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            self.webdriver.switch_to.window(self.webdriver.window_handles[0])
        except TimeoutException:
            pass  # no new tab opened (same-tab redirect or instant credit)
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
            if not clicked:
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
