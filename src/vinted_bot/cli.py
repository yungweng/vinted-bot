import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _open_when_ready(url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                webbrowser.open(url)
                return
        except Exception:
            time.sleep(0.2)
    print(f"Server hat nicht innerhalb von {timeout}s geantwortet. Oeffne manuell: {url}")


def _serve():
    import uvicorn
    from vinted_bot.dashboard.app import app

    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    print(f"Dashboard startet auf {url} ...", flush=True)
    threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()
    uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")).run()


def _scrape():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY env var ist nicht gesetzt.", file=sys.stderr)
        print("       export OPENROUTER_API_KEY=sk-or-...", file=sys.stderr)
        sys.exit(1)
    from vinted_bot.scrape import main as scrape_main
    scrape_main()


def main():
    args = sys.argv[1:]
    if not args:
        _serve()
        return
    cmd = args[0]
    if cmd == "serve":
        _serve()
    elif cmd == "scrape":
        _scrape()
    else:
        print(f"Unbekannter Befehl: {cmd}", file=sys.stderr)
        print("Verfuegbar: vinted-bot [serve|scrape]", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
