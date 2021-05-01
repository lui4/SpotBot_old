import json
import sys

from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import QMainWindow, QApplication

from spotbot.ui_functions.console_utils import ConsolePage
from spotbot.ui_functions.ui_pages import *


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        uic.loadUi("./ui/ui_main.ui", self)

        with open("../config/settings_base_config.json")as f:
            self.settings_config = json.load(f)

        self.is_running = False  # this is used to check if the bot is used in any way
        self.threadpool = QThreadPool()
        self.showMaximized()

        header = self.streaming_accounts_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.streaming_accounts_table.horizontalHeader().show()
        self.artist_table.horizontalHeader().show()

        self.btn_toggle.clicked.connect(lambda: UIFunctions().toggle_menu(350, True, self))

        # PAGE 1
        SettingsPage().load_saved_settings(parent=self)

        self.settings_btn.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.settings_page))

        self.discord_webhook.textChanged.connect(lambda: SettingsPage().set_discord_webhook(parent=self))
        self.send_discord_after_finish.stateChanged.connect(
            lambda state: SettingsPage().set_send_discord_webhook_after_finish(parent=self, state=state))
        self.time_between_discord_webhooks.timeChanged.connect(
            lambda: SettingsPage().set_time_between_discord_notifications(parent=self))

        self.threads_per_core.valueChanged.connect(lambda: SettingsPage().set_threads_per_core(parent=self))

        self.thread_delay.valueChanged.connect(lambda: SettingsPage().set_thread_delay(parent=self))

        self.core_delay.valueChanged.connect(lambda: SettingsPage().set_core_delay(parent=self))

        self.allow_monitoring.stateChanged.connect(lambda state: SettingsPage().set_allow_monitoring(parent=self, state=state))

        self.check_proxies.stateChanged.connect(lambda state: SettingsPage().set_check_proxies(parent=self, state=state))
        self.proxy_checking_timeout.valueChanged.connect(lambda: SettingsPage().set_proxy_checking_timeout(parent=self))
        self.proxy_checking_threads.valueChanged.connect(lambda: SettingsPage().set_proxy_checking_threads(parent=self))

        # PAGE 2
        self.console_btn.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.console_page))
        self.console_table.setFont(QtGui.QFont('Arial', 20))

        ConsolePage(parent=self, thread_id=10).add_message(message="This is a test message", status="INFO")
        # PAGE 3
        self.spotify_bot_btn.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.spotify_bot_page))

        # PAGE 4
        self.account_page_btn.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.accounts_page))

        AccountPage().load_accounts(self)

        self.upload_streaming_accounts.clicked.connect(lambda: AccountPage().upload_streaming_accounts(self))

        self.upload_streaming_proxies.clicked.connect(lambda: AccountPage().upload_streaming_proxies(self))

        self.add_accounts.clicked.connect(lambda: AccountPage().add_accounts(self))

        self.delete_not_working_accounts.clicked.connect(lambda: AccountPage().delete_not_working_accounts(self))

        # PAGE 6

        ArtistsPage().update_artist_table_item(parent=self)
        ArtistsPage().update_artists_stats(parent=self)

        self.artists_button.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.artists_page))

        self.upload_botting_songs.clicked.connect(lambda: ArtistsPage().upload_botting_links(self))

        self.add_artist.clicked.connect(lambda: ArtistsPage().add_artist(parent=self))

        self.delete_artist.clicked.connect(lambda: ArtistsPage().delete_artist(parent=self))

        self.to_update_artist.textChanged.connect(lambda: ArtistsPage().update_artist_changed(parent=self))

        self.update_artist.clicked.connect(lambda: ArtistsPage().update_artist(parent=self))
        # PAGE 7
        self.session_btn.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.session_page))

        self.show()


if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    window = MainWindow()
    sys.exit(app.exec_())