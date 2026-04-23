def _fmt_money(value, currency="EUR"):
    if value is None:
        return "unbekannt"
    return f"{value:.2f} {currency}"


_FORMAT_INSTRUCTION = (
    "\n\n---\n"
    "Antwortformat (pflicht):\n"
    "Bei Zustimmung: antworte exakt das Wort 'ja' und nichts weiter.\n"
    "Bei Ablehnung: antworte 'nein: <Grund in max 15 Woertern>'.\n"
    "Der Grund soll die wichtigste Regel nennen, an der es scheitert "
    "(z.B. 'Modellnummer nicht in Bildern', 'Versand 4,99 EUR ueber Limit', "
    "'Risse in Beschreibung'). Keine Aufzaehlungen, keine Absaetze, nur ein Satz."
)


def build_user_message(item, ocr_text):
    currency = item.get("currency", "EUR")
    description = item.get("description") or "(keine Beschreibung)"
    return (
        "<bilder_ocr>\n"
        f"{ocr_text}\n"
        "</bilder_ocr>\n\n"
        "<artikel_daten>\n"
        f"Titel: {item.get('title','')}\n"
        f"Marke: {item.get('brand','')}\n"
        f"Groesse: {item.get('size','')}\n"
        f"Zustand: {item.get('condition','')}\n"
        f"Farbe: {item.get('color','')}\n"
        f"Preis: {_fmt_money(item.get('price'), currency)}\n"
        f"Kaeuferschutz: {_fmt_money(item.get('buyer_protection'), currency)}\n"
        f"Versand ab: {_fmt_money(item.get('shipping'), currency)}\n"
        f"Hochgeladen: {item.get('uploaded_at','')}\n"
        f"URL: {item.get('url','')}\n"
        "</artikel_daten>\n\n"
        "<beschreibung>\n"
        f"{description}\n"
        "</beschreibung>"
        + _FORMAT_INSTRUCTION
    )
