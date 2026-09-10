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
CAST = {
    "pasha": {
        "name": "Pasha",
        "look": ("Pasha, an enormous round orange tabby cat with a very round face, "
                 "thick plush cheeks, a heavy soft belly, short legs and huge lazy "
                 "amber eyes, with a distinctive white blaze down his nose"),
        "role": "the self-appointed king of the sofa",
        "traits": "lazy, enormously proud, treats every minor inconvenience as a personal insult",
    },
    "mochi": {
        "name": "Mochi",
        "look": ("Mochi, a small very round cream-white cat with a fluffy chest, "
                 "rosy pink nose, tiny ears and enormous worried blue eyes, always "
                 "looking slightly startled"),
        "role": "the anxious one who keeps the flat tidy",
        "traits": "nervous, well-meaning, apologises with her body language, panics early and often",
    },
    "olive": {
        "name": "Olive",
        "look": ("Olive, a chubby black cat with a white chest patch shaped like a "
                 "bib, one white front paw and sharp bright green eyes, with a "
                 "permanently smug expression"),
        "role": "the schemer who starts most of the trouble",
        "traits": "clever, mischievous, never admits fault, always has a plan that backfires",
    },
    "biscuit": {
        "name": "Biscuit",
        "look": ("Biscuit, a stocky grey British Shorthair with a very broad flat "
                 "face, dense velvety fur, a thick neck and round copper eyes that "
                 "never blink"),
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
