import json
import os

from pymongo import MongoClient


class MongoDBHelper:
    @property
    def db_connection(self, col_name="SpotifyBot"):
        client = MongoClient("localhost", 27017)
        return client[col_name]

    @property
    def configurations(self):
        return self.db_connection["Configurations"]

    def account_data(self, account):
        return self.db_connection["MetaData"].find_one({"account": account}), self.db_connection["Accounts"].find_one(
            {"account": account})

    def set_account_meta_data(self, new_account_object):
        self.db_connection["MetaData"].update_one({"account": new_account_object["account"]},{"$set":  new_account_object})

    def artist_data(self, artist_name):
        return self.db_connection["Artists"].find_one({"artist_name": artist_name})


class SqlliteDBHelper:
    @staticmethod
    def get_account_data(account):
        pass


class SettingsHelper:
    @staticmethod
    def get_settings():
        with open("settings.json")as file:
            return json.load(file)
