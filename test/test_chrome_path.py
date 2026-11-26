import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from src.browser import Browser
from src.utils import (
    DEFAULT_CONFIG,
    Config,
    argumentParser,
    commandLineArgumentsAsConfig,
)


class StopSetup(Exception):
    pass


class TestChromePathConfiguration(TestCase):
    def test_no_chrome_path_by_default(self):
        self.assertIsNone(DEFAULT_CONFIG.browser.get("chrome-path"))

    def test_cli_option_sets_the_chrome_path_and_keeps_the_other_defaults(self):
        with patch("sys.argv", ["main.py", "--chrome-path", "C:/chrome/chrome.exe"]):
            config = DEFAULT_CONFIG | commandLineArgumentsAsConfig(argumentParser())

        self.assertEqual(config.browser["chrome-path"], "C:/chrome/chrome.exe")
        self.assertFalse(config.browser.visible)

    def test_cli_option_is_not_set_when_not_given(self):
        with patch("sys.argv", ["main.py", "--visible"]):
            config = commandLineArgumentsAsConfig(argumentParser())

        self.assertNotIn("chrome-path", config.browser)


class TestChromePathUse(TestCase):
    def configured(self, value):
        return patch("src.browser.CONFIG", Config({"browser": {"chrome-path": value}}))

    def test_nothing_is_configured(self):
        with self.configured(None):
            self.assertIsNone(Browser.configuredChromePath())

    def test_an_existing_file_is_returned(self):
        with tempfile.TemporaryDirectory() as folder:
            chrome = Path(folder) / "chrome.exe"
            chrome.write_text("")
            with self.configured(str(chrome)):
                self.assertEqual(Browser.configuredChromePath(), str(chrome))

    def test_a_missing_file_is_reported_with_the_setting_name(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.configured(str(Path(folder) / "nope.exe")):
                with self.assertRaisesRegex(FileNotFoundError, "browser.chrome-path"):
                    Browser.configuredChromePath()

    def test_the_version_is_read_from_the_configured_chrome(self):
        with patch("src.browser.WebDriver") as webdriver:
            webdriver.return_value.capabilities = {"browserVersion": "158.0.1.2"}

            self.assertEqual(Browser.getChromeVersion("D:/chrome/chrome.exe"), "158.0.1.2")

        options = webdriver.call_args.kwargs["options"]
        self.assertEqual(options.binary_location, "D:/chrome/chrome.exe")

    def test_the_version_check_uses_the_default_chrome_when_none_is_configured(self):
        with patch("src.browser.WebDriver") as webdriver:
            webdriver.return_value.capabilities = {"browserVersion": "158.0.1.2"}

            Browser.getChromeVersion()

        self.assertEqual(webdriver.call_args.kwargs["options"].binary_location, "")

    def launch(self, chromePath):
        browser = Browser.__new__(Browser)
        browser.headless = True
        browser.localeLang = "en-US"
        browser.proxy = None
        browser.userDataDir = Path("sessions/test")
        browser.chromePath = chromePath
        with patch("src.browser.os.path.exists", return_value=False), \
                patch.object(Browser, "getChromeVersion", return_value="158.0.1.2") as version, \
                patch("src.browser.webdriver.Chrome", side_effect=StopSetup) as chrome:
            with self.assertRaises(StopSetup):
                browser.browserSetup()
        return version, chrome

    def test_the_driver_is_started_with_the_configured_chrome(self):
        version, chrome = self.launch("D:/chrome/chrome.exe")

        version.assert_called_once_with("D:/chrome/chrome.exe")
        self.assertEqual(
            chrome.call_args.kwargs["browser_executable_path"], "D:/chrome/chrome.exe"
        )
        self.assertEqual(chrome.call_args.kwargs["version_main"], 158)

    def test_the_driver_looks_for_chrome_by_itself_when_none_is_configured(self):
        version, chrome = self.launch(None)

        version.assert_called_once_with(None)
        self.assertNotIn("browser_executable_path", chrome.call_args.kwargs)
