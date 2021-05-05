import math
import queue
import random
import sys
import time

import undetected_chromedriver
from CustomConsole import ConsolePage
from DBHelper import MongoDBHelper
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver import ActionChains, TouchActions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from spotbot.cookie_generator.cookie_gen import GenerateFootprint
from spotbot.spotify_bot_instance.seleniumwrapper import SeleniumHelper
from spotbot.spotify_bot_instance.signals.account_status import AccountStatus
from spotbot.spotify_bot_instance.signals.threadsignals import ThreadSignals
from spotbot.utils.randomizer import is_random


def requires_account_log_in(requires):
    """This decorator ensures that the current account is logged in"""

    def inner(method):
        def _inner(cls, *args, **kwargs):  # accepts **kwargs and *args to deal with methods that have parameters
            if len([cookie for cookie in cls.driver.get_cookies() if "accounts.spotify.com" == cookie["domain"]]) != 0:
                cls.log_in_status = AccountStatus.NOT_LOGGED_IN
            else:
                cls.log_in_status = AccountStatus.LOGGED_IN

            if cls.log_in_status == AccountStatus.NOT_LOGGED_IN or cls.log_in_status == AccountStatus.ACCOUNT_DETAILS_WRONG or cls.log_in_status == AccountStatus.PROXY_ERROR and requires:
                # logger.print_log(f"{Fore.RED}[-] Account is not logged in!", logging_level=logging.ERROR) TODO
                return

            return method(cls, *args, **kwargs)

        return _inner

    return inner


def requires_specific_route(route):
    """This decorator takes a list or a string of route/s and will naviagte to one of them to be on the right link
    before the method gets called."""

    def inner(method):
        def _inner(cls, *args, **kwargs):
            target_route = route if isinstance(route, str) else random.choice(route)
            if target_route.lower() not in cls.driver.current_url.lower():
                target_page_btn = cls.actions.find_element_by_xpath(f"//a[@href='{target_route}']")
                if target_page_btn is None:
                    if "/account/overview/" in cls.driver.current_url:
                        spotify_logo_to_click = cls.actions.find_element_by_xpath(
                            "//a[@class='mh-header-primary svelte-18o1xvt']")
                        cls.actions.click(element=spotify_logo_to_click)
                        time.sleep(random.randint(1, 3))
                        open_webplayer_btn = cls.actions.find_element_by_xpath("//a[@class='btn btn-stroked-dark']")
                        cls.actions.click(element=open_webplayer_btn)
                        target_page_btn = cls.actions.find_element_by_xpath(f"//a[@href='{target_route}']")
                    else:
                        cls.event_queue.put(ThreadSignals.ERROR)
                        cls.debugged_print(msg=f"Failed to navigate to the route {target_route}", status="ERROR")
                        return
                cls.actions.click(element=target_page_btn)
                print(f"Navigated to the route {target_route}")
            return method(cls, *args, **kwargs)

        return _inner

    return inner


