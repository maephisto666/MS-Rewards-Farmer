import unittest
from unittest.mock import patch, MagicMock

import main


class TestMain(unittest.TestCase):

    # noinspection PyUnusedLocal
    @patch.object(main, "save_previous_points_data")
    @patch.object(main, "setupLogging")
    @patch.object(main, "setupAccounts")
    @patch.object(main, "executeBot")
    # @patch.object(Utils, "send_notification")
    def test_send_notification_when_exception(
        self,
        # mock_send_notification: MagicMock,
        mock_executeBot: MagicMock,
        mock_setupAccounts: MagicMock,
        mock_setupLogging: MagicMock,
        mock_save_previous_points_data: MagicMock,
    ):
        mock_setupAccounts.return_value = [{"password": "foo", "username": "bar"}]
        mock_executeBot.side_effect = Exception

        main.main()

        # mock_send_notification.assert_called()


if __name__ == "__main__":
    unittest.main()
