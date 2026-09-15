let badges = [];

let filteredBadges = [];


const BADGE_IMAGE_BASE =
    "https://data.hubba.cc/images/album1584";


/* =========================
   JSON LADEN
   ========================= */

async function loadBadges() {

    try {

        const response =
            await fetch(
                "data/badges.json"
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        badges =
            await response.json();


        filteredBadges =
            [...badges];


        document
            .getElementById("loading")
            .style.display = "none";


        updateStatus();


        renderBadges();


    } catch (error) {

        console.error(error);


        document
            .getElementById("loading")
            .innerHTML = `
                <div class="error">
                    Fehler beim Laden der Badge-Daten.
                    <br><br>
                    ${error.message}
                </div>
            `;
    }
}


/* =========================
   STATUS
   ========================= */

function updateStatus() {

    document
        .getElementById("status")
        .textContent =
            `${filteredBadges.length.toLocaleString("de-DE")} von ${badges.length.toLocaleString("de-DE")} Badges`;
}


/* =========================
   RENDER
   ========================= */

function renderBadges() {

    const container =
        document.getElementById(
            "badges"
        );


    container.innerHTML = "";


    if (
        filteredBadges.length === 0
    ) {

        container.innerHTML = `
            <div class="error">
                Keine Badges gefunden.
            </div>
        `;

        return;
    }


    const fragment =
        document.createDocumentFragment();


    for (
        const badge of filteredBadges
    ) {

        const card =
            document.createElement(
                "div"
            );


        card.className =
            "badge";


        /* IMAGE */

        const image =
            document.createElement(
                "img"
            );


        image.className =
            "badge-image";


        image.src =
            `${BADGE_IMAGE_BASE}/${encodeURIComponent(
                badge.code
            )}.gif`;


        image.alt =
            badge.code;


        image.loading =
            "lazy";


        image.onerror = () => {

            image.style.opacity =
                "0.15";
        };


        /* CODE */

        const code =
            document.createElement(
                "div"
            );


        code.className =
            "badge-code";


        code.textContent =
            badge.code;


        /* AMOUNT */

        const amount =
            document.createElement(
                "div"
            );


        amount.className =
            "badge-amount";


        if (
            badge.amount === null ||
            badge.amount === undefined
        ) {

            amount.textContent =
                "Umlauf: nicht verfügbar";

        } else {

            amount.textContent =
                `Umlauf: ${Number(
                    badge.amount
                ).toLocaleString(
                    "de-DE"
                )}`;
        }


        card.appendChild(image);

        card.appendChild(code);

        card.appendChild(amount);


        fragment.appendChild(card);
    }


    container.appendChild(
        fragment
    );
}


/* =========================
   SUCHE
   ========================= */

function searchBadges() {

    const value =
        document
            .getElementById("search")
            .value
            .trim()
            .toLowerCase();


    filteredBadges =
        badges.filter(
            badge =>
                badge.code
                    .toLowerCase()
                    .includes(value)
        );


    sortBadges();

    renderBadges();

    updateStatus();
}


/* =========================
   SORTIERUNG
   ========================= */

function sortBadges() {

    const mode =
        document
            .getElementById("sort")
            .value;


    filteredBadges.sort(
        (a, b) => {

            if (
                mode === "code-asc"
            ) {

                return a.code.localeCompare(
                    b.code,
                    undefined,
                    {
                        numeric: true,
                        sensitivity: "base"
                    }
                );
            }


            if (
                mode === "code-desc"
            ) {

                return b.code.localeCompare(
                    a.code,
                    undefined,
                    {
                        numeric: true,
                        sensitivity: "base"
                    }
                );
            }


            if (
                mode === "amount-desc"
            ) {

                return (
                    (b.amount ?? -1) -
                    (a.amount ?? -1)
                );
            }


            if (
                mode === "amount-asc"
            ) {

                return (
                    (a.amount ?? Infinity) -
                    (b.amount ?? Infinity)
                );
            }


            return 0;
        }
    );
}


/* =========================
   EVENTS
   ========================= */

document
    .getElementById("search")
    .addEventListener(
        "input",
        searchBadges
    );


document
    .getElementById("sort")
    .addEventListener(
        "change",
        () => {

            sortBadges();

            renderBadges();
        }
    );


/* =========================
   START
   ========================= */

loadBadges();