class SpotifyBotInstance:
    log_in_status = AccountStatus.NOT_LOGGED_IN

    def __init__(self, account, event_queue, parent, thread_id, song_skipping_chance, debug=False):
        self.account_meta_dict, self.account_dict = MongoDBHelper().account_data(account=account)
        self.event_queue = event_queue
        self.debug = debug
        self.driver = self.setup_driver()
        self.song_skipping_chance = song_skipping_chance

        self.actions = SeleniumHelper(driver=self.driver, mobile=self.account_meta_dict["user_agent"][
            "is_mobile"])  # TODO: Implement is_mobile this on the account adding process
        self.print_to_gui = ConsolePage(parent=parent, thread_id=thread_id)

    @property
    def email(self):
        """Getter for easier account email access"""
        return self.account_meta_dict["account"].split(":", 1)[0]

    @property
    def password(self):
        """Getter for easier account password accesss"""
        return self.account_meta_dict["account"].split(":", 1)[1]

    @staticmethod
    def setup_driver():
        """Sets up the driver
        :return: webdriver instance"""
        options = undetected_chromedriver.ChromeOptions()
        options.add_experimental_option('w3c', False)
        return undetected_chromedriver.Chrome(options=options,
                                              executable_path="../../driver/chromedriver/chromedriver_89.exe")

    def initialization(self):
        """Gets called after the self.login() and makes sure that the playback gets stopped and reseted.
        :return:None
        """
        self.actions.navigate_to_weplayer_from_overview_page()
        time.sleep(random.randint(1, 2))
        self.click_playback_btn(stop_playback=True)
        time.sleep(random.randint(1, 2))
        self.reset_playback()
        time.sleep(random.randint(1, 2))
        self.click_repeat_song_btn(1)

    def calculate_total_track_seconds(self):
        """Calculates the total seconds of playltime of the current playing track without respect to the lost time"""
        time_element = self.actions.find_element_by_xpath("//div[@data-testid='playback-duration']")
        return math.ceil(int(time_element.text.split(":")[0]) * 60 + int(time_element.text.split(":")[1]))

    def calculate_total_already_played_track_seconds(self):
        """Calculates the already listened seconds of a song"""
        time_element = self.actions.find_element_by_xpath("//div[@data-testid='playback-position']").text.split(":")
        print(f"Already lost sleep time: {int(time_element[0]) * 60 + int(time_element[1])}")
        return math.ceil(int(time_element[0]) * 60 + int(time_element[1]))

    def calclulate_random_listening_time(self, track_total_seconds):
        """
        Different from SpotifyBotInstance.calculate_total_track_seconds(), since this calculates the track listening seconds
        with a random factor, so that the bot listens a random time to the songs.
        :param track_total_seconds: Total length of the tracks in seconds
        :return: play_not_full_song, sleep_time
        """
        lost_sleep_time = self.calculate_total_already_played_track_seconds()

        if is_random(random.randint(10, 20)):
            sleep_time = (track_total_seconds * random.randint(3, 9) / 10) - lost_sleep_time

            if is_random(random.randint(10, 12)):
                sleep_time = random.randint(1, 30)

            play_not_full_song = True
        else:
            sleep_time = track_total_seconds - lost_sleep_time
            play_not_full_song = False

        self.debugged_print(msg=f"Sleep time: {sleep_time}",
                            status="INFO", only_debug=True)

        return math.floor(play_not_full_song), abs(sleep_time)

    def accept_cookies(self):
        """Accepts cookies when they appear
        :return: if the cookies got accepted (True/False)
        """
        accept_cookie_btn = self.actions.find_element_by_xpath("//button[@id='onetrust-accept-btn-handler']")

        if accept_cookie_btn is not None:
            self.actions.click(element=accept_cookie_btn)
            return True
        else:
            return False

    def choose_random_playlist(self):
        """Picks a random playlist from the synchronized playlists
        :return: None if error occured and a random playlist if not
        """
        accounts_playlist = self.account_meta_dict["playlist"]["playlists"]

        if not accounts_playlist:
            return None

        return random.choice(accounts_playlist)

    def debugged_print(self, msg, status, only_debug=False):
        """Defines the output of the application and is used as a switch for the print messages between development
        (only_debug=True) and production (only_debug=False).
        :return: None
        """

        if not self.debug and not only_debug:
            self.print_to_gui.add_message(status=status, message=msg)
        else:
            print(f"[DEBUG MODE] [{status}] [only_debug={only_debug}] {msg}")

    def skip_song(self):
        time.sleep(random.randint(3, 10))

        song_skip_element = self.actions.find_element_by_xpath("//button[@data-testid='control-button-skip-forward']")

        self.actions.click(element=song_skip_element)

    def wait_for_advertisement_to_finish(self):
        """Checks for advertisement and if it exists it will listen to it.
        :return:bool wheter the action was performed successfully or not
        """
        advertisement = self.actions.find_element_by_xpath(
            "//div[@class='cover-art shadow cover-art--with-auto-height']", timeout=4)

        if advertisement is not None:
            time.sleep(self.calculate_total_track_seconds() - self.calculate_total_already_played_track_seconds())
            self.event_queue.put(ThreadSignals.LISTENED_TO_AD)
            self.debugged_print(msg=f"Account {self.email} > Listened to ad", status="INFO")
            time.sleep(random.randint(3, 4))
            return True
        else:
            return False

    def adjust_playback(self, set_playback_volume=None):
        """
        Adjusts the playback volume to a given or random value.
        :param set_playback_volume: caller defines the playback volume
        :return: bool indicating if an error occurred or not
        """
        if set_playback_volume is None:
            set_playback_volume = random.randint(1, 10) * 10

        playback_volume = self.actions.find_element_by_xpath("//div[@data-testid='volume-bar']")

        if playback_volume is None:
            return False

        act = ActionChains(self.driver)
        act.move_to_element(playback_volume)
        playback_pixel = math.floor(playback_volume.size["width"] / 100 * set_playback_volume)

        if playback_pixel < int(playback_volume.size["width"] / 2):
            playback_pixel = - int(playback_pixel / 2)
        elif playback_pixel == int(playback_volume.size["width"] / 2):
            playback_pixel = 0
        else:
            playback_pixel = int(playback_pixel / 2)

        act.move_by_offset(playback_pixel, 0).click()
        act.perform()
        self.debugged_print(msg=f"Successfully adjusted the playback to ~{set_playback_volume}%", status="INFO", only_debug=True)
        return True

    def click_repeat_song_btn(self, repeat_times=1):
        repeat_element = self.actions.find_element_by_xpath("//button[@data-testid='control-button-repeat']")
        if repeat_times is None:
            return True

        if repeat_element.get_attribute("aria-checked") == "mixed":
            if repeat_times == 3:
                return True
            elif repeat_times == 1:
                self.actions.click(element=repeat_element)
            elif repeat_times == 2:
                for _ in range(2):
                    self.actions.click(element=repeat_element)
                    time.sleep(random.randint(1, 2))
            else:
                raise ValueError(f"repeat_times must be in the range 0 < repeat_times <=3")
            return True

        if repeat_element.get_attribute("aria-checked") == "false":
            if repeat_times == 3:
                for _ in range(2):
                    self.actions.click(element=repeat_element)
                    time.sleep(random.randint(1, 2))
            elif repeat_times == 1:
                return True
            elif repeat_times == 2:
                self.actions.click(element=repeat_element)
            else:
                raise ValueError(f"repeat_times must be in the range 0 < repeat_times <=3")
            return True

        if repeat_element.get_attribute("aria-checked") == "true":
            if repeat_times == 3:
                self.actions.click(element=repeat_element)
            elif repeat_times == 1:
                for _ in range(2):
                    self.actions.click(element=repeat_element)
                    time.sleep(random.randint(1, 2))
            elif repeat_times == 2:
                return True
            else:
                raise ValueError(f"repeat_times must be in the range 0 < repeat_times <=3")
            return True

        return False

    def click_shuffle_song_btn(self, toggle_on=True):
        shuffle_element = self.actions.find_element_by_xpath("//button[@data-testid='control-button-shuffle']")

        if shuffle_element is None:
            return False

        if toggle_on and shuffle_element.get_attribute('aria-checked') != "true":
            self.actions.click(element=shuffle_element)

        if not toggle_on and shuffle_element.get_attribute('aria-checked') == "true":
            self.actions.click(element=shuffle_element)

        return True

    def click_playback_btn(self, stop_playback=True):
        print(sys._getframe().f_back.f_code.co_name)
        playback_btn = self.actions.find_element_by_xpath("//button[@data-testid='control-button-play']")
        if playback_btn is not None and not stop_playback:
            print("Continued the playback")
            self.actions.click(element=playback_btn)
            return True

        playback_btn = self.actions.find_element_by_xpath("//button[@data-testid='control-button-pause']")
        if playback_btn is not None and stop_playback:
            print("Stopped the playback")
            self.actions.click(element=playback_btn)
            return True

        print("Failed to stop/continue the playback")
        return False

    def is_target_song(self, artist_name, song_name):
        if artist_name in self.account_meta_dict["artists"]:
            self.event_queue.put(ThreadSignals.STREAM_GAINED)
            self.debugged_print(msg=f"Gained a Stream || Artist: {artist_name} || Song: {song_name} ||",
                                status="SUCCESS")

    def reset_playback(self):
        if not self.calculate_total_already_played_track_seconds() > 3:
            return

        try:
            song_back = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@class='bc13c597ccee51a09ec60253c3c51c75-scss']")))
            self.actions.click(element=song_back)
        except TimeoutException:
            return

        self.actions.click(element=song_back)

    def connect_to_device_actions(self):
        device_actions = self.actions.find_element_by_xpath(f"//span[@class='connect-device-picker']//button")

        if device_actions is None:
            return False

        self.actions.click(element=device_actions)

        device_to_pick = self.actions.find_element_by_xpath("//button[@class='media connect-device-list-item']")

        if device_to_pick is None:
            return False

        self.actions.click(element=device_to_pick)

        return True

    def login(self):
        """
        This function navigates to https://www.spotify.com/login and will check wheter the account is logged in or not.
        If the account is logged in, it will return from this function. However if the account isn't already logged in
        it will log it in and safe the session in the predefined user-data-dir. Once the log in fails because of wrong
        credentials or a proxy error, it will set the account_working flag inside the mongodb to false. This function
        will also increment the logins on the session collection (by 1 if the login was valid) and post the login to the
        bot creators api.
        ----------------------------------------------------------------------------------------------------------------
        :chances:
            - [8 - 14%] click on "register on Spotify" and then go a step back after x seconds
            - [7 - 9%] generate a new cookie footprint with n amount of steps before logging in
            - [3 - 8%] refresh the page
            - [5 - 7%] uncheck the "safe account login details" checkbox
            - [4 - 6%] click on login with facebook, or apple or google
                - [10 - 15%] click on a random link on the new site and then go two steps back after x seconds
                    - [3- 7%] after going back one site, go forward one more time
            - [1 - 2%] quit the webdriver and stop all further actions for this account after log in
        ----------------------------------------------------------------------------------------------------------------
        :return: bool
            - bool: did a fatal exception occur? Or did the bot stopped earlier because it hit the 1-2 percent
              treshhold ? -> (True/False)
        """
        if len([cookie for cookie in self.driver.get_cookies() if "accounts.spotify.com" == cookie["domain"]]) != 0:
            self.debugged_print(msg=f"Account > {self.email} already logged in", status="INFO")
            self.log_in_status = AccountStatus.LOGGED_IN
            return False

        if is_random(random.randint(7, 9)) and not self.account_meta_dict["incognito"]:
            GenerateFootprint(random.randint(1, 40), self.email, driver=self.driver).generate_footprint()

        time.sleep(random.randint(0, 3))

        try:
            self.driver.get(f'https://www.spotify.com/{self.account_meta_dict["country"]}/login')
            self.accept_cookies()
        except WebDriverException:
            self.debugged_print(msg=f"Account > {self.email} || Failed to navigate to spotify.com/login",
                                status="ERORR")
            self.event_queue.put(ThreadSignals.FAILED_LOGIN)
            self.log_in_status = AccountStatus.PROXY_ERROR
            return True, False

        time.sleep(random.randint(0, 3))

        for index in range(3):
            redirect_btn = \
            self.actions.find_element_by_xpath(xpath="//div[@class='col-xs-12']//a[@ng-href]", multiple_elements=True)[
                index]
            if is_random(random.randint(4, 6)):
                self.actions.click(element=redirect_btn)
                time.sleep(random.randint(1, 5))
                if not index:  # gets triggered only on the first run since index == 0 gets evalueted to False
                    try:
                        accept_fb_cookies_btn = self.actions.find_element_by_xpath(
                            "//button[@data-testid='cookie-policy-dialog-accept-button']")
                        self.actions.click(element=accept_fb_cookies_btn)
                    except WebDriverException:
                        pass
                if is_random(random.randint(4, 6)):
                    total_back_forth_iterations = random.randint(1, 4)
                    total_iterations = 0
                    for _ in range(total_back_forth_iterations):
                        search_links = self.actions.find_element_by_xpath("//a[@href and not(@target='_blank')]",
                                                                          multiple_elements=True)
                        if len(search_links) > 0:
                            link = random.choice(search_links)
                            self.actions.click(element=link)
                            total_iterations += 1
                    time.sleep(random.randint(2, 6))
                    for _ in range(total_iterations):
                        self.driver.back()
                        if is_random(random.randint(3, 7)):
                            self.driver.forward()
                            time.sleep(random.randint(1, 4))
                            self.driver.back()
                        time.sleep(random.randint(1, 3))
                    time.sleep(random.randint(1, 2))
                time.sleep(random.randint(1, 3))
                self.driver.back()

        if is_random(random.randint(3, 8)):
            self.driver.refresh()

        if is_random(random.randint(8, 14)):
            time.sleep(1)
            register_on_spotify_btn = self.actions.find_element_by_xpath("//a[@id='sign-up-link']")
            self.actions.click(element=register_on_spotify_btn)
            time.sleep(random.randint(1, 10))
            self.driver.back()
            time.sleep(random.randint(2, 3))
            if self.accept_cookies():
                self.debugged_print(msg=f"Account > {self.email} accepted cookies", status="INFO")

        if is_random(random.randint(5, 7)):
            safe_account_details_btn = self.actions.find_element_by_xpath("//div[@class='checkbox']")
            self.actions.click(element=safe_account_details_btn)

        time.sleep(random.randint(1, 2))

        username_login_field = self.actions.find_element_by_xpath("//input[@id='login-username']")
        self.actions.legit_typing(element=username_login_field, text=self.email,
                                  clear_input_field=True)

        time.sleep(random.randint(1, 3))

        password_login_field = self.actions.find_element_by_xpath("//input[@id='login-password']")
        self.actions.legit_typing(element=password_login_field, text=self.password,
                                  clear_input_field=True)

        time.sleep(random.randint(2, 3))

        login_btn = self.actions.find_element_by_xpath(xpath="//button[@id='login-button']")
        self.actions.click(element=login_btn)

        time.sleep(random.randint(2, 4))
        if self.accept_cookies():
            self.debugged_print(msg=f"Account > {self.email} accepted cookies", status="INFO")

        if self.actions.find_element_by_xpath("//span[@class='ng-binding ng-scope']") is not None:
            self.event_queue.put(ThreadSignals.FAILED_LOGIN)
            self.log_in_status = AccountStatus.NOT_LOGGED_IN
            self.debugged_print(msg=f"Account {self.email} > Login Failed (Wrong Credentials)", status="ERROR")
            return True

        time.sleep(random.randint(2, 4))
        account_plan_element = self.actions.find_element_by_xpath(
            "//span[@class='PlanHeader__ProductName-sc-14eqsfg-3 ctYAHi']")
        self.driver.execute_script("arguments[0].scrollIntoView();", account_plan_element)

        time.sleep(random.randint(1, 2))

        self.account_meta_dict["account_plan"] = account_plan_element.text
        MongoDBHelper().set_account_meta_data(new_account_object=self.account_meta_dict)

        if is_random(random.randint(1, 2)) and self.account_meta_dict["allow_earlier_stopping"]:
            self.debugged_print(msg=f"Account > {self.email} stopping after login", status="INFO")
            self.debugged_print(status="INFO", msg=f"Account > {self.email} stopping after login")
            self.event_queue.put(ThreadSignals.STOPPED_EARLIER)
            return True

        self.debugged_print(msg=f"Account > {self.email} logged in successfully", status="SUCCESS")
        self.event_queue.put(ThreadSignals.GAINED_LOGIN)
        self.log_in_status = AccountStatus.LOGGED_IN

        return False

    @requires_account_log_in(True)
    @requires_specific_route(route=["/search", "/", "/collection", "/collection/tracks"])
    def create_playlist(self):
        """
        This method is used to create playlists if the current account is choosen to create playllists. It will only
        create the playlists on a certain percentage to prevent all playlists from beeing created direct on the first
        run.
        ----------------------------------------------------------------------------------------------------------------
        :chances:
            - [20 - 30%] pick a target song to put into the playlist
            - [10 - 15%] create a playlist description
            - [10 - 14%] create a new playlist if needed
            - [3 - 8%] refresh the page
            - [1 - 2%] quit the webdriver and stop all further actions for this account after log in
            ----------------------------------------------------------------------------------------------------------------
        :return: bool
            - bool: did a fatal exception occur? Or did the bot stopped earlier because it hit the 1-2 percent
                treshhold ? -> (True/False)
        """
        cp = self.actions.find_element_by_xpath("//ul[@data-testid='rootlist']/li", multiple_elements=True)
        if cp is None:
            current_playlists = []
        else:
            current_playlists = [pl.text for pl in cp]
        synced_playlists = self.account_meta_dict["playlist"]["playlists"]  # accounts playlists

        unsynced_playlists = list(set(synced_playlists) - set(current_playlists)) + list(
            set(current_playlists) - set(synced_playlists))

        for up in unsynced_playlists:
            if up not in synced_playlists:
                self.account_meta_dict["playlist"]["playlists"].append(up)
            elif up in synced_playlists and up not in current_playlists:
                self.account_meta_dict["playlist"]["playlists"].remove(up)

        if self.account_meta_dict["playlist"]["playlist_amount"] < len(self.account_meta_dict["playlist"]["playlists"]):
            self.account_meta_dict["playlist"]["playlist_amount"] = len(self.account_meta_dict["playlist"]["playlists"])

        MongoDBHelper().set_account_meta_data(self.account_meta_dict)

        if self.account_meta_dict["playlist"]["playlist_amount"] == len(
                self.account_meta_dict["playlist"]["playlists"]):
            self.debugged_print(msg="Account already has the desired amount of playlists", status="INFO",
                                only_debug=True)
            return False

        if is_random(random.randint(10, 14)):
            create_playllist_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='create-playlist-button']")))
            self.actions.click(element=create_playllist_btn)

            time.sleep(random.randint(1, 3))

            playlist_menu_btn = self.actions.find_element_by_xpath(
                "//span[@class='_24864e895a756f2651d941331fe60a46-scss']")
            self.actions.click(element=playlist_menu_btn)

            time.sleep(random.randint(1, 4))

            available_playlist_names = MongoDBHelper().configurations.find_one()["playlist"]["playlist_names"]
            playlist_name = None

            searching_for_playlist_name = True
            max_timeout = len(available_playlist_names) * 2
            index = 0

            while searching_for_playlist_name:
                current_name = random.choice(available_playlist_names)
                if current_name not in current_playlists:
                    playlist_name = current_name

                if index == max_timeout:
                    searching_for_playlist_name = False
                index += 1

            if playlist_name is None:
                self.debugged_print(msg=f"Account > {self.email} No free playlist name found", status="ERROR")
                self.event_queue.put(ThreadSignals.ERROR)
                return False

            playlist_name_input = self.actions.find_element_by_xpath(
                "//input[@data-testid='playlist-edit-details-name-input']")
            self.account_meta_dict["playlist"]["playlists"].append(playlist_name)
            self.actions.legit_typing(element=playlist_name_input, clear_input_field=True, text=playlist_name)

            playlist_description_input = self.actions.find_element_by_xpath(
                "//textarea[@data-testid='playlist-edit-details-description-input']")

            if is_random(random.randint(10, 15)):
                self.actions.legit_typing(element=playlist_description_input, clear_input_field=False,
                                          text=random.choice(MongoDBHelper().configurations.find_one()["playlist"][
                                                                 "playlist_descriptions"]))

            save_playlist_btn = self.actions.find_element_by_xpath(
                "//button[@data-testid='playlist-edit-details-save-button']")
            self.actions.click(element=save_playlist_btn)

            account_genre = self.account_meta_dict["favorite_song"]["genre"]
            account_genre_songs = MongoDBHelper().configurations.find_one()["favorite_songs"][account_genre]
            print(account_genre_songs)
            target_song_names = []

            for artist in self.account_meta_dict["artists"]:
                for ts in MongoDBHelper().artist_data(artist)["artist_botting_links"]["single_songs"]:
                    if ts.startswith("http"):
                        continue
                    if is_random(random.randint(30, 40)) or MongoDBHelper().artist_data(artist)["best_song"] in ts:
                        target_song_names.append({"artist_name": artist, "song": ts})

            used_songs = []
            added_song_amt = 0

            for _ in range((random.randint(4, 15))):
                if is_random(random.randint(20, 30)):
                    song_to_add = random.choice(target_song_names)
                else:
                    song_to_add = random.choice(account_genre_songs)

                if song_to_add in used_songs:
                    continue

                add_playlist_song_input = self.actions.find_element_by_xpath(
                    "//input[@class='_655bc45ccbf3d91c685865ff470892eb-scss f3fc214b257ae2f1d43d4c594a94497f-scss']")
                self.actions.legit_typing(element=add_playlist_song_input, clear_input_field=True,
                                          text=f"{song_to_add['song']} {song_to_add['artist_name']}")

                found_songs = self.actions.find_element_by_xpath("//div[@data-testid='tracklist-row']",
                                                                 multiple_elements=True)

                if found_songs is None:
                    self.debugged_print(msg=f"Couldn't add the song {song_to_add} because it was not found",
                                        status="ERROR", only_debug=True)
                    continue

                for i, found_song in enumerate(found_songs):
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView();", found_song)
                    except WebDriverException:
                        self.debugged_print(msg=f"Couldn't add the song {song_to_add} because it was not found",
                                            status="ERROR", only_debug=True)
                        break

                    if song_to_add["song"] in found_song.text.splitlines()[0] and song_to_add["artist_name"] in \
                            found_song.text.splitlines()[1]:
                        add_song_to_playlist_btn = \
                            self.actions.find_element_by_xpath("//button[@data-testid='add-to-playlist-button']",
                                                               multiple_elements=True)[
                                i - added_song_amt]
                        self.actions.click(element=add_song_to_playlist_btn)

                        self.debugged_print(msg=f"Added the song {song_to_add} to the playlist", status="INFO",
                                            only_debug=True)

                        added_song_amt += 1
                        break

                    time.sleep(random.random())

                used_songs.append(song_to_add)
                time.sleep(random.randint(1, 3))

            MongoDBHelper().set_account_meta_data(self.account_meta_dict)
            self.debugged_print(
                msg=f"Account {self.email}> Created the playlist \"{playlist_name}\" with a total of {len(used_songs)} songs",
                status="SUCCESS")
            self.event_queue.put(ThreadSignals.CREATED_PLAYLIST)

            if is_random(random.randint(1, 2)) and self.account_meta_dict["allow_earlier_stopping"]:
                self.debugged_print(msg=f"Account {self.email} >  stopped after adding new playlist", status="INFO")
                self.event_queue.put(ThreadSignals.STOPPED_EARLIER)
                return True

    @requires_account_log_in(True)
    @requires_specific_route(route=["/search", "/", "/collection", "/collection/tracks"])
    def delete_playlist(self, playlist_name=None):
        """
        Deletes a random playlist to create randomness to the process. This method can only be used when the state of
        the account is on the webplayer page and has access to the playlist on the left side. It will also remove the
        deleted playlist from the database to sync the database in real time.
        ----------------------------------------------------------------------------------------------------------------
        :chances:
        - [4 - 8%] after deleting a random playlist create a new one (call SpotifyBotInstance.create_playlist())
        - [1 - 2%] quit the webdriver and stop all further actions for this account after the action
        ----------------------------------------------------------------------------------------------------------------
        :return: bool
            - bool: did a fatal exception occur? Or did the bot stopped earlier because it hit the 1-2 percent
                treshhold ? -> (True/False)
        """
        to_delete_playlist = playlist_name if playlist_name is not None else self.choose_random_playlist()

        if to_delete_playlist is None:
            return

        time.sleep(random.randint(1, 2))

        for index, playlist in enumerate(
                self.actions.find_element_by_xpath("//div[@data-testid='rootlist-item']", multiple_elements=True)):
            playlist_name = playlist.text
            if playlist_name == to_delete_playlist:
                self.actions.click(element=playlist)
                time.sleep(random.randint(1, 2))

                playlist_menu_btn = self.actions.find_element_by_xpath(
                    "//button[@class='_605821ce181f6de6632eabd6a46377fb-scss']")
                self.actions.click(element=playlist_menu_btn)
                time.sleep(random.randint(1, 2))

                delete_btn = \
                    self.actions.find_element_by_xpath("//button[@class='d2a8e42f26357f2d21c027f30d93fb64-scss']",
                                                       multiple_elements=True)[3]
                self.actions.click(element=delete_btn)
                time.sleep(random.randint(1, 2))

                accept_del_btn = self.actions.find_element_by_xpath(
                    "//button[@class='_3f37264be67c8f40fa9f76449afdb4bd-scss _9eb5acf729a98d62135ca21777fef244-scss']")
                self.actions.click(element=accept_del_btn)
                time.sleep(random.randint(1, 2))

                self.debugged_print(msg=f"Account {self.email} > Randomly deleted the playlist \"{playlist_name}\"",
                                    status="INFO")

                self.account_meta_dict["playlist"]["playlists"].remove(to_delete_playlist)
                MongoDBHelper().set_account_meta_data(new_account_object=self.account_meta_dict)
                break

        time.sleep(random.randint(1, 3))

        if is_random(random.randint(4, 8)):
            self.create_playlist()

        if is_random(random.randint(1, 2)) and self.account_meta_dict["allow_earlier_stopping"]:
            self.debugged_print(msg=f"Account > {self.email} stopping after adding deleting a random playlist",
                                status="INFO")
            self.event_queue.put(ThreadSignals.STOPPED_EARLIER)
            return True

    @requires_account_log_in(True)
    @requires_specific_route(route=["/search", "/", "/collection", "/collection/tracks"])
    def listen_to_random_playlist(self):
        if not self.account_meta_dict["playlist"]["playlists"]:
            return False

        playlist_to_listen = self.choose_random_playlist()

        if playlist_to_listen is None:
            return False

        for index, playlist in enumerate(
                self.actions.find_element_by_xpath("//div[@data-testid='rootlist-item']", multiple_elements=True)):
            if playlist.text == playlist_to_listen:
                self.actions.click(element=playlist)
                break

        time.sleep(random.randint(1, 4))

        clickable_track_btns = self.actions.find_element_by_xpath(
            "//button[@class='_38168f0d5f20e658506cd3e6204c1f9a-scss']", multiple_elements=True)

        if is_random(random.randint(20, 30)):
            if self.click_shuffle_song_btn(toggle_on=True):
                self.debugged_print(msg="Clicked the shuffle song button", status="INFO", only_debug=True)
            play_shuffled_playlist = True
        else:
            self.click_shuffle_song_btn(toggle_on=False)
            play_shuffled_playlist = False

        tracks = self.actions.find_element_by_xpath("//div[@data-testid='tracklist-row' and div[span]]",
                                                    multiple_elements=True)
        if tracks is None:
            self.debugged_print(msg=f"The playlist \"{playlist_to_listen}\" doesn't contain any tracks -> deleting it",
                                status="ERROR", only_debug=True)
            self.delete_playlist(playlist_name=playlist_to_listen)
            return

        time.sleep(1)
        act = ActionChains(self.driver)
        act.move_to_element(tracks[0])
        act.perform()
        time.sleep(4)

        play_btn = clickable_track_btns[0]
        self.actions.click(element=play_btn)

        deleted_tracks = 0
        for track_number, track in enumerate(tracks):
            self.click_playback_btn(stop_playback=False)
            iteration_start_time = time.time()
            if self.account_meta_dict["account_plan"] == "Spotify Free":
                self.wait_for_advertisement_to_finish()

            time.sleep(random.randint(1, 2))
            song_name = self.actions.find_element_by_xpath("//a[@data-testid='nowplaying-track-link']").text
            song_artist = self.actions.find_element_by_xpath("//a[@data-testid='nowplaying-artist']").text

            time.sleep(random.randint(3, 4))

            self.debugged_print(
                msg=f"Now listening to the song \"{song_name}\" from the playlist \"{playlist_to_listen}\"",
                status="INFO", only_debug=True)

            if is_random(random.randint(self.song_skipping_chance - random.randint(1, 4), self.song_skipping_chance)):
                self.skip_song()
                self.debugged_print(msg=f"Account {self.email} > Skipped the song \"{song_name}\"", status="INFO",
                                    only_debug=True)
                self.event_queue.put(ThreadSignals.SKIPPED_SONG)
                continue

            if is_random(random.randint(4, 7)) and not play_shuffled_playlist:
                to_delete_song = self.actions.find_element_by_xpath(
                    f"//div[@role='row' and @aria-rowindex='{track_number + 2 - deleted_tracks}']/div[@data-testid='tracklist-row' and div[span]]",
                    multiple_elements=True)[0]
                try:
                    act = ActionChains(self.driver)
                    act.move_to_element(to_delete_song)
                    act.perform()
                except WebDriverException:
                    self.debugged_print(msg=f"Error occured trying to delete the track \"{song_name}\"", status="ERROR",
                                        only_debug=True)
                    self.event_queue.put(ThreadSignals.ERROR)
                    self.skip_song()
                    continue

                context_icon = self.actions.find_element_by_xpath(
                    "//button[@class='_605821ce181f6de6632eabd6a46377fb-scss _50a94aaa6bd60a02583729be7f0e4f93-scss']",
                    multiple_elements=True)[track_number - deleted_tracks]

                time.sleep(random.randint(1, 2))

                self.actions.click(element=context_icon)
                time.sleep(random.randint(1, 2))

                remove_track_from_playlist = self.actions.find_element_by_xpath(
                    "//span[@class='ellipsis-one-line f3fc214b257ae2f1d43d4c594a94497f-scss']", multiple_elements=True)[
                    6]
                remove_track_from_playlist = remove_track_from_playlist.find_element_by_xpath("..")
                self.actions.click(element=remove_track_from_playlist)
                time.sleep(random.randint(1, 2))

                self.debugged_print(msg=f"Deleted the song \"{song_name}\" from the playlist \"{playlist_to_listen}\"",
                                    status="INFO", only_debug=True)
                time.sleep(random.randint(2, 4))
                self.skip_song()
                deleted_tracks += 1
                continue

            if is_random(random.randint(5, 12)):
                self.adjust_playback()

            if is_random(random.randint(3, 6)):

                if self.connect_to_device_actions():
                    self.debugged_print(msg=f"Connected to a random device on Spotify", status="INFO", only_debug=True)

            play_not_full_song, sleep_time = self.calclulate_random_listening_time(track_total_seconds=self.calculate_total_track_seconds())
            time.sleep(sleep_time)

            if play_not_full_song:
                self.skip_song()

                if round(time.time() - iteration_start_time) >= 30:
                    self.is_target_song(artist_name=song_artist, song_name=song_name)
                continue

            self.is_target_song(artist_name=song_artist, song_name=song_name)

            if is_random(random.randint(5, 8)):
                self.debugged_print(msg=f"Randomly stopped listening to the playlist: {playlist_to_listen}", status="INFO")
                break

        self.click_playback_btn(stop_playback=True)
        time.sleep(random.randint(2, 4))
        self.wait_for_advertisement_to_finish()
        self.debugged_print(msg=f"Finished listening to the playlist: \"{playlist_to_listen}\"", status="INFO",
                            only_debug=True)

        if is_random(random.randint(1, 2)):
            self.debugged_print(msg=f"Hitted 1-2 % treshold to create a random playlist after listening to a random playlist",status="INFO", only_debug=True)
            self.create_playlist()

        if is_random(random.randint(1, 2)):
            self.debugged_print(msg=f"Hitted 1-2 % treshold to delete a random playlist after listening to a random playlist",status="INFO", only_debug=True)
            self.delete_playlist()
        return False

    @requires_account_log_in(True)
    @requires_specific_route(route=["/search"])
    def listen_to_favorite_song_in_minimized_window(self):
        """
        Listens to account's favorite songs in a minimized window, it will get to the song using the hyperlink provided
        by the artist or it will use the search bar and search for the song.
        ----------------------------------------------------------------------------------------------------------------
        :chances:
            - [1-2%] quit the webdriver and stop all further actions after the action
        ----------------------------------------------------------------------------------------------------------------
        :return: bool
            - bool: did a fatal exception occur? Or did the bot stopped earlier because it hit the 1-2 percent
              treshhold ? -> (True/False)
        """
        self.reset_playback()
        time.sleep(random.randint(1, 2))
        self.click_playback_btn(stop_playback=True)

        favorite_song = self.account_meta_dict["favorite_song"]["song_name"]
        favorite_song_artist = self.account_meta_dict["favorite_song"]["song_artist"]

        song_input_field = self.actions.find_element_by_xpath("//input[@data-testid='search-input']")

        self.actions.legit_typing(element=song_input_field, text=f"{favorite_song} {favorite_song_artist}", clear_input_field=True)

        total_iterations = random.randint(1, 5)
        self.debugged_print(msg=f"Now listening to the favorite song \"{favorite_song}\" for {total_iterations}x time/s", status="INFO")
        for iteration in range(total_iterations):
            if not iteration:
                self.click_repeat_song_btn(2)

                search_results = self.actions.find_element_by_xpath("//div[@data-testid='tracklist-row']",
                                                                    multiple_elements=True)

                if search_results is None:
                    self.debugged_print(msg=f"Couldn't find the favorite song \"{favorite_song}\"", status="ERROR")
                    self.event_queue.put(ThreadSignals.ERROR)
                    return False

                for index, found_song in enumerate(search_results):
                    if favorite_song_artist in found_song.text.splitlines()[1] and favorite_song in \
                            found_song.text.splitlines()[0]:
                        time.sleep(random.randint(1, 2))
                        act = ActionChains(self.driver)
                        act.move_to_element(found_song)
                        act.perform()
                        start_playback_btn = self.actions.find_element_by_xpath(
                            "//div[@class='_9811afda86f707ead7da1d12f4dd2d3e-scss']//button", multiple_elements=True)[
                            index]
                        self.actions.click(element=start_playback_btn)
                        print(f"Successfully started the playback for the song {favorite_song}")
                        time.sleep(random.randint(2, 4))
                        self.driver.minimize_window()
                        break

            print("Sleeping now")
            time.sleep(random.randint(2, 3))
            sleep_time = self.calculate_total_track_seconds() - self.calculate_total_already_played_track_seconds()
            print(f"Sleep time: {sleep_time}")
            time.sleep(sleep_time)

        time.sleep(random.randint(2, 3))
        self.click_playback_btn(stop_playback=True)
        time.sleep(random.randint(2, 3))
        self.reset_playback()
        print("Finished")
        self.driver.maximize_window()

    @requires_account_log_in(True)
    def explore_new_songs(self):
        """
        Explores new songs. It will start listening to the predefined favorite song and will listen to suggestions to
        explore new songs. It also has a small probability to replace/add a random new explored song to the favorite
        songs. If the account has no favorite song, it will just start listening to random songs from a random picked
        genre from the database.
        ----------------------------------------------------------------------------------------------------------------
        :chances:
            - [4-7%] randomly stop this action after listening to a song
            - [2-5%] adjust playback volume
            - [2-5%] explore new songs in minimized window
            - [2-5%] explore new songs in maximized window
            - [2-4%] replace already existing favorite songs with a new explored one
            - [2-4%] add a new explored song to the favorite songs
            - [1-3%] use a new explored song as the favorite song on a account which has no favorite song
            - [1-3%] save the song to a self defined random playlist if the user has a self defined playlist
            - [1-2%] quit the webdriver and stop all further actions for this account after the action
            - [user-defined] skip a song
            - [user-defined] mute playback for x seconds
            - [user-defined] heart a song
            - [user-defined] follow the artist of a explored song
        ----------------------------------------------------------------------------------------------------------------
        :return: bool
            - bool: did a fatal exception occur? Or did the bot stopped earlier because it hit the 1-2 percent
              treshhold ? -> (True/False)
        """
        pass

    @requires_account_log_in(True)
    def listen_to_favorite_song_for_x_sec(self):
        pass

    @requires_account_log_in(True)
    def listen_to_charts(self):
        pass

    def start(self):
        """
        This method is used to start and coordinate the whole botting operation on each account. It is responsible to
        start all functions selected from the GenerateWorkInstructions class.
        :return: None
        """
        if self.login():
            return

        self.initialization()

        if self.account_meta_dict["playlist"]["have_playlist"] and not self.account_meta_dict["playlist"][
            "playlist_name"]:
            self.create_playlist()

        workload = GenerateWorkInstructions().generate_workload()  # load the "to use" functions

        for method_to_use in workload:
            if method_to_use != self.start.__name__:  # checks if the current method != to the start() method
                if getattr(self, method_to_use)():  # call the bots methods
                    break


class GenerateWorkInstructions:
    """Generates a custom MRO of functions in a random order from the SpotifyBotInstance class"""

    @staticmethod
    def generate_workload(min_jobs=1, max_jobs=12):
        """
        This function will create "jobs" which will then be executed by the SpotifyBotInstance class and their methods
        :param min_jobs: minimum amount of jobs to create
        :param max_jobs: maximum amount of jobs to create
        :return: list containing the jobs
        """
        class_methods = [m for m in SpotifyBotInstance.__dict__ if
                         not m.startswith('__') and hasattr(SpotifyBotInstance, m)]
        return [random.choice(class_methods) for _ in range(min_jobs, max_jobs)]


if __name__ == '__main__':
    queue = queue.Queue()
    instance = SpotifyBotInstance(account="spotify-account0002@protonmail.com:_5]38=\"95v)H}Wa'",
                                  event_queue=queue, parent=None, thread_id=1, debug=True, song_skipping_chance=10)
    instance.login()
    instance.initialization()
    instance.listen_to_favorite_song_in_minimized_window()
    while not queue.empty():
        print(queue.get())
