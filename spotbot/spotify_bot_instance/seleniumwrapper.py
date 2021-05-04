import random
import time

from selenium.common.exceptions import MoveTargetOutOfBoundsException, TimeoutException, StaleElementReferenceException, WebDriverException
from selenium.webdriver import ActionChains, TouchActions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Randomizer import is_random


class ModifiedActionChain:
    def __init__(self, driver, mobile):
        self.driver = driver
        self.mobile = mobile
        self.action = ActionChains(self.driver)

    def click(self, element, click_delay=random.randint(0, 3)):
        try:
            self.action.move_to_element(element).perform()
        except StaleElementReferenceException:
            pass

        time.sleep(random.randint(1, 2))

        try:
            if self.mobile:
                touch_action = TouchActions(self.driver)
                time.sleep(click_delay)
                touch_action.tap(element).perform()
            else:
                time.sleep(click_delay)
                element.click()
        except WebDriverException:
            return False

        return True

    def double_click(self, element):
        if self.mobile:
            self.action.double_click(element)
            self.action.perform()
        else:
            touch_action = TouchActions(self.driver)
            touch_action.double_tap(element)
            touch_action.perform()

        return True

    def right_click(self, element):
        self.action.context_click(element)
        self.action.perform()

    def click_amd_hold(self, element):
        if self.mobile:
            touch_action = TouchActions(self.driver)
            touch_action.long_press(element)
            touch_action.perform()
        else:
            self.action.click_and_hold(element)
            self.action.perform()

    def move_with_offset(self, x_coord, y_coord):
        if self.mobile:
            touch_action = TouchActions(self.driver)
            touch_action.move(x_coord, y_coord)
            touch_action.perform()
        else:
            self.action.move_by_offset(x_coord, y_coord)
            self.action.perform()

    def move_to_element_with_offset(self, element, x, y):
        try:
            self.action.move_to_element_with_offset(element, x, y)
            self.action.perform()
            return True
        except MoveTargetOutOfBoundsException:
            return False


class SeleniumHelper(ModifiedActionChain):
    """methods to improve selenium experience and humanize movements"""

    def __init__(self, driver, mobile):
        super().__init__(driver, mobile)
        self.driver = driver
        self.mobile = mobile

    def _clear_input_field(self, element):
        super().click(element=element)

        if is_random(random.randint(30, 80)):
            element.send_keys(Keys.CONTROL, "a")
            time.sleep(random.randint(1, 3))
            element.send_keys(Keys.BACKSPACE)
        else:
            for x in range(len(element.get_attribute("value"))):
                time.sleep(random.random())
                element.send_keys(Keys.BACKSPACE)

        return True

    def legit_typing(self, element, text: str, clear_input_field: bool) -> bool:
        """
        Uses the .send_keys() in a sequence with random wait between each tick to make the typing look legit.
        ----------------------------------------------------------------------------------------------------------------
        :chances:
            - [4-6%] type a wrong letter and replace it with the right one after x seconds
            - [2-4%] after each character entered take a break longer than 1s (1-3s)
            - [1%] after each character entered take a break for longer than 3s (3-5s)
        ----------------------------------------------------------------------------------------------------------------
        :param clear_input_field: whether to clear the input field or not
        :param element: webdriver element to send the keys to
        :param text: string which contains the text to send to the element
        :return: True or False whether the action was performed successfully
        """
        super().click(element=element)

        if clear_input_field:
            if element.get_attribute("value"):
                self._clear_input_field(element=element)
        for char in text:
            if is_random(random.randint(2, 4)):
                time.sleep(random.randint(1, 3))
            elif is_random(random.randint(1, 2)):
                time.sleep(random.randint(3, 5))
            elif is_random(random.randint(4, 6)):
                element.send_keys(random.choice(list(text)))
                time.sleep(random.randint(1, 3))
                element.send_keys(Keys.BACKSPACE)
                time.sleep(random.randint(1, 4))
            time.sleep(random.random())
            element.send_keys(char)
        return True

    def random_scrolling(self, *args):
        """
        Scrolls legit to the given elements.
        ----------------------------------------------------------------------------------------------------------------
        :chances:
            - [3 - 6%] sleep 1 - 4 seconds longer
            - [3 - 6%] perfrom a click on the element
        ----------------------------------------------------------------------------------------------------------------
        :param args: n amount of element to scroll to
        :return: True or False whether the action was performed successfully
        """

        for element in args:
            if is_random(random.randint(3, 6)):
                time.sleep(random.randint(1, 4))

            self.driver.execute_script("arguments[0].scrollIntoView();", element)

            time.sleep(random.randint(1, 4))
            if is_random(random.randint(3, 6)):
                if is_random(random.randint(7, 15)):
                    super(SeleniumHelper, self).double_click(element=element)
                elif is_random(random.randint(6, 12)):
                    super(SeleniumHelper, self).right_click(element=element)
                else:
                    super(SeleniumHelper, self).click(element=element)

    def find_element_by_xpath(self, xpath, timeout=8, multiple_elements=False):
        """
        Wrapper for the selenium driver.find_element_by_xpath() method to remove boilerplate code.
        :param xpath: Xpath to the desired element
        :param timeout: Max seconds of how long it is allowed to find the element
        :param multiple_elements: select multiple elements
        :return: if the element wasn't found it will return None else the WebDriver element
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
        except TimeoutException:
            return

        if multiple_elements:
            return self.driver.find_elements_by_xpath(xpath)

        return element

    def navigate_to_weplayer_from_overview_page(self):
        """
        This method doesn't really fit into this class but is used to navigate to the webplayer from the accounts
        overview page.
        :return: bool. This determines wether it had to perform the action or had nothing to change because it was
        already on the webplayer.
        """
        if "/account/overview/" in self.driver.current_url:
            spotify_logo_to_click = self.find_element_by_xpath("//a[@class='mh-header-primary svelte-18o1xvt']")
            super().click(element=spotify_logo_to_click)

            time.sleep(random.randint(1, 3))

            open_webplayer_btn = self.find_element_by_xpath("//a[@class='btn btn-stroked-dark']")
            super().click(element=open_webplayer_btn)
            return True
        return False

    def navigate_to_explore_page(self):
        try:
            explore_btn = self.find_element_by_xpath("//a[@href='/search']")
            self.click(element=explore_btn)
            return True
        except WebDriverException:
            return False


if __name__ == '__main__':
    pass
