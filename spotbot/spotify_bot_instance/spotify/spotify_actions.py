import math

from spotbot.spotify_bot_instance.seleniumwrapper import SeleniumHelper


class SpotifyActions(SeleniumHelper):
    __slots__ = ['driver', 'mobile']

    def __init__(self, driver, mobile):
        super().__init__(driver=driver, mobile=mobile)

    @property
    def current_playing_song(self):
        """Returns the name of the current playing song"""
        return super().find_element_by_xpath("//a[@data-testid='nowplaying-track-link']").text

    @property
    def current_playing_artist(self):
        """Returns the name of the current playing artist"""
        return super().find_element_by_xpath("//a[@data-testid='nowplaying-artist']").text

    @property
    def current_playback_total_seconds(self):
        """Calculates the total seconds of playltime of the current playing track without respect to the lost time"""
        total_time = super().find_element_by_xpath("//div[@data-testid='playback-duration']").text.split(":")
        return int(total_time[0]) * 60 + int(total_time[1])

    @property
    def current_playback_played_seconds(self):
        """Calculates the already listened seconds of a song"""
        lost_time = super().find_element_by_xpath("//div[@data-testid='playback-position']").text.split(":")
        return int(lost_time[0]) * 60 + int(lost_time[1])

    def skip_song(self):
        song_skip_element = super().find_element_by_xpath("//button[@data-testid='control-button-skip-forward']")
        super().click(element=song_skip_element)

    def previous_song(self):
        if self.current_playback_played_seconds < 3:
            return

        song_previous_element = super().find_element_by_xpath("//button[@data-testid='control-button-shuffle']")
        if song_previous_element is None:
            return False
        super().click(element=song_previous_element)
        return True

    def stop_playback(self):
        playback_btn = super().find_element_by_xpath("//button[@data-testid='control-button-play']")
        if playback_btn is not None:
            super().click(element=playback_btn)
            return True
        return False

    def continue_playback(self):
        playback_btn = super().find_element_by_xpath("//button[@data-testid='control-button-pause']")
        if playback_btn is not None:
            super().click(element=playback_btn)
            return True
        return False

    def connect_to_device(self):
        device_actions = super().find_element_by_xpath(f"//span[@class='connect-device-picker']//button")

        if device_actions is None:
            return False

        super().click(element=device_actions)
        device_to_pick = super().find_element_by_xpath("//button[@class='media connect-device-list-item']")

        if device_to_pick is None:
            return False

        super().click(element=device_to_pick)

        return True

    def activate_shuffle(self):
        shuffle_element = super().find_element_by_xpath("//button[@data-testid='control-button-shuffle']")

        if shuffle_element.get_attribute('aria-checked') == "true" or shuffle_element is None:
            return False

        super().click(element=shuffle_element)

        return True

    def deactivate_shuffle(self):
        shuffle_element = super().find_element_by_xpath("//button[@data-testid='control-button-shuffle']")

        if shuffle_element.get_attribute('aria-checked') != "true" or shuffle_element is None:
            return False

        super().click(element=shuffle_element)

        return True

