import random

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QRunnable
from colorama import init, Fore
from pymongo import MongoClient

from spotbot.utils.proxy_checker import ProxyChecker
from spotbot.cookie_generator.cookie_gen import GenerateFootprint
from spotbot.utils.format import CommandLineStyling
from spotbot.utils.dbhelper import MongoDBHelper

init(autoreset=True)


class WorkerSignals(QObject):
    finished = pyqtSignal()
    created_account = pyqtSignal(dict)


class StreamingAccountCreator(QRunnable):
    """
    This class gets called when the bot starts and it assigns all the important stuff/options to the accounts and is
    immutable
    """

    def __init__(self, accounts, proxies, parent):
        super(StreamingAccountCreator, self).__init__()
        self.signals = WorkerSignals()

        client = MongoClient("localhost", 27017)
        db = client["SpotifyBot"]
        self.account_col = db["Accounts"]
        self.meta_col = db["MetaData"]
        self.proxies_col = db["Proxies"]
        self.configurations_document = db["Configurations"].find_one()
        del self.configurations_document["_id"]
        self.accounts = {account for account in accounts}
        self.proxies = {proxy for proxy in proxies}
        self.parent = parent
        self.accounts_per_proxy = self.parent.proxies_per_account.value()

    def account_exists_in_meta_col(self, account):
        """
        This method checks if the account is in the database and returns True if it is and False if not
        :param account: the account that should be checked
        :return: True or False
        """
        return True if self.meta_col.find_one({"account": account}) is not None else False

    def insert_meta_account(self, account, age, gender):
        """
        This method inserts a account into the database
        :return:
        """
        cookie_amount = random.randint(1, 39)
        query = {"account": account,
                 "proxy_uses": 1,
                 "age": age,
                 "gender": gender,
                 "cookies": cookie_amount,
                 "user_agent": self._generate_useragent(),
                 "favorite_song": self._generate_favorite_song(int(age), gender),
                 "change_profil_picture": self._generate_change_profil_picture(),
                 "change_account_username": self._generate_change_account_username(),
                 "only_play_embedded": self._generate_only_play_embedded(),
                 "listen_to_podcast": self._generate_listen_to_podcast(),
                 "incognito": self._generate_incognito(),
                 "account_plan": "",
                 "allow_earlier_stopping": True,  # let the user define this probability
                 "account_status": "Working",
                 }
        query["artists"] = self._generate_artists(query["only_play_embedded"])
        if query["artists"] is None:
            return False

        if not query["incognito"]:
            GenerateFootprint(cookie_amount, account.split(":")[0]).generate_footprint()

        self.meta_col.insert_one(query)
        return True

    def _generate_useragent(self):
        user_agent_to_pick = {}
        user_agent = []

        random_number = random.randint(1, 100)
        if random_number < self.parent.chance_to_run_mobile.value():
            user_agent_to_pick["use_mobile"] = True
        else:
            user_agent_to_pick["use_mobile"] = False

        random_number = random.randint(1, 100)
        if random_number < self.parent.chance_to_have_two_user_agents.value():
            user_agent_to_pick["two_user_agents"] = True
        else:
            user_agent_to_pick["two_user_agents"] = False

        if user_agent_to_pick["use_mobile"]:
            device = random.choice(list(self.configurations_document["user_agents"]["mobile_device"].keys()))

            user_agent.append(random.choice(self.configurations_document["user_agents"]["mobile_device"][device]))
        else:
            device = random.choice(list(self.configurations_document["user_agents"]["pc"].keys()))

            user_agent.append(random.choice(self.configurations_document["user_agents"]["pc"][device]))

        if user_agent_to_pick["two_user_agents"]:
            platform = random.choice(list(self.configurations_document["user_agents"].keys()))

            user_agent.append(random.choice(random.choice(platform)))

        return user_agent

    def _generate_favorite_song(self, age, gender):
        favorite_song_data = {}

        random_number = random.randint(1, 100)
        if random_number < self.parent.chance_no_favorite_song.value():
            return {"genre": None, "song": None}

        random_number = random.randint(1, 100)
        if random_number < self.parent.chance_no_favorite_song.value():
            return None

        random_number = random.randint(1, 100)
        if gender == "undefined" and random_number < 40:  # pick a random lgbtq song
            favorite_song_genre = "lgbtq"
            favorite_song_meta = random.choice(self.configurations_document["favorite_songs"][favorite_song_genre])

            favorite_song_data["song_name"] = favorite_song_meta["song"]
            favorite_song_data["artist_name"] = favorite_song_meta["artist_name"]

            return favorite_song_data

        random_number = random.randint(1, 100)
        if gender == "female" and random_number < 45:  # have a chance to listen to pop songs and other soft songs
            possible_genres = ["hip_hop", "k_pop", "rnb"]

            favorite_song_genre = random.choice(possible_genres)
            favorite_song_meta = random.choice(self.configurations_document["favorite_songs"][favorite_song_genre])

            favorite_song_data["song_name"] = favorite_song_meta["song"]
            favorite_song_data["song_artist"] = favorite_song_meta["artist_name"]

            return favorite_song_data

        random_number = random.randint(1, 100)
        if gender == "male" and random_number < 60:  # have a chance to listen to rap
            possible_genres = ["rap", "instrumental", "blues"]

            favorite_song_genre = random.choice(possible_genres)
            favorite_song_meta = random.choice(self.configurations_document["favorite_songs"][favorite_song_genre])

            favorite_song_data["song_name"] = favorite_song_meta["song"]
            favorite_song_data["song_artist"] = favorite_song_meta["artist_name"]

            return favorite_song_data

        random_number = random.randint(1, 100)
        if age > 30 and random_number < 25:
            possible_genres = ["50s", "60s", "70s", "80s", "90s", "2000s"]

            favorite_song_genre = random.choice(possible_genres)
            favorite_song_meta = random.choice(self.configurations_document["favorite_songs"][favorite_song_genre])

            favorite_song_data["song_name"] = favorite_song_meta["song"]
            favorite_song_data["song_artist"] = favorite_song_meta["artist_name"]

            return favorite_song_data

        if not favorite_song_data:
            favorite_song_genre = random.choice(list(self.configurations_document["favorite_songs"].keys()))
            favorite_song_meta = random.choice(self.configurations_document["favorite_songs"][favorite_song_genre])

            favorite_song_data["song_name"] = favorite_song_meta["song"]
            favorite_song_data["song_artist"] = favorite_song_meta["artist_name"]

        return favorite_song_data

    def _generate_change_profil_picture(self):
        chance_profile_picture = self.parent.chance_profile_picture.value()
        random_number = random.randint(1, 100)

        return False if random_number > chance_profile_picture else True

    def _generate_change_account_username(self):
        chance_change_username = self.parent.chance_change_username.value()
        random_number = random.randint(1, 100)

        return False if random_number > chance_change_username else True

    def _generate_only_play_embedded(self):
        only_listen_to_embedded_chance = self.parent.only_play_embedded.value()
        random_number = random.randint(1, 100)

        return False if random_number > only_listen_to_embedded_chance else True

    def _generate_listen_to_podcast(self):
        chance_to_listen_to_podcast = self.parent.chance_listen_to_podcast.value()
        random_number = random.randint(1, 100)

        return False if random_number > chance_to_listen_to_podcast else True

    def _generate_more_than_two_user_agents(self):
        two_useragents_chance = self.parent.chance_to_have_two_user_agents.value()
        random_number = random.randint(1, 100)

        return False if random_number > two_useragents_chance else True

    def _generate_incognito(self):
        incognito_chance = self.parent.incognito_chance.value()
        random_number = random.randint(1, 100)

        return False if random_number > incognito_chance else True

    def _generate_artists(self, only_play_embedded):
        artist_col = MongoDBHelper().db_connection["Artists"]
        account_col = MongoDBHelper().db_connection["MetaData"]
        artists = []

        if not artist_col.estimated_document_count():
            self.parent.add_accounts_error.setText("Please upload a artist before adding accounts")
            print("Upload a artist before adding accounts")
            return

        for artist in artist_col.find():
            if artist["current_accounts_to_use"] == 100:
                continue

            accounts_using_this_artist = len([account for account in account_col.find() if
                                              artist["artist_name"] in account["artists"] and account[
                                                  "account_status"] == "Working"])

            if int(account_col.estimated_document_count() / 100) * artist[
                "current_accounts_to_use"] <= accounts_using_this_artist:
                if accounts_using_this_artist >= artist["current_accounts_to_use"]:
                    continue

            if only_play_embedded and artist["allow_embedded"]:
                artists.append(artist["artist_name"])
                continue

            artists.append(artist["artist_name"])

        if not artists:
            self.parent.add_accounts_error.setText("No artist found to assign to this account")
            return

        return artists

    @pyqtSlot()
    def run(self):
        """
        This method is the main method of this class and will combine all methods and checks
        :return: None
        """
        if self.parent.check_proxies.isChecked():
            not_working_proxies = ProxyChecker(proxies=self.proxies,
                                               proxy_max_timeout=self.parent.settings_config["proxy_checking_timeout"],
                                               threads=self.parent.settings_config[
                                                   "proxy_checking_threads"]).start_check()
        else:
            not_working_proxies = []

        for index, account in enumerate(self.accounts):
            try:
                email, pwd, gender, age = account.strip().split(":")
            except ValueError:
                print(
                    f"{Fore.RED}[-] Account [{index + 1}/{len(self.accounts)}] > {account} is in the wrong format (user:pass:gender:age)")
                CommandLineStyling().dotted_line(Fore.YELLOW, 35)
                continue
            CommandLineStyling().dotted_line(Fore.YELLOW, 35)

            if ":" not in account:
                print(
                    f"[#] Account [{index + 1}/{len(self.accounts)}] > {email}:{pwd} is invalid or in the wrong format (email:pwd)")
                continue
            if self.account_col.find_one({"account": f"{email}:{pwd}"}) is not None:
                print(
                    f"[#] Account [{index + 1}/{len(self.accounts)}] > {email}:{pwd} is already registered in the database")
                continue

            available_proxies = [proxy for proxy in self.proxies if
                                 len([used_proxy for used_proxy in
                                      self.account_col.find({"proxy": proxy})]) <
                                 self.proxies_col.find_one({"proxy": proxy.strip()})[
                                     "max_proxy_accounts"] and proxy not in not_working_proxies]
            if not available_proxies:
                print(f"{Fore.GREEN}[#] Finished adding accounts")
                return
            if not self.account_exists_in_meta_col(f"{email}:{pwd}"):
                if not self.insert_meta_account(f"{email}:{pwd}", age, gender):
                    print(
                        f"{Fore.RED}[-] Account [{index + 1}/{len(self.accounts)}] > {email}:{pwd} No artist found to assign - skipping it")
                    continue
            else:
                old_proxy_uses = self.meta_col.find_one({"account": f"{email}:{pwd}"})["proxy_uses"]

                if old_proxy_uses + 1 > int(self.parent.max_proxy_uses.value()):
                    print(
                        f"{Fore.RED}[+] Account [{index + 1}/{len(self.accounts)}] > {email}:{pwd} exceeded the max proxy uses of {self.parent.max_proxy_uses.value()} - not using it")
                    continue

                self.meta_col.update_one({"account": f"{email}:{pwd}"}, {"$set": {"proxy_uses": old_proxy_uses + 1}})

            proxy = random.choice(available_proxies)
            self.account_col.insert_one({"account": f"{email}:{pwd}", "proxy": proxy.strip()})

            print(f"{Fore.GREEN}[+] Account [{index + 1}/{len(self.accounts)}] > {email}:{pwd} added to the database")
            self.signals.created_account.emit({"account": account, "proxy": proxy,
                                               "user_agent": self.meta_col.find_one({"account": f"{email}:{pwd}"})[
                                                   "user_agent"]})

        print(f"{Fore.GREEN}[#] Finished adding accounts")
        self.signals.finished.emit()
