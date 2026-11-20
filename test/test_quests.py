import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from selenium.common import TimeoutException

from src.quests import Quests
from src.rsc import QuestStep, parse_quest_cards, parse_quest_page

MONTHLY = "ENWW_pcparent_FY27_BingMonthlyPC_Nov_punchcard"
SPOTIFY = "WW_evergreen_pcparent_Spotify_punchcard"
REWARDS_APP = "WW_pcparent_RewardsApp_weekly_Exclusive_Novw3_2026_punchcard"


def html(rscText: str) -> str:
    return f"<html><script>self.__next_f.push([1,{json.dumps(rscText)}])</script></html>"


def step(n: int, completed=False, locked=False) -> dict:
    return {
        "ariaLabel": f"Do it {n}, Step {n}",
        "hash": "abc",
        "href": f"https://www.bing.com/search?q=step{n}",
        "edgeAction": "$undefined",
        "isCompleted": completed,
        "isLocked": locked,
        "linkText": f"Do it {n}",
        "offerId": f"ENWW_pcchild{n}_urlreward_FY27_BingMonthlyPC_Nov_punchcard",
    }


def questPage(steps: list[dict], progress="0/5 tasks") -> str:
    return html(
        '["$","p",null,{"children":"%s"}]\n%s'
        % (progress, "\n".join(f'["$","$L65",null,{json.dumps(s)}]' for s in steps))
    )


class TestQuestParsing(TestCase):
    def test_quest_cards_are_listed_in_page_order_without_duplicates(self):
        rsc = "".join(
            f'["$","$L2b","{i}",{{"href":"/earn/quest/{o}","instrument":{{"data":{{"offerId":"{o}"}}}}}}]'
            for i, o in enumerate([SPOTIFY, REWARDS_APP, MONTHLY, MONTHLY])
        )
        self.assertEqual(
            parse_quest_cards(html(rsc)), [SPOTIFY, REWARDS_APP, MONTHLY]
        )

    def test_page_without_quests_gives_no_card(self):
        self.assertEqual(parse_quest_cards(html('{"href":"/earn/other"}')), [])

    def test_only_the_first_step_is_actionable_while_the_others_are_locked(self):
        page = parse_quest_page(
            questPage([step(1)] + [step(n, locked=True) for n in range(2, 6)])
        )

        self.assertEqual(len(page.steps), 5)
        self.assertEqual(page.progress, "0/5 tasks")
        self.assertEqual(page.next_step().offer_id, page.steps[0].offer_id)

    def test_no_step_is_offered_when_all_the_remaining_ones_are_locked(self):
        page = parse_quest_page(
            questPage([step(n, locked=True) for n in range(2, 6)], "1/5 tasks")
        )

        self.assertIsNone(page.next_step())
        self.assertEqual(page.progress, "1/5 tasks")

    def test_completed_and_locked_steps_are_skipped(self):
        page = parse_quest_page(
            questPage([step(1, completed=True), step(2), step(3, locked=True)])
        )

        self.assertEqual(page.next_step().aria_label, "Do it 2, Step 2")

    def test_rsc_undefined_flags_are_not_truthy(self):
        raw = step(1)
        raw["isCompleted"] = "$undefined"
        raw["isLocked"] = "$undefined"

        self.assertTrue(QuestStep.from_rsc(raw).is_actionable)

    def test_page_without_steps_is_empty(self):
        page = parse_quest_page(html('["$","p",null,{"children":"hello"}]'))

        self.assertEqual(page.steps, [])
        self.assertIsNone(page.next_step())
        self.assertEqual(page.progress, "")


