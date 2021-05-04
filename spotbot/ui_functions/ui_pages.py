import json
import multiprocessing
import os
import random

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QPropertyAnimation, QTime
from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog
from colorama import Fore
from pymongo import MongoClient
import undetected_chromedriver as uc


from spotbot.ui_functions.streaming_account_functions import StreamingAccountCreator
from spotbot.utils.format import CommandLineStyling
import operator
from spotbot.ui_main import *


class UIFunctions(MainWindow):
    def toggle_menu(self, max_width, enable, parent):
        if enable:
            width = parent.frame_left_menu.width()
            max_extend = max_width
            standard = 120

            if width == 120:
                width_extended = max_extend
            else:
                width_extended = standard

            self.animation = QPropertyAnimation(self.frame_left_menu, b"minimumWidth")
            self.animation.setDuration(400)
            self.animation.setStartValue(width)
            self.animation.setEndValue(width_extended)
            self.animation.start()


class SettingsPage:
    @staticmethod
    def load_saved_settings(parent):
        parent.send_discord_after_finish.setChecked(parent.settings_config["send_webhook_after_finish"])

        discord_sleeping_minutes = int(
            round(int(parent.settings_config["time_between_discord_notifications"]) / 1000 / 60))

        if discord_sleeping_minutes > 60:
            discord_sleeping_hours = discord_sleeping_minutes / 60
            minutes = discord_sleeping_minutes % 60
            time = QTime()
            time.setHMS(discord_sleeping_hours, minutes, 0)
            parent.time_between_discord_webhooks.setTime(time)
        else:
            time = QTime()
            time.setHMS(0, discord_sleeping_minutes, 0)
            parent.time_between_discord_webhooks.setTime(time)

        if parent.settings_config["discord_webhook"] == "":
            parent.selected_discord_webhook.setText("Current selected discord webhook to notify: None")
        else:
            parent.selected_discord_webhook.setText(
                f"Current selected discord webhook to notify: {parent.settings_config['discord_webhook']}")

        parent.threads_per_core.setValue(parent.settings_config["threads_per_core"])

        parent.thread_delay.setValue(parent.settings_config["thread_delay"])

        parent.core_delay.setValue(parent.settings_config["core_delay"])

        parent.allow_monitoring.setChecked(parent.settings_config["allow_monitoring"])

        parent.check_proxies.setChecked(parent.settings_config["check_proxies"])

        parent.proxy_checking_threads.setValue(parent.settings_config["proxy_checking_threads"])

        parent.proxy_checking_timeout.setValue(parent.settings_config["proxy_checking_timeout"])

    @staticmethod
    def set_discord_webhook(parent):
        lineedit_value = parent.discord_webhook.text()
        parent.selected_discord_webhook.setWordWrap(True)
        parent.selected_discord_webhook.setText(f"Current selected webhook: {lineedit_value}")

        parent.settings_config["discord_webhook"] = lineedit_value

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_time_between_discord_notifications(parent):
        timeedit_value = parent.time_between_discord_webhooks.time()
        hour = timeedit_value.hour()
        minute = timeedit_value.minute()
        total_ms = 0

        if minute != 0:
            total_ms += minute * 60 * 1000

        if hour != 0:
            total_ms += hour * 60 * 60 * 1000

        parent.settings_config["time_between_discord_notifications"] = total_ms

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_send_discord_webhook_after_finish(parent, state):
        if state == QtCore.Qt.Checked:
            parent.settings_config["send_webhook_after_finish"] = True
        else:
            parent.settings_config["send_webhook_after_finish"] = False

    @staticmethod
    def set_threads_per_core(parent):
        spinbox_value = parent.threads_per_core.value()

        parent.settings_config["threads_per_core"] = spinbox_value

        parent.account_genning_thread_amount.setMaximum(
            parent.settings_config["threads_per_core"] * multiprocessing.cpu_count())
        parent.account_genning_thread_amount.setMinimum(spinbox_value)

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_thread_delay(parent):
        spinbox_value = parent.thread_delay.value()

        parent.settings_config["thread_delay"] = spinbox_value

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_core_delay(parent):
        spinbox_value = parent.core_delay.value()

        parent.settings_config["core_delay"] = spinbox_value

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_allow_monitoring(parent, state):
        if state == QtCore.Qt.Checked:
            parent.settings_config["allow_monitoring"] = True
        else:
            parent.settings_config["allow_monitoring"] = False

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_check_proxies(parent, state):
        if state == QtCore.Qt.Checked:
            parent.settings_config["check_proxies"] = True
            parent.proxy_checking_threads.setEnabled(True)
            parent.proxy_checking_timeout.setEnabled(True)
        else:
            parent.settings_config["check_proxies"] = False
            parent.proxy_checking_threads.setEnabled(False)
            parent.proxy_checking_timeout.setEnabled(False)

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_proxy_checking_timeout(parent):
        spinbox_value = parent.proxy_checking_timeout.value()

        parent.settings_config["proxy_checking_timeout"] = spinbox_value

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)

    @staticmethod
    def set_proxy_checking_threads(parent):
        spinbox_value = parent.proxy_checking_threads.value()

        parent.settings_config["proxy_checking_threads"] = spinbox_value

        with open("./dependencies/settings_base_config.json", "w")as f:
            json.dump(parent.settings_config, f, indent=4)


