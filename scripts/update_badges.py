import requests


GITHUB_REPO_API = (
    "https://api.github.com/repos/"
    "IlIllllllIIIlIIl/hubba-files"
)


def main():
    print("1. Starte Test...", flush=True)

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "hubba-badges-updater",
    }

    print("2. Verbinde mit GitHub...", flush=True)

    response = requests.get(
        GITHUB_REPO_API,
        timeout=15,
        headers=headers,
    )

    print(
        f"3. GitHub antwortet mit HTTP {response.status_code}",
        flush=True,
    )

    response.raise_for_status()

    data = response.json()

    print(
        f"4. Repository gefunden: {data['full_name']}",
        flush=True,
    )

    print(
        f"5. Default-Branch: {data['default_branch']}",
        flush=True,
    )

    print("6. Test erfolgreich!", flush=True)


if __name__ == "__main__":
    main()
