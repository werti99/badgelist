import json
from pathlib import Path

import requests


GITHUB_REPO_API = (
    "https://api.github.com/repos/"
    "IlIllllllIIIlIIl/hubba-files"
)

OUTPUT_FILE = Path("data/badges.json")


def get_badge_codes():
    """Liest alle Badge-Codes aus images/album1584."""

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "hubba-badges-updater",
    }

    print("1. Verbinde mit GitHub...", flush=True)

    repo_response = requests.get(
        GITHUB_REPO_API,
        timeout=15,
        headers=headers,
    )

    repo_response.raise_for_status()

    repo_data = repo_response.json()
    default_branch = repo_data["default_branch"]

    print(
        f"2. Default-Branch: {default_branch}",
        flush=True,
    )

    tree_url = (
        f"{GITHUB_REPO_API}/git/trees/"
        f"{default_branch}?recursive=1"
    )

    print("3. Lade Repository-Dateibaum...", flush=True)

    response = requests.get(
        tree_url,
        timeout=60,
        headers=headers,
    )

    response.raise_for_status()

    data = response.json()

    print(
        f"4. GitHub liefert {len(data.get('tree', []))} Einträge.",
        flush=True,
    )

    badge_codes = []

    for item in data.get("tree", []):
        path = item.get("path", "")

        if not path.startswith("images/album1584/"):
            continue

        if not path.lower().endswith(".gif"):
            continue

        filename = Path(path).name
        code = filename[:-4]

        if code:
            badge_codes.append(code)

    badge_codes = sorted(
        set(badge_codes),
        key=str.lower,
    )

    return badge_codes


def save_badges(badge_codes):
    """Speichert alle Badge-Codes als JSON."""

    badges = []

    for code in badge_codes:
        badges.append(
            {
                "code": code,
                "amount": None,
            }
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
            badges,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")


def main():
    print("Badge-Update gestartet.", flush=True)

    badge_codes = get_badge_codes()

    print(
        f"5. Insgesamt {len(badge_codes)} Badge-Codes gefunden.",
        flush=True,
    )

    print("6. Erstelle badges.json...", flush=True)

    save_badges(badge_codes)

    print(
        f"7. {OUTPUT_FILE} wurde erfolgreich erstellt.",
        flush=True,
    )

    print("Badge-Update erfolgreich!", flush=True)


if __name__ == "__main__":
    main()
