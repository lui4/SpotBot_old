import random
import threading
import time

from colorama import Fore, init

init(autoreset=True)
lock = threading.Lock()


class LockedPrints:
    @staticmethod
    def locked_blue_print(msg):
        time.sleep(random.randint(0,2))
        lock.acquire()
        print(f"{Fore.BLUE}{msg}")
        lock.release()


class CommandLineStyling:
    @staticmethod
    def dotted_line(color, mul):
        print(f"{color}---" * mul)


if __name__ == '__main__':
    CommandLineStyling().dotted_line(Fore.RED, 30)
