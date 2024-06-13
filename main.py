import argparse
import csv
import json
import logging
import logging.config
import logging.handlers as handlers
import random
import re
import sys
import time
from datetime import datetime
from enum import Enum, auto

from src import (
    Browser,
    Login,
    MorePromotions,
    PunchCards,
    Searches,
    DailySet,
    Account,
)
from src.loggingColoredFormatter import ColoredFormatter
from src.utils import Utils, RemainingSearches


def main():
    args = argumentParser()
    setupLogging()
    loadedAccounts = setupAccounts()

    # Load previous day's points data
    previous_points_data = load_previous_points_data()

    for currentAccount in loadedAccounts:
        try:
            earned_points = executeBot(currentAccount, args)
            previous_points = previous_points_data.get(currentAccount.username, 0)

            # Calculate the difference in points from the prior day
            points_difference = earned_points - previous_points

            # Append the daily points and points difference to CSV and Excel
            log_daily_points_to_csv(
                earned_points, points_difference
            )

            # Update the previous day's points data
            previous_points_data[currentAccount.username] = earned_points

            logging.info(
                f"[POINTS] Data for '{currentAccount.username}' appended to the file."
            )
        except Exception as e:
            Utils.sendNotification(
                "⚠️ Error occurred, please check the log", f"{e}\n{e.__traceback__}"
            )
            logging.exception(f"{e.__class__.__name__}: {e}")
            exit(1)

    # Save the current day's points data for the next day in the "logs" folder
    save_previous_points_data(previous_points_data)
    logging.info("[POINTS] Data saved for the next day.")


def log_daily_points_to_csv(earned_points, points_difference):
    logs_directory = Utils.getProjectRoot() / "logs"
    csv_filename = logs_directory / "points_data.csv"

    # Create a new row with the date, daily points, and points difference
    date = datetime.now().strftime("%Y-%m-%d")
    new_row = {
        "Date": date,
        "Earned Points": earned_points,
        "Points Difference": points_difference,
    }

    fieldnames = ["Date", "Earned Points", "Points Difference"]
    is_new_file = not csv_filename.exists()

    with open(csv_filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if is_new_file:
            writer.writeheader()

        writer.writerow(new_row)


def setupLogging():
    _format = "%(asctime)s [%(levelname)s] %(message)s"
    terminalHandler = logging.StreamHandler(sys.stdout)
    terminalHandler.setFormatter(ColoredFormatter(_format))

    logs_directory = Utils.getProjectRoot() / "logs"
    logs_directory.mkdir(parents=True, exist_ok=True)

    # so only our code is logged if level=logging.DEBUG or finer
    # if not working see https://stackoverflow.com/a/48891485/4164390
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": True,
        }
    )
    logging.basicConfig(
        level=logging.INFO,
        format=_format,
        handlers=[
            handlers.TimedRotatingFileHandler(
                logs_directory / "activity.log",
                when="midnight",
                interval=1,
                backupCount=2,
                encoding="utf-8",
            ),
            terminalHandler,
        ],
    )


def argumentParser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MS Rewards Farmer")
    parser.add_argument(
        "-v", "--visible", action="store_true", help="Optional: Visible browser"
    )
    parser.add_argument(
        "-l", "--lang", type=str, default=None, help="Optional: Language (ex: en)"
    )
    parser.add_argument(
        "-g", "--geo", type=str, default=None, help="Optional: Geolocation (ex: US)"
    )
    parser.add_argument(
        "-p",
        "--proxy",
        type=str,
        default=None,
        help="Optional: Global Proxy (ex: http://user:pass@host:port)",
    )
    parser.add_argument(
        "-vn",
        "--verbosenotifs",
        action="store_true",
        help="Optional: Send all the logs to the notification service",
    )
    parser.add_argument(
        "-cv",
        "--chromeversion",
        type=int,
        default=None,
        help="Optional: Set fixed Chrome version (ex. 118)",
    )
    return parser.parse_args()


def setupAccounts() -> list[Account]:
    """Sets up and validates a list of accounts loaded from 'accounts.json'."""

    def validEmail(email: str) -> bool:
        """Validate Email."""
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email))

    accountPath = Utils.getProjectRoot() / "accounts.json"
    if not accountPath.exists():
        accountPath.write_text(
            json.dumps(
                [{"username": "Your Email", "password": "Your Password"}], indent=4
            ),
            encoding="utf-8",
        )
        noAccountsNotice = """
    [ACCOUNT] Accounts credential file "accounts.json" not found.
    [ACCOUNT] A new file has been created, please edit with your credentials and save.
    """
        logging.warning(noAccountsNotice)
        exit(1)
    loadedAccounts: list[Account] = []
    for rawAccount in json.loads(accountPath.read_text(encoding="utf-8")):
        account: Account = Account(**rawAccount)
        if not validEmail(account.username):
            logging.warning(
                f"[CREDENTIALS] Invalid email: {account.username}, skipping this account"
            )
            continue
        loadedAccounts.append(account)
    random.shuffle(loadedAccounts)
    return loadedAccounts


