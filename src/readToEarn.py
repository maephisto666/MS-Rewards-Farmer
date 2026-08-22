import logging
import random
import secrets
import time

from requests_oauthlib import OAuth2Session
from selenium.webdriver.common.by import By

from src.browser import Browser
from .activities import Activities
from .utils import makeRequestsSession, cooldown

# todo Use constant naming style
client_id = "0000000040170455"
authorization_base_url = "https://login.live.com/oauth20_authorize.srf"
token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
redirect_uri = " https://login.live.com/oauth20_desktop.srf"
scope = ["service::prod.rewardsplatform.microsoft.com::MBI_SSL"]


class ReadToEarn:
    """
    Class to handle Read to Earn in MS Rewards.
    """

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver
        self.activities = Activities(browser)

    def completeReadToEarn(self):

        logging.info("[READ TO EARN] " + "Trying to complete Read to Earn...")

        accountName = self.browser.email
        mobileApp = makeRequestsSession(
            OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
        )
        authorization_url = mobileApp.authorization_url(
            authorization_base_url, access_type="offline_access", login_hint=accountName
        )[0]

        # Get Referer URL from webdriver
        self.webdriver.get(authorization_url)
        count = 0
        while True:
            current_url = self.webdriver.current_url
            if current_url.startswith(
                "https://login.live.com/oauth20_desktop.srf?code="
            ):
                redirect_response = current_url
                break
            # A silent SSO redirect should reach the ?code= URL within a second
            # or two. Log where the flow is parked each poll so that, if it
            # stalls, we can see which interactive screen (passkey / "Stay
            # signed in?" / consent) is blocking the redirect.
            logging.info("[READ TO EARN] Waiting for Login (URL: %s)", current_url)
            time.sleep(1)
            count += 1
            if count >= 10:
                # Capture the blocking page state before giving up, so the
                # failure is diagnosable instead of a contextless exception.
                visible_buttons = []
                for b in self.webdriver.find_elements(By.XPATH, "//button | //*[@role='button']"):
                    try:
                        if b.is_displayed():
                            visible_buttons.append(
                                (b.text or "").strip()
                                or b.get_attribute("id")
                                or b.get_attribute("data-testid")
                            )
                    except Exception:
                        continue
                logging.error(
                    "[READ TO EARN] Stuck waiting for OAuth redirect. "
                    "URL: %s | Title: %s | visible buttons: %s",
                    self.webdriver.current_url, self.webdriver.title, visible_buttons,
                )
                raise Exception("Stuck in waiting for login")

        logging.info("[READ TO EARN] Logged-in successfully !")
        token = mobileApp.fetch_token(
            token_url, authorization_response=redirect_response, include_client_id=True
        )
        # Do Daily Check in
        json_data = {
            "amount": 1,
            "country": self.browser.localeGeo.lower(),
            "id": secrets.token_hex(64),
            "type": 101,
            "attributes": {
                "offerid": "Gamification_Sapphire_DailyCheckIn",
            },
        }
        logging.info("[READ TO EARN] Daily App Check In")
        r = mobileApp.post(
            "https://prod.rewardsplatform.microsoft.com/dapi/me/activities",
            json=json_data,
        )
        balance = r.json().get("response").get("balance")
        time.sleep(random.randint(10, 20))

        # json data to confirm an article is read
        json_data = {
            "amount": 1,
            "country": self.browser.localeGeo.lower(),
            "id": 1,
            "type": 101,
            "attributes": {
                "offerid": "ENUS_readarticle3_30points",
            },
        }

        # 10 is the most articles you can read. Sleep time is a guess, not tuned
        for i in range(10):
            # Replace ID with a random value so get credit for a new article
            json_data["id"] = secrets.token_hex(64)
            r = mobileApp.post(
                "https://prod.rewardsplatform.microsoft.com/dapi/me/activities",
                json=json_data,
            )
            newbalance = r.json().get("response").get("balance")

            if newbalance == balance:
                logging.info("[READ TO EARN] Read All Available Articles !")
                break

            logging.info("[READ TO EARN] Read Article " + str(i + 1))
            balance = newbalance
            cooldown()

        logging.info("[READ TO EARN] Completed the Read to Earn successfully !")
