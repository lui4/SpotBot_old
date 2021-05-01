import queue
import socket
import threading
from threading import Thread

from colorama import Fore
from proxy_checker import ProxyChecker as PC


class ProxyChecker:
    def __init__(self, proxies, proxy_max_timeout=10, threads=10):
        socket.setdefaulttimeout(proxy_max_timeout)
        self.proxies = proxies
        self.threads = threads
        self.queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.lock = threading.Lock()
        for proxy in proxies:
            self.queue.put(proxy)

    def check_proxy(self):
        while not self.queue.empty():
            proxy = self.queue.get()
            checked_proxy = PC().check_proxy(proxy)
            self.result_queue.put(
                {"proxy": proxy, "country_code": checked_proxy["country_code"] if checked_proxy else False})

    def start_check(self):
        threads = []
        for _ in range(self.threads):
            thread = Thread(target=self.check_proxy)
            thread.start()
            threads.append(thread)

        for t in threads:
            t.join()

        not_working_proxies = []
        while not self.result_queue.empty():
            item = self.result_queue.get()
            if not item["country_code"]:
                not_working_proxies.append(item["proxy"])
                print(f"{Fore.RED}[-] Proxy > {item['proxy'].strip()} not working")
            else:
                print(f"{Fore.GREEN}[+] Proxy > {item['proxy'].strip()} working")

        return not_working_proxies


if __name__ == '__main__':

    i = ProxyChecker(
        ["154.16.74.230:5432", "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231",
         "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231",
         "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231", "23342.2.23.2:231"])
    print(i.start_check())
