import json
import subprocess
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

# Nach wie vielen Badges gespeichert + committed wird
COMMIT_EVERY = 500

# Maximale Laufzeit dieses GitHub-Action-Jobs
MAX_RUNTIME_SECONDS = 5 * 60 * 60

# Kleine Pause zwischen erfolgreichen Requests
REQUEST_DELAY = 0.5

# Wartezeit bei HTTP 429
RATE_LIMIT_WAIT = 60

# Maximale Versuche bei Fehlern
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

        result = {}

        for badge in data:
            if "code" not in badge:
                continue

            # Alte badges.json hatte noch kein "checked".
            # Diese werden deshalb als noch nicht geprüft behandelt.
            if "checked" not in badge:
                badge["checked"] = False

            result[badge["code"]] = badge

        return result

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


def git_commit_and_push():
    print(
        "   → Speichere Zwischenstand auf GitHub...",
        flush=True,
    )

    subprocess.run(
        [
            "git",
            "config",
            "user.name",
            "github-actions[bot]",
        ],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "add",
            "data/badges.json",
        ],
        check=True,
    )

    # Prüfen, ob tatsächlich Änderungen vorhanden sind
    result = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--quiet",
        ]
    )

    if result.returncode == 0:
        print(
            "   → Keine Änderungen.",
            flush=True,
        )
        return

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Update badge data",
        ],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "push",
        ],
        check=True,
    )

    print(
        "   → Zwischenstand erfolgreich gepusht.",
        flush=True,
    )


def get_badge_amount(code):
    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

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

            # HTTP 429 = zu viele Anfragen
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

            # WICHTIG:
            #
            # badge_code muss tatsächlich unserem
            # angefragten Code entsprechen.
            #
            # badge_code: null bedeutet NICHT Umlauf 0.
            if api_code != code:
                return None, True

            # Badge bestätigt, aber keine Zahl geliefert
            if amount is None:
                return None, True

            # Bestätigter Badge mit 0 bleibt 0
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
                print(
                    f"   {code} konnte nach "
                    f"{MAX_RETRIES} Versuchen "
                    f"nicht abgefragt werden.",
                    flush=True,
                )

                # Nicht als checked markieren.
                # Wird beim nächsten Lauf erneut versucht.
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
    # Badge-Codes laden
    # --------------------------------------------------

    codes = get_badge_codes()

    # --------------------------------------------------
    # Bestehenden Cache laden
    # --------------------------------------------------

    data = load_existing_data()

    # Neue Codes hinzufügen
    for code in codes:

        if code not in data:
            data[code] = {
                "code": code,
                "amount": None,
                "checked": False,
            }

    # Nicht mehr vorhandene Codes entfernen
    code_set = set(codes)

    data = {
        code: badge
        for code, badge in data.items()
        if code in code_set
    }

    # --------------------------------------------------
    # Position bestimmen
    # --------------------------------------------------

    unchecked_codes = [
        code
        for code in codes
        if not data[code].get("checked", False)
    ]

    # Wenn alle geprüft wurden:
    # neuen kompletten Durchlauf beginnen.
    if not unchecked_codes:

        print(
            "Alle Badges wurden bereits geprüft.",
            flush=True,
        )

        print(
            "Starte neuen Durchlauf.",
            flush=True,
        )

        for code in codes:
            data[code]["checked"] = False

        unchecked_codes = codes

    first_code = unchecked_codes[0]

    print(
        f"Starte bei: {first_code}",
        flush=True,
    )

    # --------------------------------------------------
    # Badges abfragen
    # --------------------------------------------------

    processed_since_commit = 0
    total_processed = 0

    for code in unchecked_codes:

        # Laufzeit kontrollieren
        elapsed = time.time() - start_time

        if elapsed >= MAX_RUNTIME_SECONDS:

            print(
                "Maximale Laufzeit erreicht.",
                flush=True,
            )

            save_data(data)
            git_commit_and_push()

            print(
                "Fortschritt wurde gespeichert.",
                flush=True,
            )

            break

        amount, successful = get_badge_amount(
            code
        )

        if successful:

            data[code]["amount"] = amount
            data[code]["checked"] = True

        total_processed += 1
        processed_since_commit += 1

        # Alle 50 Fortschritt anzeigen
        if total_processed % 50 == 0:

            checked = sum(
                1
                for badge in data.values()
                if badge.get("checked", False)
            )

            percentage = (
                checked / len(codes)
            ) * 100

            print(
                f"   Fortschritt: "
                f"{checked:,} / {len(codes):,} "
                f"({percentage:.1f} %)"
                .replace(",", "."),
                flush=True,
            )

        # --------------------------------------------------
        # Alle 500 Ergebnisse committen
        # --------------------------------------------------

        if processed_since_commit >= COMMIT_EVERY:

            save_data(data)

            git_commit_and_push()

            processed_since_commit = 0

        time.sleep(REQUEST_DELAY)

    else:

        # Alle Badges dieses Durchlaufs geschafft
        save_data(data)
        git_commit_and_push()

        print(
            "Alle Badges dieses Durchlaufs wurden geprüft.",
            flush=True,
        )

    # --------------------------------------------------
    # Statistik
    # --------------------------------------------------

    checked = sum(
        1
        for badge in data.values()
        if badge.get("checked", False)
    )

    available = sum(
        1
        for badge in data.values()
        if (
            badge.get("checked", False)
            and badge.get("amount") is not None
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
        f"Geprüft: "
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
