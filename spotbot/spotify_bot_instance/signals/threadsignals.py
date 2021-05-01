from enum import Enum, auto


class ThreadSignals(Enum):
    STOPPED_EARLIER = auto()
    CREATED_PLAYLIST = auto()
    FATAL_ERROR = auto()
    ERROR = auto()
    STREAM_GAINED = auto()
    EMBEDDED_STREAM_GAINED = auto()
    FOLLOWED_TARGET_ARTIST = auto()
    FOLLOWED_RANDOM_ARTIST = auto()
    FOLLOWED_PLAYLIST = auto()
    ADDED_SONG_TO_PLAYLIST = auto()
    LIKED_SONG = auto()
    FAILED_LOGIN = auto()
    GAINED_LOGIN = auto()
    LISTENED_TO_AD = auto()
    SKIPPED_SONG = auto()