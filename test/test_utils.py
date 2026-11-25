from unittest import TestCase
from unittest.mock import MagicMock, call, patch

# noinspection PyPackageRequirements
from parameterized import parameterized
from requests import Response

from src.utils import (
    BING_HOME_URL,
    BING_REWARDS_FLYOUT_URL,
    CONFIG,
    APPRISE,
    DEFAULT_CONFIG,
    Utils,
    argumentParser,
    commandLineArgumentsAsConfig,
    isValidCountryCode,
    isValidLanguageCode,
)


class TestUtils(TestCase):
    def test_default_channels_enable_desktop_and_mobile(self):
        self.assertTrue(DEFAULT_CONFIG.channel.desktop.enabled)
        self.assertTrue(DEFAULT_CONFIG.channel.mobile.enabled)

    def test_cli_channel_flags_override_configuration(self):
        with patch(
            "sys.argv",
            ["main.py", "--no-desktop-channel", "--mobile-channel"],
        ):
            config = commandLineArgumentsAsConfig(argumentParser())

        self.assertFalse(config.channel.desktop.enabled)
        self.assertTrue(config.channel.mobile.enabled)

    def test_bing_auth_opens_flyout_directly_before_selector_fallback(self):
        webdriver = MagicMock()
        utils = Utils(webdriver)

        with (
            patch.object(utils, "_isBingRewardsAuthenticated", side_effect=[False, True]),
            patch.object(utils, "_clickGetStartedIfPresent") as click_get_started,
            patch.object(utils, "_findFirstVisible") as find_pill,
        ):
            utils.ensureBingSearchAuth()

        self.assertEqual(
            webdriver.get.call_args_list,
            [
                call(BING_HOME_URL),
                call(BING_REWARDS_FLYOUT_URL),
                call(BING_HOME_URL),
            ],
        )
        click_get_started.assert_called_once()
        find_pill.assert_not_called()

    def test_bing_auth_falls_back_to_rewards_header_control(self):
        webdriver = MagicMock()
        pill = MagicMock()
        utils = Utils(webdriver)
        action_chain = MagicMock()

        with (
            patch.object(
                utils, "_isBingRewardsAuthenticated", side_effect=[False, False, True]
            ),
            patch.object(utils, "_clickGetStartedIfPresent") as click_get_started,
            patch.object(utils, "_findFirstVisible", return_value=pill),
            patch("src.utils.ActionChains", return_value=action_chain),
        ):
            utils.ensureBingSearchAuth()

        self.assertEqual(
            webdriver.get.call_args_list,
            [
                call(BING_HOME_URL),
                call(BING_REWARDS_FLYOUT_URL),
                call(BING_HOME_URL),
                call(BING_HOME_URL),
            ],
        )
        self.assertEqual(click_get_started.call_count, 2)
        action_chain.move_to_element.assert_called_once_with(pill)

    def test_bing_rewards_info_decodes_goal_title_as_utf8(self):
        response = Response()
        response.status_code = 200
        response.encoding = "ISO-8859-1"
        response._content = (
            b'{"flyoutResult":{"userGoal":{"title":"M\xc3\xbcnchen"}}}'
        )
        session = MagicMock()
        session.get.return_value = response
        webdriver = MagicMock()
        webdriver.get_cookies.return_value = []

        with patch("src.utils.makeRequestsSession", return_value=session):
            info = Utils(webdriver).getBingRewardsInfo()

        self.assertEqual(info["flyoutResult"]["userGoal"]["title"], "München")

    def test_send_notification(self):
        CONFIG.apprise.enabled = True
        APPRISE.notify("body", "title")

    @parameterized.expand(
        [
            ("US", True),
            ("US-GA", True),
            ("XX", False),
            ("US-XX", False),
        ]
    )
    def test_isValidCountryCode(self, code, expected):
        self.assertEqual(isValidCountryCode(code), expected)

    @parameterized.expand(
        [
            ("en", True),
            ("en-US", True),
            ("xx", False),
            ("en-XX", False),
        ]
    )
    def test_isValidLanguageCode(self, code, expected):
        self.assertEqual(isValidLanguageCode(code), expected)

    def test_load_localized_activities_with_valid_language(self):
        from src.utils import load_localized_activities

        localized_activities = load_localized_activities("en")
        self.assertTrue(
            localized_activities.title_to_query,
            "localized_activities.title_to_query should not be empty",
        )
        self.assertTrue(
            localized_activities.ignore,
            "localized_activities.ignore should not be empty",
        )

    def test_load_localized_activities_with_invalid_language(self):
        from src.utils import load_localized_activities

        # An unknown language falls back to English rather than raising, so no
        # account is skipped just because its locale has no query file.
        fallback = load_localized_activities("foo")
        english = load_localized_activities("en")
        self.assertEqual(fallback.title_to_query, english.title_to_query)
        self.assertEqual(fallback.ignore, english.ignore)