class TestQuests(TestCase):
    def setUp(self):
        self.browser = MagicMock()
        self.driver = self.browser.webdriver
        self.driver.current_url = "https://rewards.bing.com/earn"
        self.driver.window_handles = ["main"]
        self.driver.current_window_handle = "main"
        patcher = patch("src.quests.cooldown")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.quests = Quests(self.browser)

    def earnCards(self, *offerIds: str) -> str:
        return html(
            "".join(f'{{"href":"/earn/quest/{o}"}}' for o in offerIds)
        )

    def test_spotify_and_rewards_app_quests_are_ignored(self):
        self.driver.page_source = self.earnCards(SPOTIFY, REWARDS_APP, MONTHLY)

        self.assertEqual(self.quests._questOfferIds(), [MONTHLY])
        self.browser.utils.goToEarn.assert_called_once()

    def test_a_new_monthly_quest_is_picked_up_without_knowing_its_title(self):
        december = "ENWW_pcparent_FY27_BingMonthlyPC_Dec_punchcard"
        self.driver.page_source = self.earnCards(SPOTIFY, REWARDS_APP, december)

        self.assertEqual(self.quests._questOfferIds(), [december])

    def test_nothing_is_done_when_there_is_no_quest(self):
        self.driver.page_source = self.earnCards(SPOTIFY, REWARDS_APP)

        self.quests.completeQuests()

        self.driver.get.assert_not_called()

    def test_an_error_does_not_propagate_so_the_run_can_go_on(self):
        self.driver.page_source = self.earnCards(MONTHLY)
        with patch.object(Quests, "_loadQuest", side_effect=RuntimeError("boom")), \
                self.assertLogs(level="ERROR") as logs:
            self.quests.completeQuests()

        self.assertTrue(any("Failed to complete the quests" in m for m in logs.output))

    def test_nothing_is_clicked_when_the_next_step_is_locked(self):
        self.driver.page_source = self.earnCards(MONTHLY)
        with patch.object(
            Quests, "_loadQuest", return_value=parse_quest_page(
                questPage([step(2, locked=True)], "1/5 tasks")
            ),
        ), patch.object(Quests, "_clickStep") as click:
            self.quests.completeQuests()

        click.assert_not_called()

    def test_a_step_is_clicked_and_verified_with_a_reload(self):
        self.driver.page_source = self.earnCards(MONTHLY)
        before = parse_quest_page(questPage([step(1)] + [step(n, locked=True) for n in range(2, 6)]))
        after = parse_quest_page(questPage([step(n, locked=True) for n in range(2, 6)], "1/5 tasks"))
        with patch.object(Quests, "_loadQuest", side_effect=[before, after]) as load, \
                patch.object(Quests, "_clickStep", return_value=True) as click, \
                self.assertLogs(level="INFO") as logs:
            self.quests.completeQuests()

        click.assert_called_once_with(before.steps[0])
        self.assertEqual(load.call_count, 2)
        self.assertTrue(any("step done (0/5 tasks -> 1/5 tasks)" in m for m in logs.output))

    def test_the_state_is_polled_until_the_server_registers_the_step(self):
        self.driver.page_source = self.earnCards(MONTHLY)
        before = parse_quest_page(questPage([step(1)] + [step(n, locked=True) for n in range(2, 6)]))
        after = parse_quest_page(questPage([step(n, locked=True) for n in range(2, 6)], "1/5 tasks"))
        # the first reloads still show the step as open (not registered yet)
        with patch("src.quests.VERIFY_TIMEOUT", 5), patch("src.quests.VERIFY_POLL", 0.01), \
                patch.object(Quests, "_loadQuest", side_effect=[before, before, before, after]) as load, \
                patch.object(Quests, "_clickStep", return_value=True), \
                self.assertLogs(level="INFO") as logs:
            self.quests.completeQuests()

        self.assertEqual(load.call_count, 4)
        self.assertTrue(any("step done (0/5 tasks -> 1/5 tasks)" in m for m in logs.output))
        self.assertFalse(any("still open" in m for m in logs.output))

    def test_a_step_that_stays_open_after_the_click_is_reported(self):
        self.driver.page_source = self.earnCards(MONTHLY)
        page = parse_quest_page(questPage([step(1)]))
        with patch("src.quests.VERIFY_TIMEOUT", 0.2), patch("src.quests.VERIFY_POLL", 0.05), \
                patch.object(Quests, "_loadQuest", return_value=page), \
                patch.object(Quests, "_clickStep", return_value=True), \
                self.assertLogs(level="WARNING") as logs:
            self.quests.completeQuests()

        self.assertTrue(any("still open" in m and "after the click" in m for m in logs.output))

    def test_no_reload_happens_when_the_click_did_not_work(self):
        self.driver.page_source = self.earnCards(MONTHLY)
        page = parse_quest_page(questPage([step(1)]))
        with patch.object(Quests, "_loadQuest", return_value=page) as load, \
                patch.object(Quests, "_clickStep", return_value=False):
            self.quests.completeQuests()

        load.assert_called_once()

    def test_click_with_a_real_pointer_then_the_opened_page_is_closed(self):
        target = parse_quest_page(questPage([step(1)])).steps[0]
        anchor = MagicMock()
        anchor.get_attribute.return_value = target.aria_label
        other = MagicMock()
        other.get_attribute.return_value = "something else"
        self.driver.find_elements.return_value = [other, anchor]
        self.driver.window_handles = ["main", "popup"]
        self.driver.execute_script.return_value = "complete"

        with patch("src.quests.ActionChains") as actions, \
                patch("src.quests.WebDriverWait") as wait:
            wait.return_value.until.return_value = True
            self.assertTrue(self.quests._clickStep(target))

        actions.return_value.move_to_element.assert_called_once_with(anchor)
        actions.return_value.move_to_element.return_value.click.return_value.perform.assert_called_once()
        self.driver.close.assert_called_once()
        self.driver.switch_to.window.assert_called_with("main")

    def test_click_reports_failure_when_no_page_is_opened(self):
        target = parse_quest_page(questPage([step(1)])).steps[0]
        anchor = MagicMock()
        anchor.get_attribute.return_value = target.aria_label
        self.driver.find_elements.return_value = [anchor]

        waits = [True, TimeoutException()]

        def until(_condition):
            result = waits.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with patch("src.quests.ActionChains"), patch("src.quests.WebDriverWait") as wait:
            wait.return_value.until.side_effect = until
            self.assertFalse(self.quests._clickStep(target))

        self.driver.close.assert_not_called()

    def test_click_reports_failure_when_the_button_is_missing(self):
        target = parse_quest_page(questPage([step(1)])).steps[0]
        self.driver.find_elements.return_value = []

        with patch("src.quests.WebDriverWait") as wait:
            wait.return_value.until.side_effect = TimeoutException()
            self.assertFalse(self.quests._clickStep(target))
