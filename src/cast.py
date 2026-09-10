"""Dizinin sabit kadrosu ve sabit dunyasi.

Neden ayri bir dosya: onceki tasarimda her bolumde Gemini YENI kediler
uyduruyordu. Sonuc birbirinden kopuk melodram parcalariydi -- izleyicinin
baglanacagi kimse yoktu. Sitcom bunun tersi calisir: ayni kadro, ayni ev,
tanidik huylar. Espri de zaten oradan cikar; karakteri tanidigin icin ne
yapacagini tahmin edip gulersin.

Gorsel tutarlilik da buradan geliyor: karakter tarifi artik her bolumde
model tarafindan yeniden yazilmiyor, buradaki metin BIREBIR ayni sekilde
isteme giriyor.
"""

# Her tarif, gorsel modelin ayni kediyi cizmesi icin yeterince yogun olmali:
# govde, tuy deseni, yuz, goz rengi ve tek bir ayirt edici isaret.
#
# Tarifler bilerek GERCEK kedi anatomisine yazildi. Onceki surumde "plush
# cheeks", "huge round eyes" gibi ifadeler vardi ve model bunlari oyuncak
# bebek yuzune ceviriyordu -- tombik ama gercek degil. Simdi cinsi, kilosu
# ve kusurlari (dagilmis tuy, hafif sasi bakis, yamuk biyik) tarif ediliyor.
CAST = {
    "pasha": {
        "name": "Pasha",
        "look": ("Pasha, a very overweight ginger tabby domestic shorthair with classic "
                 "swirled tabby markings, a low hanging belly that sways when he walks, "
                 "short thick legs, heavy jowls, narrow sleepy amber eyes and a white "
                 "stripe down his nose, fur slightly greasy and uneven along his back"),
        "role": "the self-appointed king of the sofa",
        "traits": "lazy, enormously proud, treats every minor inconvenience as a personal insult",
    },
    "mochi": {
        "name": "Mochi",
        "look": ("Mochi, a small plump cream-white long-haired cat with a slightly "
                 "matted ruff, faint tabby ghost markings on her legs, a pink nose with "
                 "a small dark freckle, thin whiskers that bend unevenly and pale blue "
                 "eyes set a little wide apart"),
        "role": "the anxious one who keeps the flat tidy",
        "traits": "nervous, well-meaning, apologises with her body language, panics early and often",
    },
    "olive": {
        "name": "Olive",
        "look": ("Olive, a stocky black domestic shorthair with a ragged white bib on "
                 "her chest, one white front paw, a few stray white hairs on her flank, "
                 "a slightly notched left ear and narrow yellow-green eyes"),
        "role": "the schemer who starts most of the trouble",
        "traits": "clever, mischievous, never admits fault, always has a plan that backfires",
    },
    "biscuit": {
        "name": "Biscuit",
        "look": ("Biscuit, a thickset blue-grey British Shorthair with a broad square "
                 "muzzle, dense plush coat that stands up slightly on his shoulders, a "
                 "heavy neck, and small round copper eyes with a flat unreadable stare"),
        "role": "the silent flatmate who eats everything",
        "traits": "deadpan, says nothing, appears at the worst possible moment, unbothered by chaos",
    },
}

# Dizinin sabit mekanlari. Ayni ev, ayni esyalar -- her bolumde degisen sadece
# hangi odada oldugumuz.
LOCATIONS = [
    "the living room of a small cosy flat: a worn beige sofa with a knitted "
    "blanket, a low wooden coffee table and a tall window with soft daylight",
    "the little kitchen of the same flat: pale green cupboards, a cluttered "
    "counter, a humming fridge and warm afternoon light",
    "the narrow hallway of the same flat: a shoe rack, a coat hook and a front "
    "door with frosted glass, lit by a single warm ceiling lamp",
    "the same living room at night: only a lamp and the blue glow of a "
    "television lighting the worn beige sofa",
]

# Kadro ikilileri: hangi ikili sahnede, komedinin rengi degisiyor.
PAIRINGS = [
    ("pasha", "olive"),    # tembel kral vs. dolapci -- catisma
    ("mochi", "olive"),    # endiseli vs. belali -- kurban/fail
    ("pasha", "mochi"),    # kral vs. temizlikci -- pasif agresif
    ("olive", "biscuit"),  # plan vs. sessiz duvar
    ("pasha", "biscuit"),  # iki agirlik, tek koltuk
    ("mochi", "biscuit"),  # panik vs. hicbir tepki
]


def describe(keys: list[str]) -> str:
    """Secili kadronun gorsel tarifi -- her bolumde BIREBIR ayni metin."""
    return " ".join(CAST[k]["look"] + "." for k in keys if k in CAST)


def roster(keys: list[str]) -> str:
    """Senaryo yazarina verilecek karakter ozeti."""
    lines = []
    for k in keys:
        c = CAST.get(k)
        if c:
            lines.append(f"- {c['name']}: {c['role']}. {c['traits']}.")
    return "\n".join(lines)


def names(keys: list[str]) -> str:
    return " and ".join(CAST[k]["name"] for k in keys if k in CAST)
