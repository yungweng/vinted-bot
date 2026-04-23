from curl_cffi import requests
from bs4 import BeautifulSoup

from config import SCRAPER


class VintedSession:
    def __init__(self):
        self.session = requests.Session(impersonate=SCRAPER["impersonate"])
        self.csrf_token = None
        self._bootstrap()

    def _bootstrap(self):
        r = self.session.get(
            SCRAPER["base_url"] + "/",
            timeout=SCRAPER["request_timeout"],
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        tag = soup.find("meta", attrs={"name": "csrf-token"})
        if tag and tag.get("content"):
            self.csrf_token = tag["content"]

    def get(self, url, params=None):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": SCRAPER["base_url"] + "/",
        }
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        r = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=SCRAPER["request_timeout"],
        )
        r.raise_for_status()
        return r
