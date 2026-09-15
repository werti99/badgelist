import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


GITHUB_REPO_API = (
    "https://api.github.com/repos/"
    "IlIllllllIIIlIIl/hubba-files"
)

BADGE_API_URL = "https://json.hubba.cc/badges.php"

BADGE_PATH = "images/album1584"

OUTPUT_FILE = Path("data/badges.json")

# Anzahl paralleler Anfragen
MAX_WORKERS = 10

# Zwischen fehlgeschlagenen Versuchen
RETRIES = 3


def get_badge_codes():
    print("1. Verbinde mit GitHub...", flush=True)

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
        f"2. Default-Branch: {default_branch}",
        flush=True,
    )

    print(
        "3. Lade Repository-Dateibaum...",
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

    print(
        f"4. GitHub liefert "
        f"{len(tree.get('tree', []))} Einträge.",
        flush=True,
    )

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
        f"5. Insgesamt {len(codes):,} Badge-Codes gefunden."
        .replace(",", "."),
        flush=True,
    )

    return codes


def get_badge_amount(code):
    """Fragt die Umlaufzahl eines Badges ab.

    Rückgabe:
        int  -> Badge wurde von der API bestätigt
        0    -> Badge wurde bestätigt und hat 0 Umlauf
        None -> Badge nicht bestätigt oder Fehler
    """

    for attempt in range(1, RETRIES + 1):

        try:
            response = requests.get(
                BADGE_API_URL,
                params={
                    "name": code,
                },
                timeout=15,
                headers={
                    "User-Agent": "hubba-badges-updater",
                },
            )

            response.raise_for_status()

            data = response.json()

            api_code = data.get("badge_code")
            amount = data.get("total_amount")

            # Ganz wichtig:
            # Nur wenn die API den Badge-Code bestätigt,
            # akzeptieren wir die Umlaufzahl.
            if api_code != code:
                return None

            if amount is None:
                return None

            return int(amount)

        except Exception as error:

            if attempt < RETRIES:
                time.sleep(1 * attempt)
            else:
                print(
                    f"Fehler bei {code}: {error}",
                    flush=True,
                )

    return None


def main():
    print("Badge-Update gestartet.", flush=True)

    codes = get_badge_codes()

    print(
        "6. Frage Umlaufzahlen ab...",
        flush=True,
    )

    results = []

    completed = 0
    total = len(codes)

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_to_code = {
            executor.submit(
                get_badge_amount,
                code,
            ): code
            for code in codes
        }

        for future in as_completed(
            future_to_code
        ):
            code = future_to_code[future]

            try:
                amount = future.result()
            except Exception as error:
                print(
                    f"Fehler bei {code}: {error}",
                    flush=True,
                )
                amount = None

            results.append(
                {
                    "code": code,
                    "amount": amount,
                }
            )

            completed += 1

            # Fortschritt alle 100 Badges anzeigen
            if (
                completed % 100 == 0
                or completed == total
            ):
                print(
                    f"   Fortschritt: "
                    f"{completed:,} / {total:,}"
                    .replace(",", "."),
                    flush=True,
                )

    # Wieder nach Badge-Code sortieren
    results.sort(
        key=lambda badge: (
            badge["code"].lower(),
            badge["code"],
        )
    )

    print(
        "7. Erstelle badges.json...",
        flush=True,
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

    available = sum(
        1
        for badge in results
        if badge["amount"] is not None
    )

    unavailable = len(results) - available

    print(
        f"8. {OUTPUT_FILE} wurde erfolgreich erstellt.",
        flush=True,
    )

    print(
        f"   Bestätigte Umlaufzahlen: "
        f"{available:,}".replace(",", "."),
        flush=True,
    )

    print(
        f"   Nicht verfügbar: "
        f"{unavailable:,}".replace(",", "."),
        flush=True,
    )

    print(
        "Badge-Update erfolgreich!",
        flush=True,
    )


if __name__ == "__main__":
    main()