class AccountPage:
    ACCOUNTS = []
    PROXIES = []

    @property
    def account_database_connection(self):
        client = MongoClient("localhost", 27017)
        database = client["SpotifyBot"]
        return database["Accounts"], database["MetaData"], database["Proxies"]

    def update_added_accounts_stats(self, parent):
        account_col, meta_col, _ = self.account_database_connection
        total_accounts = account_col.estimated_document_count()
        working_accounts = len([working_account for working_account in meta_col.find() if meta_col.find_one({"account": working_account["account"]})["account_status"] == "Working"])
        not_working_accounts = len([not_working_account for not_working_account in meta_col.find() if meta_col.find_one({"account": not_working_account["account"]})["account_status"] == "Not Working" and account_col.find_one({"account": not_working_account["account"]}) is not None])

        parent.total_accounts.setText(f"Total loaded accounts: {total_accounts}")
        parent.total_working_accounts.setText(f"Total working accounts: {working_accounts}/{total_accounts}")
        parent.total_not_working_accounts.setText(f"Total not working accounts: {not_working_accounts}/{total_accounts}")

    def load_accounts(self, parent):
        account_col, meta_col, _ = self.account_database_connection

        for document in meta_col.find():
            if account_col.find_one({"account": document["account"]}) is None:
                continue

            row_position = parent.streaming_accounts_table.rowCount()
            parent.streaming_accounts_table.setColumnCount(5)
            parent.streaming_accounts_table.insertRow(row_position)

            email, password = document["account"].split(":", 1)
            parent.streaming_accounts_table.setItem(row_position, 0, QTableWidgetItem(email))
            parent.streaming_accounts_table.setItem(row_position, 1, QTableWidgetItem(password))
            parent.streaming_accounts_table.setItem(row_position, 2, QTableWidgetItem(account_col.find_one({"account": document["account"]})["proxy"]))
            parent.streaming_accounts_table.setItem(row_position, 3, QTableWidgetItem(document["user_agent"]["user_agent"]))
            parent.streaming_accounts_table.setItem(row_position, 4, QTableWidgetItem(""))
            status = document["account_status"]

            if status == "Working":
                parent.streaming_accounts_table.item(row_position, 4).setBackground(QtGui.QColor(12, 168, 12))
            else:
                parent.streaming_accounts_table.item(row_position, 4).setBackground(QtGui.QColor(237, 12, 12))
            self.update_added_accounts_stats(parent)

    @staticmethod
    def upload_streaming_accounts(parent):
        dialog = QFileDialog()
        streaming_accounts_path = dialog.getOpenFileName(None, "Import TEXT", "", "TEXT Streaming Accounts (*.txt)")

        if streaming_accounts_path[0] == "":
            return

        with open(streaming_accounts_path[0], "r")as file:
            accounts = [account for account in file.readlines() if "@" in account]

            if not accounts:
                parent.add_accounts_error.setText(
                    f"The file {os.path.basename(streaming_accounts_path[0])} doesn't contain accounts")
                return
        parent.add_accounts_error.setText(f"Loaded accounts: {os.path.basename(streaming_accounts_path[0])}")
        AccountPage.ACCOUNTS = [*AccountPage.ACCOUNTS, *accounts]

    def upload_streaming_proxies(self, parent):
        dialog = QFileDialog()
        streaming_proxies_path = dialog.getOpenFileName(None, "Import TEXT", "", "TEXT Streaming Proxies (*.txt)")

        if streaming_proxies_path[0] == "":
            return

        with open(streaming_proxies_path[0], "r")as file:
            proxies = [proxy for proxy in file.readlines() if ":" and "." in proxy]

            if not proxies:
                parent.add_accounts_error.setText(
                    f"The file {os.path.basename(streaming_proxies_path[0])} doesn't contain proxies")
                return
            parent.add_accounts_error.setText(f"Loaded Proxies: {os.path.basename(streaming_proxies_path[0])}")
            AccountPage.PROXIES = [*AccountPage.PROXIES, *proxies]
            self._add_proxies(parent)

    def _add_proxies(self, parent):
        account_col, meta_col, proxies_col = self.account_database_connection
        already_added_proxies = [proxy for proxy in proxies_col.find()]

        for proxy in AccountPage.PROXIES:
            if proxy in already_added_proxies:
                continue

            max_proxy_accounts = random.randint(parent.proxies_per_account.value() - random.randint(0,2), parent.proxies_per_account.value() + random.randint(0, 2))

            proxies_col.insert_one({"proxy": proxy.strip(), "max_proxy_accounts": max_proxy_accounts})
            already_added_proxies.append(proxy)

    def add_accounts(self, parent):
        if len(self.PROXIES) == 0 or len(self.ACCOUNTS) == 0:
            parent.add_accounts_error.setText("Please provide proxies and accounts before adding")
            return

        print(f"{Fore.BLUE}[#] Account adding process started")

        worker = StreamingAccountCreator(accounts=self.ACCOUNTS, proxies=self.PROXIES,
                                         parent=parent)
        worker.signals.created_account.connect(lambda result: self._add_account_to_table(result, parent))
        worker.signals.finished.connect(lambda: parent.add_accounts_error.setText("Added all accounts"))
        parent.threadpool.start(worker)

        AccountPage.PROXIES.clear()
        AccountPage.ACCOUNTS.clear()
        self.update_added_accounts_stats(parent)

    def _add_account_to_table(self, result, parent):
        account = result["account"]
        proxy = result["proxy"]
        user_agent = result["user_agent"]

        parent.add_accounts_error.setText("Assigning started")
        email, password, _, _ = account.split(":")
        row_position = parent.streaming_accounts_table.rowCount()
        parent.streaming_accounts_table.setColumnCount(5)
        parent.streaming_accounts_table.insertRow(row_position)
        parent.streaming_accounts_table.setItem(row_position, 0, QTableWidgetItem(email))
        parent.streaming_accounts_table.setItem(row_position, 1, QTableWidgetItem(password))
        parent.streaming_accounts_table.setItem(row_position, 2, QTableWidgetItem(proxy))
        parent.streaming_accounts_table.setItem(row_position, 3, QTableWidgetItem(user_agent[0]))
        parent.streaming_accounts_table.setItem(row_position, 4, QTableWidgetItem(""))
        parent.streaming_accounts_table.item(row_position, 4).setBackground(QtGui.QColor(12, 168, 12))

        self.update_added_accounts_stats(parent)

    def delete_not_working_accounts(self, parent):
        account_col, meta_col, _ = self.account_database_connection

        for i, account_document in reversed(list(enumerate(account_col.find()))):
            if not meta_col.find_one({'account': account_document['account']})["account_status"] == "Working":
                print(f"[#] Account > {account_document['account']} removed from database")
                parent.streaming_accounts_table.removeRow(i)
                account_col.delete_one({"account": account_document["account"]})

                self.update_added_accounts_stats(parent)


