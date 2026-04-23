import sys

from vinted_bot.scraper.filters import params_from_url


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/discover_filters.py '<vinted-url>'")
        print()
        print("Tipp: gehe auf vinted.de, setze dort alle Filter in der UI,")
        print("kopiere die URL aus der Adressleiste und gib sie hier rein.")
        sys.exit(1)
    params = params_from_url(sys.argv[1])
    if not params:
        print("Keine Parameter in der URL gefunden.")
        sys.exit(0)
    print("API-Parameter fuer SEARCH_URL oder SEARCH_OVERRIDES:")
    for key, value in params.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
