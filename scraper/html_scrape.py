import re

from bs4 import BeautifulSoup

from config import SCRAPER


def fetch_item_page(session, item_url):
    r = session.session.get(
        item_url,
        timeout=SCRAPER["request_timeout"],
        headers={"Referer": SCRAPER["base_url"] + "/"},
    )
    r.raise_for_status()
    return r.text


def extract_description(html):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []

    og = soup.find("meta", attrs={"property": "og:description"})
    if og and og.get("content"):
        candidates.append(og["content"].strip())

    for attrs in (
        {"itemprop": "description"},
        {"data-testid": "item-description-content"},
        {"data-testid": "description"},
    ):
        el = soup.find(attrs=attrs)
        if el:
            text = el.get_text("\n", strip=True)
            if text:
                candidates.append(text)

    for script in soup.find_all("script"):
        raw = script.string or script.get_text() or ""
        if '"description"' not in raw:
            continue
        for m in re.finditer(r'"description"\s*:\s*"((?:\\.|[^"\\])*)"', raw):
            try:
                text = bytes(m.group(1), "utf-8").decode("unicode_escape", errors="replace")
            except Exception:
                text = m.group(1)
            text = text.strip()
            if text:
                candidates.append(text)

    if not candidates:
        return ""

    candidates.sort(key=len, reverse=True)
    return candidates[0]


def _to_float(s):
    try:
        return float(str(s).replace(",", "."))
    except (ValueError, AttributeError, TypeError):
        return None


# Vinted rendert den Versandpreis als Label-Wert-Paar. Die Stelle erkennen wir daran,
# dass irgendwo kurz nach dem Wort "Versand" ein Preis steht, oft mit "ab" davor,
# oft aber auch direkt. Strategie: alle "Versand"-Positionen finden, im Fenster
# danach den ersten Euro-Betrag suchen, Minimum aller Treffer nehmen.
def extract_shipping(html, verbose=False):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    candidates = []

    for m in re.finditer(r"\bVersand\b", text):
        window = text[m.end():m.end() + 200]
        # Stoppe bei "Kaeuferschutz"/"Käuferschutz"-Block, damit wir den Kaeuferschutz-
        # Betrag nicht versehentlich als Versand nehmen.
        cutoff = re.search(r"K(?:ä|ae)uferschutz|Schneller|Verschickt", window)
        if cutoff:
            window = window[:cutoff.start()]
        # Suche den ersten Euro-Betrag im Fenster
        price_match = re.search(r"(\d{1,2}[.,]\d{2})\s*€", window)
        if price_match:
            value = _to_float(price_match.group(1))
            if value is not None and 0 < value < 30:
                candidates.append((value, window[:80].replace("\n", " | ")))

    if verbose:
        print(f"    [shipping] {len(candidates)} Kandidaten gefunden:")
        for value, ctx in candidates:
            print(f"      {value:.2f} EUR  aus  '{ctx}...'")

    if candidates:
        return min(c[0] for c in candidates)

    return None


def shipping_debug(html):
    """Zeigt wie extract_shipping entschieden hat."""
    _ = extract_shipping(html, verbose=True)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    print(f"    [shipping] alle 'Versand'-Stellen im Text:")
    for i, m in enumerate(re.finditer(r"\bVersand\b", text), 1):
        snippet = text[m.start():m.end() + 120].replace("\n", " | ")
        print(f"      [{i}] ...{snippet}...")
