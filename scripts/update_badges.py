import json
from pathlib import Path

import requests


GITHUB_REPO_API = (
    "https://api.github.com/repos/"
    "IlIllllllIIIlIIl/hubba-files"
)

BADGE_API_URL = "https://json.hubba.cc/badges.php"

OUTPUT_FILE = Path("data/badges.json")

# Nur für diesen Test
TEST_CODES = [
    "ADM",
    "BAZ10",
    "001IT",
    "0404C",
    "14HUBBA",
]


def get_badge_amount(code):
    """Fragt die Umlaufzahl eines Badges ab.

    Rückgabe:
        int  -> API hat eine gültige Zahl geliefert
        0    -> API meldet ausdrücklich 0
        None -> API konnte keinen gültigen Wert liefern
    """

    print(
        f"Frage Umlaufzahl für {code} ab...",
        flush=True,
    )

    try:
        response = requests.get(
            BADGE_API_URL,
            params={"name": code},
            timeout=15,
            headers={
                "User-Agent": "hubba-badges-updater",
            },
        )

        print(
            f"  HTTP {response.status_code}",
            flush=True,
        )

        response.raise_for_status()

        data = response.json()

        print(
            f"  API-Antwort: {data}",
            flush=True,
        )

        # Wichtig:
        # None bleibt None.
        # 0 bleibt 0.
        amount = data.get("total_amount")

        if amount is None:
            print(
                "  -> Ergebnis: null",
                flush=True,
            )
            return None

        amount = int(amount)

        print(
            f"  -> Ergebnis: {amount}",
            flush=True,
        )

        return amount

    except Exception as error:
        print(
            f"  -> Fehler: {error}",
            flush=True,
        )

        return None


def main():
    print("Umlaufzahl-Test gestartet.", flush=True)
    print("", flush=True)

    results = []

    for code in TEST_CODES:
        amount = get_badge_amount(code)

        results.append(
            {
                "code": code,
                "amount": amount,
            }
        )

        print("", flush=True)

    print("Ergebnisse:", flush=True)

    for badge in results:
        print(
            f"{badge['code']}: {badge['amount']}",
            flush=True,
        )

    print("", flush=True)
    print("Test erfolgreich.", flush=True)


if __name__ == "__main__":
    main()