class AppriseSummary(Enum):
    always = auto()
    on_error = auto()


def executeBot(currentAccount: Account, args: argparse.Namespace):
    logging.info(f"********************{currentAccount.username}********************")

    accountPointsCounter: int
    remainingSearches: RemainingSearches
    startingPoints: int

    with Browser(mobile=False, account=currentAccount, args=args) as desktopBrowser:
        utils = desktopBrowser.utils
        accountPointsCounter = Login(desktopBrowser).login()
        startingPoints = accountPointsCounter
        if startingPoints == "Locked":
            Utils.sendNotification("🚫 Account is Locked", currentAccount.username)
            return 0
        if startingPoints == "Verify":
            Utils.sendNotification(
                "❗️ Account needs to be verified", currentAccount.username
            )
            return 0
        logging.info(
            f"[POINTS] You have {utils.formatNumber(accountPointsCounter)} points on your account"
        )
        # todo - make quicker if done
        DailySet(desktopBrowser).completeDailySet()
        PunchCards(desktopBrowser).completePunchCards()
        MorePromotions(desktopBrowser).completeMorePromotions()
        # VersusGame(desktopBrowser).completeVersusGame()
        utils.goHome()
        remainingSearches = utils.getRemainingSearches()

        if remainingSearches.desktop != 0:
            accountPointsCounter = Searches(
                desktopBrowser, remainingSearches
            ).bingSearches(remainingSearches.desktop)

        utils.goHome()
        goalPoints = utils.getGoalPoints()
        goalTitle = utils.getGoalTitle()

    time.sleep(7.5)  # give time for browser to close, probably can be more fine-tuned

    if remainingSearches.mobile != 0:
        with Browser(mobile=True, account=currentAccount, args=args) as mobileBrowser:
            utils = mobileBrowser.utils
            Login(mobileBrowser).login()
            accountPointsCounter = Searches(
                mobileBrowser, remainingSearches
            ).bingSearches(remainingSearches.mobile)

            utils.goHome()
            goalPoints = utils.getGoalPoints()
            goalTitle = utils.getGoalTitle()

            remainingSearches = utils.getRemainingSearches()

    logging.info(
        f"[POINTS] You have earned {utils.formatNumber(accountPointsCounter - startingPoints)} points this run !"
    )
    logging.info(
        f"[POINTS] You are now at {utils.formatNumber(accountPointsCounter)} points !"
    )
    appriseSummary = AppriseSummary[utils.config.get("apprise", {}).get("summary", AppriseSummary.on_error.name)]
    if appriseSummary == AppriseSummary.always:
        goalNotifier = ""
        if goalPoints > 0:
            logging.info(
                f"[POINTS] You are now at {(utils.formatNumber((accountPointsCounter / goalPoints) * 100))}% of your "
                f"goal ({goalTitle}) !"
            )
            goalNotifier = (f"🎯 Goal reached: {(utils.formatNumber((accountPointsCounter / goalPoints) * 100))}%"
                            f" ({goalTitle})")

        Utils.sendNotification(
            "Daily Points Update",
            "\n".join(
                [
                    f"👤 Account: {currentAccount.username}",
                    f"⭐️ Points earned today: {utils.formatNumber(accountPointsCounter - startingPoints)}",
                    f"💰 Total points: {utils.formatNumber(accountPointsCounter)}",
                    goalNotifier,
                ]
            ),
        )
    elif appriseSummary == AppriseSummary.on_error:
        if remainingSearches.desktop > 0 or remainingSearches.mobile > 0:
            Utils.sendNotification(
                "Error: remaining searches",
                f"account username: {currentAccount.username}, {remainingSearches}",
            )

    return accountPointsCounter


def export_points_to_csv(points_data):
    logs_directory = Utils.getProjectRoot() / "logs"
    csv_filename = logs_directory / "points_data.csv"
    with open(csv_filename, mode="a", newline="") as file:  # Use "a" mode for append
        fieldnames = ["Account", "Earned Points", "Points Difference"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Check if the file is empty, and if so, write the header row
        if file.tell() == 0:
            writer.writeheader()

        for data in points_data:
            writer.writerow(data)


# Define a function to load the previous day's points data from a file in the "logs" folder
def load_previous_points_data():
    logs_directory = Utils.getProjectRoot() / "logs"
    try:
        with open(logs_directory / "previous_points_data.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


# Define a function to save the current day's points data for the next day in the "logs" folder
def save_previous_points_data(data):
    logs_directory = Utils.getProjectRoot() / "logs"
    with open(logs_directory / "previous_points_data.json", "w") as file:
        json.dump(data, file, indent=4)


if __name__ == "__main__":
    main()
