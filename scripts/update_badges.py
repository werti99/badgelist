import json
import time
from pathlib import Path

import requests


GITHUB_REPO_API = (
    "https://api.github.com/repos/"
    "IlIllllllIIIlIIl/hubba-files"
)

BADGE_API_URL = "https://json.hubba.cc/badges.php"

BADGE_PATH = "images/album1584"

OUTPUT_FILE = Path("data/badges.json")

# Maximal so lange pro GitHub-Action-Lauf arbeiten.
# Danach wird der Fortschritt gespeichert und am nächsten Tag fortgesetzt.
MAX_RUNTIME_SECONDS = 5 * 60 * 60

# Normale Pause zwischen erfolgreichen Anfragen.
REQUEST_DELAY = 0.5

# Bei 429 mindestens so lange warten.
RATE_LIMIT_WAIT = 60

# Maximale Anzahl Versuche bei einem Badge.
MAX_RETRIES = 10


def get_badge_codes():
    print("1. Lade Badge-Codes von GitHub...", flush=True)

    response = requests.get(
        GITHUB_REPO_API,
        timeout=30,
        headers={
            "User-Agent": "hubba-badges-updater",
        },
    )

    response.raise_for_status()

    repo_info = response.json()
    default_branch = repo_info["default_branch"]

    print(
        f"   Default-Branch: {default_branch}",
        flush=True,
    )

    tree_url = (
        f"https://api.github.com/repos/"
        f"IlIllllllIIIlIIl/hubba-files/"
        f"git/trees/{default_branch}"
        f"?recursive=1"
    )

    response = requests.get(
        tree_url,
        timeout=60,
        headers={
            "User-Agent": "hubba-badges-updater",
        },
    )

    response.raise_for_status()

    tree = response.json()

    codes = []
    prefix = BADGE_PATH + "/"

    for item in tree.get("tree", []):
        path = item.get("path", "")

        if not path.startswith(prefix):
            continue

        if item.get("type") != "blob":
            continue

        filename = path[len(prefix):]

        if not filename.lower().endswith(".gif"):
            continue

        code = filename[:-4]

        if code:
            codes.append(code)

    codes = sorted(
        set(codes),
        key=lambda value: (
            value.lower(),
            value,
        ),
    )

    print(
        f"   {len(codes):,} Badge-Codes gefunden."
        .replace(",", "."),
        flush=True,
    )

    return codes


def load_existing_data():
    if not OUTPUT_FILE.exists():
        return {}

    try:
        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return {
            badge["code"]: badge
            for badge in data
            if "code" in badge
        }

    except Exception as error:
        print(
            f"Warnung: badges.json konnte nicht gelesen werden: {error}",
            flush=True,
        )

        return {}


def save_data(data):
    results = sorted(
        data.values(),
        key=lambda badge: (
            badge["code"].lower(),
            badge["code"],
        ),
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )


