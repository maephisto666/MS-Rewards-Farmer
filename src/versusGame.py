import logging
import time

from src.browser import Browser


class VersusGame:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver

    def completeVersusGame(self):
        try:
            i = 0
            self.webdriver.get(
                "https://www.bing.com/?form=ML2NF7&rwgbopen=1&rwgbscenario=versus&thirdPartyPartnerId=VersusGame"
            )
            time.sleep(10)
            flyout = self.webdriver.execute_script(
                'return document.querySelector("#panelFlyout")'
            )
            print(flyout)
            while flyout is None:
                flyout = self.webdriver.execute_script(
                    'return document.querySelector("#panelFlyout")'
                )
                print(f"looping flyout {flyout}")
                time.sleep(10)
                i += 1
                if i == 5:
                    logging.info("[VERSUS GAME] Versus Game Failed!")
                    return
            i = 0
            time.sleep(10)
            panelFlyoutLink = self.webdriver.execute_script(
                'return document.getElementById("panelFlyout").src'
            )
            self.webdriver.get(panelFlyoutLink)
            time.sleep(10)

            versusIframe = self.webdriver.execute_script(
                'return document.querySelector("#versusIframe")'
            )
            while versusIframe is None:
                versusIframe = self.webdriver.execute_script(
                    'return document.querySelector("#versusIframe")'
                )
                print(f"looping veruses iframe{versusIframe}")
                time.sleep(5)
                i += 1
                if i == 5:
                    logging.info("[VERSUS GAME] Versus Game Failed!")
                    return
            i = 0
            versusGameLink = self.webdriver.execute_script(
                'return document.querySelector("#versusIframe").src'
            )
            self.webdriver.get(versusGameLink)
            time.sleep(10)

            for _ in range(3):
                self.webdriver.execute_script(
                    "document.querySelectorAll('button')[1].click()"
                )
                time.sleep(10)
            logging.info("[VERSUS GAME] Completed Versus Game successfully!")
        except:
            logging.info("[VERSUS GAME] Versus Game Failed!")
            pass
