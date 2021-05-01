from PyQt5.QtCore import QRunnable, pyqtSlot, pyqtSignal, QObject
from colorama import Fore
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from spotbot.utils.format import CommandLineStyling

from spotbot.ui_functions.ui_pages import ArtistsPage


class ArtistInterpreter(QRunnable):
    def __init__(self, parent, elements, driver):
        super(ArtistInterpreter, self).__init__()
        self.parent = parent
        self.elements = elements
        self.driver = driver

    @staticmethod
    def _check_embedded_link(driver, embedded_link):
        print(f"{Fore.BLUE}[#] Embedded link checking process started")
        try:
            driver.get(embedded_link)
            WebDriverWait(driver, 10).until(
                ec.presence_of_element_located((By.XPATH, "//div[@class='b4 ah b7']")))
            print(f"{Fore.GREEN}[#] Embedded link is valid: {embedded_link}")
            return True
        except Exception:
            print(f"{Fore.RED}[#] Embedded link invalid: {embedded_link}")
            return False

    @staticmethod
    def _check_single_song_link(driver, single_song_link):
        print(f"{Fore.BLUE}[#] Single song link checking process started")
        try:
            driver.get(single_song_link)
            WebDriverWait(driver, 10).until(
                ec.presence_of_element_located((By.XPATH, "//div[@data-testid='tracklist-row' and @draggable='true']")))
            WebDriverWait(driver, 10).until(
                ec.presence_of_element_located((By.XPATH, "//div[@class='faffb409617fd7cf35017fde898cf860-scss']")))

            print(f"{Fore.GREEN}[+] Single Song link is valid: {single_song_link}")
            return True
        except Exception:
            print(f"{Fore.RED}[-] Single Song link is valid: {single_song_link}")
            return False

    @staticmethod
    def _check_album_link(driver, album_link, extract_single_album_links):
        print(f"{Fore.BLUE}[#] Album checking process started")
        try:
            driver.get(album_link)
            WebDriverWait(driver, 10).until(
                ec.presence_of_element_located((By.XPATH, "//div[@data-testid='tracklist-row' and @draggable='true']")))

            tracks = driver.find_elements_by_xpath("//div[@data-testid='tracklist-row' and @draggable='true']")

            if len(tracks) < 2:
                print(
                    f"{Fore.RED}[-] Album/Playlist/Ep link is invalid (has to contain at least 2 songs): {album_link}")
                return False

            extracted_tracks = []
            if extract_single_album_links:
                for index, track in enumerate(tracks):
                    track = track.text.splitlines()[1]
                    print(
                        f"{Fore.GREEN}[+] [{index}] Extracted the single song {track} from your album: {'https://open.spotify.com/album/3pLdWdkj83EYfDN6H2N8MR'}")
                    extracted_tracks.append(track)
            print(f"{Fore.GREEN}[+] Album link is valid: {album_link}")
            return extracted_tracks, True
        except Exception:
            print(f"{Fore.RED}[-] Cannot find your album with the link: {album_link}")
            return [], False

    @pyqtSlot()
    def run(self):
        artist_botting_links = {
            "single_songs": [],
            "embeds": [],
            "albums": [],
        }

        for element in self.elements:
            if element.startswith("song:::"):
                single_song_link = element.split(":::")[1]
                if self.parent.check_artist_before_adding.isChecked() and single_song_link.startswith("http"):
                    if not self._check_single_song_link(self.driver, single_song_link):
                        continue
                artist_botting_links["single_songs"].append(single_song_link)
            elif element.startswith("embed:::"):
                embedded_link = element.split(":::")[1]
                if self.parent.check_artist_before_adding.isChecked() and embedded_link.startswith("http"):
                    if not self._check_embedded_link(self.driver, embedded_link):
                        continue
                artist_botting_links["embeds"].append(embedded_link)
            elif element.startswith("album:::"):
                album_botting_link = element.split(":::")[1]
                if self.parent.check_artist_before_adding.isChecked() and album_botting_link.startswith("http"):
                    extracted_songs, works = self._check_album_link(self.driver, album_botting_link,
                                                                    self.parent.add_album_song_to_single_songs.isChecked())
                    if not works:
                        continue
                else:
                    extracted_songs = []
                if extracted_songs:
                    artist_botting_links["single_songs"] = [*artist_botting_links["single_songs"], *extracted_songs]
                artist_botting_links["albums"].append(album_botting_link)
            else:
                if element != "":
                    print(f"{Fore.RED}[-] Botting Link: {element} is in the wrong format")

        for link in sorted(artist_botting_links["single_songs"]):
            self.parent.favorite_artists_song.addItem(link)
        ArtistsPage.BOTTING_LINKS = artist_botting_links
        self.parent.favorite_artists_song.setCurrentText(artist_botting_links["single_songs"][::-1][0])

        self.driver.quit()

        print(f"{Fore.BLUE}[#] Finished loading/checking your songs/embeds/albums [#]")
        CommandLineStyling().dotted_line(Fore.YELLOW, 35)


class WorkerSignals(QObject):
    result = pyqtSignal(dict)


class ArtistNameGetter(QRunnable):
    def __init__(self, driver, artist_link):
        super(ArtistNameGetter, self).__init__()
        self.driver = driver
        self.artist_link = artist_link
        self.signals = WorkerSignals()

    def check_artist_link(self, link):
        print(f"{Fore.BLUE}[#] Checking the artist: {link}")
        try:
            self.driver.get(link)
            x = WebDriverWait(self.driver, 10).until(
                ec.presence_of_element_located((By.XPATH, "//h1[@class='a12b67e576d73f97c44f1f37026223c4-scss']")))
            print(f"{Fore.GREEN}[#] Found your artist with the name: {x.text}")
            return x.text, True
        except Exception:
            print(f"{Fore.RED}[#] Cannot find your artist with the link: {link}")
            return "", False

    @pyqtSlot()
    def run(self):
        artist_name, valid = self.check_artist_link(self.artist_link)
        self.signals.result.emit({"artist_name": artist_name, "valid": valid})
        self.driver.quit()
