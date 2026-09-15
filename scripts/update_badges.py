import json
import time
from pathlib import Path

import requests


# GitHub-Repository mit den HuBBa-Badge-Dateien
GITHUB_REPO_API = (
    "https://api.github.com/repos/"
    "IlIllllllIIIlIIl/hubba-files"
)

# HuBBa API für die Umlaufzahl
BADGE_API_URL = "https://json.hubba.cc/badges.php"

# Ziel-Datei in unserem eigenen Repository
OUTPUT_FILE = Path("data/badges.json")


def get_badge_codes():
    """Liest alle Badge-Codes aus dem GitHub-Repository."""

    response = requests.get(
        GITHUB_TREE_URL,
        timeout=30,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "hubba-badges-updater",
        },
    )

    response.raise_for_status()

    data = response.json()

    badge_codes = []

    for item in data.get("tree", []):
        path = item.get("path", "")

        # Nur GIFs aus images/album1584 berücksichtigen
        if not path.startswith("images/album1584/"):
            continue

        if not path.lower().endswith(".gif"):
            continue

        filename = Path(path).name

        # .gif entfernen
        code = filename[:-4]

        if code:
            badge_codes.append(code)

    # Doppelte Codes entfernen und alphabetisch sortieren
    badge_codes = sorted(set(badge_codes), key=str.lower)

    return badge_codes


def get_badge_amount(code):
    """Fragt die Umlaufzahl eines einzelnen Badges ab."""

    try:
        response = requests.get(
            BADGE_API_URL,
            params={"name": code},
            timeout=15,
            headers={
                "User-Agent": "hubba-badges-updater",
            },
        )

        response.raise_for_status()

        data = response.json()

        # API liefert beispielsweise:
        # {"badge_code":"ADM","total_amount":17}

        amount = data.get("total_amount")

        if amount is None:
            return None

        return int(amount)

    except Exception as error:
        print(f"Fehler bei {code}: {error}")
        return None


def main():
    print("Hole Badge-Codes aus GitHub...")

    badge_codes = get_badge_codes()

    print(f"{len(badge_codes)} Badge-Codes gefunden.")

    badges = []

    for index, code in enumerate(badge_codes, start=1):
        print(f"[{index}/{len(badge_codes)}] {code}")

        amount = get_badge_amount(code)

        badges.append(
            {
                "code": code,
                "amount": amount,
            }
        )

        # Kleine Pause, damit die HuBBa-API nicht mit
        # tausenden Anfragen ohne Pause belastet wird.
        time.sleep(0.1)

    # data-Ordner sicherstellen
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # JSON speichern
    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            badges,
            file,
            ensure_ascii=False,
            indent=4,
        )

        file.write("\n")

    print()
    print(f"Fertig: {OUTPUT_FILE}")
    print(f"{len(badges)} Badges gespeichert.")


if __name__ == "__main__":
    main()
