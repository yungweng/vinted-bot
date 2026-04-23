from curl_cffi import requests
from bs4 import BeautifulSoup

from vinted_bot.config import SCRAPER


class VintedBlocked(Exception):
    """Vinted returned 403 for every impersonation target — likely IP-based block."""


class VintedSession:
    def __init__(self):
        self.csrf_token = None
        self.impersonate = None
        self.session = None
        self._bootstrap()

    def _attempt_bootstrap(self, target):
        session = requests.Session(impersonate=target)
        r = session.get(
            SCRAPER["base_url"] + "/",
            headers={"Accept-Language": SCRAPER["accept_language"]},
            timeout=SCRAPER["request_timeout"],
        )
        r.raise_for_status()
        return session, r

    def _bootstrap(self):
        targets = [SCRAPER["impersonate"], *SCRAPER.get("impersonate_fallbacks", [])]
        last_error = None
        for target in targets:
            try:
                session, r = self._attempt_bootstrap(target)
            except Exception as e:
                last_error = e
                continue
            self.session = session
            self.impersonate = target
            soup = BeautifulSoup(r.text, "html.parser")
            tag = soup.find("meta", attrs={"name": "csrf-token"})
            if tag and tag.get("content"):
                self.csrf_token = tag["content"]
            return
        raise VintedBlocked(
            "Vinted hat alle Impersonation-Targets mit Fehler abgewiesen "
            f"(letzter: {last_error}). Das ist meistens ein IP-Block — probier "
            "ein VPN (z.B. ProtonVPN auf Deutschland) und starte neu."
        )

    def get(self, url, params=None):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": SCRAPER["accept_language"],
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