def get_badge_amount(code):
    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = requests.get(
                BADGE_API_URL,
                params={
                    "name": code,
                },
                timeout=20,
                headers={
                    "User-Agent": "hubba-badges-updater",
                },
            )

            # Rate Limit
            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                try:
                    wait_seconds = int(
                        retry_after
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    wait_seconds = RATE_LIMIT_WAIT

                print(
                    f"   429 bei {code} "
                    f"→ warte {wait_seconds} Sekunden...",
                    flush=True,
                )

                time.sleep(wait_seconds)
                continue

            response.raise_for_status()

            data = response.json()

            api_code = data.get("badge_code")
            amount = data.get("total_amount")

            # Die API bestätigt diesen Badge nicht.
            #
            # Wichtig:
            # Das ist NICHT dasselbe wie ein bestätigter
            # Badge mit total_amount = 0.
            if api_code != code:
                return None, True

            if amount is None:
                return None, True

            return int(amount), True

        except Exception as error:

            print(
                f"   Fehler bei {code}: {error}",
                flush=True,
            )

            if attempt < MAX_RETRIES:
                wait_seconds = min(
                    10 * attempt,
                    120,
                )

                print(
                    f"   Neuer Versuch in "
                    f"{wait_seconds} Sekunden...",
                    flush=True,
                )

                time.sleep(wait_seconds)

            else:
                return None, False

    return None, False


def main():
    start_time = time.time()

    print(
        "======================================",
        flush=True,
    )
    print(
        "HuBBa Badge Update gestartet",
        flush=True,
    )
    print(
        "======================================",
        flush=True,
    )

    # --------------------------------------------------
    # Badge-Codes holen
    # --------------------------------------------------

    codes = get_badge_codes()

    # --------------------------------------------------
    # Bestehende Daten laden
    # --------------------------------------------------

    data = load_existing_data()

    # Alle gefundenen Codes sicherstellen
    for code in codes:

        if code not in data:
            data[code] = {
                "code": code,
                "amount": None,
                "checked": False,
            }

        elif "checked" not in data[code]:
            data[code]["checked"] = False

    # Alte Codes entfernen, die nicht mehr im Repository existieren
    code_set = set(codes)

    data = {
        code: badge
        for code, badge in data.items()
        if code in code_set
    }

    # --------------------------------------------------
    # Startposition bestimmen
    # --------------------------------------------------

    start_index = 0

    for index, code in enumerate(codes):

        if not data[code].get("checked", False):
            start_index = index
            break

    else:
        # Alle wurden bereits einmal abgefragt.
        # Neuer kompletter Durchlauf.
        start_index = 0

        for code in codes:
            data[code]["checked"] = False

        print(
            "Alle Badges wurden bereits abgefragt.",
            flush=True,
        )

        print(
            "Starte neuen Durchlauf.",
            flush=True,
        )

    # --------------------------------------------------
    # Badges abfragen
    # --------------------------------------------------

    print(
        f"Starte bei Badge "
        f"{start_index + 1} / {len(codes)}: "
        f"{codes[start_index]}",
        flush=True,
    )

    processed = 0

    for index in range(
        start_index,
        len(codes),
    ):

        # Laufzeit prüfen
        elapsed = time.time() - start_time

        if elapsed >= MAX_RUNTIME_SECONDS:

            print(
                "Maximale Laufzeit erreicht.",
                flush=True,
            )

            print(
                "Fortschritt wurde gespeichert.",
                flush=True,
            )

            break

        code = codes[index]

        amount, successful = get_badge_amount(
            code
        )

        # Nur bei erfolgreicher Anfrage als
        # abgefragt markieren.
        if successful:

            data[code]["amount"] = amount
            data[code]["checked"] = True

        # Bei einem temporären Fehler NICHT als
        # erfolgreich abgefragt markieren.
        #
        # Dadurch wird der Badge beim nächsten
        # Lauf erneut versucht.

        processed += 1

        if processed % 50 == 0:

            save_data(data)

            percentage = (
                (index + 1) / len(codes)
            ) * 100

            print(
                f"   Fortschritt: "
                f"{index + 1:,} / {len(codes):,} "
                f"({percentage:.1f} %)"
                .replace(",", "."),
                flush=True,
            )

            print(
                "   Zwischenstand gespeichert.",
                flush=True,
            )

        time.sleep(REQUEST_DELAY)

    # --------------------------------------------------
    # Endgültig speichern
    # --------------------------------------------------

    save_data(data)

    checked = sum(
        1
        for code in codes
        if data[code].get("checked", False)
    )

    available = sum(
        1
        for code in codes
        if (
            data[code].get("checked", False)
            and data[code].get("amount") is not None
        )
    )

    unavailable = checked - available

    print(
        "",
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )

    print(
        "Update beendet.",
        flush=True,
    )

    print(
        f"Abgefragt: "
        f"{checked:,} / {len(codes):,}"
        .replace(",", "."),
        flush=True,
    )

    print(
        f"Umlauf verfügbar: "
        f"{available:,}"
        .replace(",", "."),
        flush=True,
    )

    print(
        f"Nicht verfügbar: "
        f"{unavailable:,}"
        .replace(",", "."),
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )


if __name__ == "__main__":
    main()
