import os
import random
from pathlib import Path

import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException
from spotbot.utils.dbhelper import MongoDBHelper


class GenerateFootprint:
    """
    This class is used to create a random set of cookie footprints to not get detected by Spotify
    """
    def __init__(self, amount_of_cookies_to_gen, email, driver=None, close_driver_afterward=False):
        if driver is not None:
            self.driver = driver
        else:
            self.driver = self._setup_driver(email=email)

        self.amount_of_cookies_to_gen = amount_of_cookies_to_gen
        self.email = email
        self.close_driver_afterward = close_driver_afterward

    @staticmethod
    def _setup_driver(email):
        options = uc.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)

        chrome_profiles_dir = fr'\data\chrome_profiles\{email}'
        options.add_argument(f"user-data-dir={str(Path(__file__).parents[2]) + chrome_profiles_dir}")

        return uc.Chrome(executable_path="../../driver/chromedriver/chromedriver_89.exe", options=options)

    def generate_footprint(self):
        """
        This function will navigate to random websites to accept cookies on and will safe these cookies in dictionaries
        which then get stored inside a list
        :return: None
        """
        cookie_websites = MongoDBHelper().configurations.find_one()["cookies_websites"]
        cookies = []

        websites = random.sample(cookie_websites, self.amount_of_cookies_to_gen)

        print(f"[#] Cookies > Now spoofing a total of {self.amount_of_cookies_to_gen} cookies for the account > {self.email}")

        for index, website in enumerate(websites):
            print(f"[#] Cookies [{index + 1}/{self.amount_of_cookies_to_gen}] > Spoofing cookies on {website} for the account > {self.email}")
            try:
                self.driver.get(website)
            except WebDriverException:
                pass
            cookies.append(self.driver.get_cookies())

        print(f"[#] Cookies > Spoofed a total of {len(cookies)} cookies for the account > {self.email}")

        if self.close_driver_afterward:
            self.driver.quit()


if __name__ == "__main__":
    i = GenerateFootprint(10, "l.wiederhold@gmx.net")
    i.generate_footprint()
