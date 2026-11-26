from unittest import TestCase
from unittest.mock import MagicMock

from src.browser import Browser
from src.constants import REWARDS_APP_USER_AGENT_MARKER

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/158.0.0.0 Edg/158.0.0.0"
METADATA = {"platform": "Windows", "mobile": False}


class TestRewardsAppIdentity(TestCase):
    def setUp(self):
        self.browser = Browser.__new__(Browser)
        self.browser.webdriver = MagicMock()
        self.browser.userAgent = USER_AGENT
        self.browser.userAgentMetadata = METADATA
        self.cdp = self.browser.webdriver.execute_cdp_cmd

    def overrides(self) -> list[dict]:
        for call in self.cdp.call_args_list:
            self.assertEqual(call.args[0], "Emulation.setUserAgentOverride")
        return [call.args[1] for call in self.cdp.call_args_list]

    def test_the_regular_override_is_the_user_agent_alone(self):
        self.assertEqual(
            self.browser.userAgentOverride(),
            {"userAgent": USER_AGENT, "platform": "Windows", "userAgentMetadata": METADATA},
        )

    def test_the_app_token_is_appended_inside_the_block_only(self):
        with self.browser.rewardsAppIdentity():
            inside = self.overrides()
            self.assertEqual(len(inside), 1)
            self.assertEqual(
                inside[0]["userAgent"], f"{USER_AGENT} {REWARDS_APP_USER_AGENT_MARKER}"
            )
            self.assertEqual(inside[0]["userAgentMetadata"], METADATA)

        self.assertEqual(self.overrides()[-1], self.browser.userAgentOverride())
        self.assertEqual(len(self.overrides()), 2)

    def test_the_regular_user_agent_is_restored_when_the_block_fails(self):
        with self.assertRaises(RuntimeError):
            with self.browser.rewardsAppIdentity():
                raise RuntimeError("boom")

        self.assertEqual(self.overrides()[-1]["userAgent"], USER_AGENT)
