from unittest import TestCase
from unittest.mock import MagicMock, patch

# noinspection PyPackageRequirements
from parameterized import parameterized
from requests import Response

from src.utils import (
    CONFIG,
    APPRISE,
    Utils,
    isValidCountryCode,
    isValidLanguageCode,
)


class TestUtils(TestCase):
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