class ArtistsPage:
    BOTTING_LINKS = None
    ARTIST = {}

    @property
    def artists_database_connection(self):
        client = MongoClient("localhost", 27017)
        database = client["SpotifyBot"]
        return database["Artists"]

    @staticmethod
    def _lowest_highest_streams(artist_col, highest_lowest):
        opr = operator.le if highest_lowest == -1 else operator.ge
        last_lowest_value = {"streams": 0, "artist": ""}
        for artist in artist_col.find():
            if opr(artist["streams"], last_lowest_value["streams"]):
                last_lowest_value["streams"] = artist["streams"]
                last_lowest_value["artist"] = artist["artist_name"]
        return last_lowest_value

    @staticmethod
    def _lowest_highest_followers(artist_col, highest_lowest):
        opr = operator.lt if highest_lowest == -1 else operator.gt
        last_lowest_value = {"follows": 0, "artist": ""}
        for artist in artist_col.find():
            if opr(artist["follows"], last_lowest_value["follows"]) or artist["follows"] == 0:
                last_lowest_value["follows"] = artist["follows"]
                last_lowest_value["artist"] = artist["artist_name"]
        return last_lowest_value

    def update_artists_stats(self, parent):
        artist_col = self.artists_database_connection
        total_artists = artist_col.estimated_document_count()
        parent.total_artists.setText(f"Your total artists: {total_artists}")

        parent.total_artists_streams.setText(f"Total botted streams on all artists: {sum([doc['streams'] for doc in artist_col.find()])}")

        highest_artist = self._lowest_highest_streams(artist_col, 1)
        parent.artists_most_streams.setText(
            f"Artist with the most streams: {highest_artist['artist']} -> {highest_artist['streams']}")

        lowest_artist = self._lowest_highest_streams(artist_col, -1)
        parent.artist_least_streams.setText(
            f"Artist with the least streams: {lowest_artist['artist']} -> {lowest_artist['streams']}")

        parent.total_botted_followers.setText(f"Your total botted followers: {sum([doc['follows'] for doc in artist_col.find()])}")

        highest_follows = self._lowest_highest_followers(artist_col, 1)
        parent.highest_artist_followers.setText(
            f"Artist with the most amount of followers: {highest_follows['artist']} -> {highest_follows['follows']}")

        lowest_follows = self._lowest_highest_followers(artist_col, -1)
        parent.lowest_artist_follower.setText(
            f"Artist with the least amount of followers: {lowest_follows['artist']} -> {lowest_follows['follows']}")

    @staticmethod
    def _setup_basic_driver():
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        return uc.Chrome(executable_path="C:/Users/luis/PycharmProjects/spotbot/driver/chromedriver/chromedriver_89.exe", options=options)

    def upload_botting_links(self, parent):
        from spotbot.ui_functions.artist_checker import ArtistInterpreter
        dialog = QFileDialog()
        botting_links_path = dialog.getOpenFileName(None, "Import TEXT", "", "TEXT Artist Songs (*.txt)")

        if botting_links_path[0] == "":
            return

        CommandLineStyling().dotted_line(Fore.YELLOW, 35)
        print(f"{Fore.BLUE}[#] Starting loading/checking your songs/embeds/albums [#]")

        with open(botting_links_path[0])as f:
            elements = list(map(lambda sentence: sentence.replace("\n", ""), f.read().split(";")))

        worker = ArtistInterpreter(parent, elements, self._setup_basic_driver())
        parent.threadpool.start(worker)

    def _is_artist_link_valid(self, artist_name, valid, parent, artist_link):
        artists_col = self.artists_database_connection
        if not valid:
            parent.artist_error.setText("The link to your artist is invalid")
            return

        if artists_col.find_one({"artist_name": artist_name}) is not None:
            parent.artist_error.setText(f"Artist already exists: {artist_name}")
            return

        ArtistsPage.ARTIST["artist_name"] = artist_name
        botting_links = self.BOTTING_LINKS.copy()

        try:
            _ = ArtistsPage.ARTIST["artist_name"]
        except KeyError:
            print("KEY ERROR")
            return

        best_song = parent.favorite_artists_song.currentText()

        if not best_song:
            parent.artist_error.setText("Please provide a file containing the artist songs")
            return

        ArtistsPage.ARTIST["link_to_artist"] = artist_link
        ArtistsPage.ARTIST["follows"] = 0
        ArtistsPage.ARTIST["streams"] = 0
        ArtistsPage.ARTIST["allow_embedded"] = True if parent.allow_embedded_on_artist.isChecked() else False
        ArtistsPage.ARTIST["account_starting_amount"] = int(parent.account_starting_amount.value())
        ArtistsPage.ARTIST["current_accounts_to_use"] = ArtistsPage.ARTIST["account_starting_amount"]
        ArtistsPage.ARTIST["growthrate_per_day"] = 0 if ArtistsPage.ARTIST["account_starting_amount"] == 100 else int(parent.artist_growthrate.value())
        ArtistsPage.ARTIST["artist_botting_links"] = botting_links
        ArtistsPage.ARTIST["best_song"] = best_song
        artists_col.insert_one(ArtistsPage.ARTIST)

        parent.artist_error.setStyleSheet("color: green;")
        parent.artist_error.setText(f"Added the artist {ArtistsPage.ARTIST['artist_name']}")

        print(f"{Fore.GREEN}[#] Successfully added the artist {ArtistsPage.ARTIST['artist_name']}")
        self.update_artist_table_item(parent)

        ArtistsPage.BOTTING_LINKS.clear()
        ArtistsPage.ARTIST.clear()

        self.update_artists_stats(parent)

    def update_artist_table_item(self, parent):
        artist_col = self.artists_database_connection

        parent.artist_table.setRowCount(0)

        for index, artist in enumerate(artist_col.find()):
            parent.artist_table.insertRow(index)
            artist_name_item = QTableWidgetItem(artist["artist_name"])
            artist_name_item.setBackground(QtGui.QColor(45, 45, 45))

            growthrate_per_day_item = QTableWidgetItem(f"{artist['growthrate_per_day']}%")
            growthrate_per_day_item.setBackground(QtGui.QColor(45, 45, 45))

            accounts_to_use_item = QTableWidgetItem(f"{artist['current_accounts_to_use']}%")
            accounts_to_use_item.setBackground(QtGui.QColor(45, 45, 45))

            best_song_item = QTableWidgetItem(artist["best_song"])
            best_song_item.setBackground(QtGui.QColor(45, 45, 45))

            streams_item = QTableWidgetItem(str(artist["streams"]))
            streams_item.setBackground(QtGui.QColor(45, 45, 45))

            parent.artist_table.setItem(index, 0, artist_name_item)
            parent.artist_table.setItem(index, 1, growthrate_per_day_item)
            parent.artist_table.setItem(index, 2, accounts_to_use_item)
            parent.artist_table.setItem(index, 3, best_song_item)
            parent.artist_table.setItem(index, 4, streams_item)

    def add_artist(self, parent):
        from spotbot.ui_functions.artist_checker import ArtistNameGetter
        artist_link = parent.artist_link.text()

        if not artist_link:
            parent.artist_error.setText("Please provide a link to your artist")
            return

        if not self.BOTTING_LINKS:
            parent.artist_error.setText("Please upload the artists single songs/embeds/albums")
            return

        driver = self._setup_basic_driver()

        worker = ArtistNameGetter(driver, artist_link)
        worker.signals.result.connect(lambda msg: self._is_artist_link_valid(msg["artist_name"], msg["valid"], parent, artist_link))
        parent.threadpool.start(worker)

    def delete_artist(self, parent):
        artist = parent.to_delete_artist.text()
        artist_col = self.artists_database_connection

        if artist_col.find_one({"artist_name": artist}) is not None or artist_col.find_one({"link": artist}) is not None:
            artist_col.delete_one({"artist_name": artist})
            artist_col.delete_one({"link": artist})
            parent.artist_error.setStyleSheet("color: green;")
            parent.artist_error.setText(f"Deleted the artist: {artist}")
            self.update_artist_table_item(parent)
        else:
            parent.artist_error.setStyleSheet("color: red;")
            parent.artist_error.setText(f"Artist can't be deleted: {artist}")

    def update_artist_changed(self, parent):
        artist = parent.to_update_artist.text()
        artist_col = self.artists_database_connection

        selected_artist_doc = artist_col.find_one({"artist_name": artist})
        if selected_artist_doc is None:
            return

        for item in selected_artist_doc["artist_botting_links"]["single_songs"]:
            parent.best_song_update.addItem(item)

        parent.allow_embedded_on_artist_update.setChecked(selected_artist_doc["allow_embedded"])

    def update_artist(self, parent):
        best_song = parent.best_song_update.currentText()
        artist_name = parent.to_update_artist.text()
        artist_col = self.artists_database_connection

        selected_artist_doc = artist_col.find_one({"artist_name": artist_name})
        if selected_artist_doc is None:
            parent.artist_error.setStyleSheet("color: red;")
            parent.artist_error.setText(f"Can't update the artist: {artist_name}")
            return

        if not best_song:
            parent.artist_error.setStyleSheet("color: red;")
            parent.artist_error.setText(f"Please enter a valid artist to update")
            return

        artist_col.update_one({"artist_name": artist_name},{"$set": {"best_song": best_song, "allow_embedded": parent.allow_embedded_on_artist_update.isChecked()}})
        parent.artist_error.setStyleSheet("color: green;")
        parent.artist_error.setText(f"Successfully updated the artist: {artist_name}")
        self.update_artist_table_item(parent)


class SpotifyBotPage:
    pass
