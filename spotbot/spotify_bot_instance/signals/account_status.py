from enum import Enum, auto


class AccountStatus(Enum):
    """This class is used to define signals and states for the accounts"""
    LOGGED_IN = auto()  # defines the state "logged in" for a account
    NOT_LOGGED_IN = auto()  # defines the state "not logged in" for a account
    ACCOUNT_DETAILS_WRONG = auto()  # defines the state "account details wrong in" for a account
    PROXY_ERROR = auto()
