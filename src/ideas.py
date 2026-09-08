"""Her calismada yeni bir kedi DRAMASI uretir.

Tasarim degisikligi: eskiden cekimler ayni hareketin kucuk adimlariydi
(dans eden kedi, poz poz). Bu guvenliydi ama izleyiciyi tutmuyordu.
Artik her Reel 6 vurusluk bir mikro-drama: kanca -> tirmanma -> twist.
Ilk kare en carpici olan; merak bosluu ilk saniyede aciliyor.

Model erisilemezse tamamen yerel sablonla devam edilir; hat asla durmaz.
"""
import json
import random

from . import log
from .textgen import TextGenError, concept_json

# Her tema, ICINDE DONUS OLAN bir premis havuzu. Duz durum degil, olay.
THEMES = {
    "aldatma": [
        "kedi eve erken gelir, dolapta baska bir kedi bulur",
        "kedi sevgilisini en yakin arkadasiyla kafede yakalar",
        "kedi telefonda mesajlari gorur, sevgilisi yalan soyler ama fotograf ortaya cikar",
        "kedi dogum gunu suprizi hazirlar, sevgilisi baskasiyla gelir",
        "kedi cift terapisine gider, terapist de sevgilisinin sevgilisi cikar",
    ],
    "sevgili": [
        "kedi evlenme teklif eder, yuzuk kutusu bos cikar",
        "kedi ilk bulusmaya gider, karsisina cocuklugundan tanidigi kedi cikar",
        "kedi sevgilisine surpriz yapar, kapiyi acan baska biri olur",
        "kedi yagmurda saatlerce bekler, sevgilisi gelmez ama not birakmistir",
        "kedi ayrilmaya karar verir, tam soyleyecekken sevgilisi ona teklif eder",
    ],
    "kovulma": [
        "kedi patronuna kahve doker, kovulur, ertesi gun patronun koltuguna oturur",
        "kedi kovulur, cikarken tum ofis ayaga kalkip alkislar",
        "kedi zam ister, patron guler, kedi rakip sirkete gecer",
        "kedi mesai sonrasi yakalanir, aslinda sirketi kurtaran raporu yaziyordur",
        "kedi kovulur, bir yil sonra ayni ofise patron olarak doner",
    ],
    "zengin": [
        "sokak kedisi piyango kazanir, ertesi gun limuzinle mahalleye doner",
        "fakir kedi, kendisini asagilayan kediyi luks restoranda garson gorur",
        "kedi caydan para cikarir, mahalledeki herkese ziyafet ceker",
        "kedi eski paltosuyla luks magazaya alinmaz, kartla geri doner",
        "kedi mirasi reddeder, sokakta buyuten kediye verir",
    ],
    "intikam": [
        "kedi surekli alay edilir, yetenek yarismasinda sahneye cikar",
        "kedi balik calan komsuyu kurar, tuzagi kendi kurdugu tuzak olur",
        "kedi kucuk gorulur, mahalle kavgasinda herkesi sasirtir",
        "kedi disari atilir, sahibi onu bulmak icin sehri arar",
    ],
    "komik": [
        "kedi diyet yapacagini ilan eder, gece buzdolabinda yakalanir",
        "kedi kopek taklidi yapar, gercek kopek gelir",
        "kedi robot supurgeye biner, evin duzenini bozar",
        "kedi karaoke yapar, mikrofonu kimseye vermez",
    ],
}

# Gorsel dil: her cekimde ayni kalmali ki kedi ayni kedi gorunsun.
STYLE_POOL = [
    "cinematic 3D animated film still, Pixar-quality fur shading, dramatic rim light, shallow depth of field",
    "hyperreal photograph, 85mm lens, moody cinematic lighting, creamy bokeh, photorealistic cat fur",
    "cinematic 3D animation, telenovela lighting with warm key and cool shadows, film grain",
    "vibrant stylised 3D cartoon, bold shapes, saturated palette, strong key light",
]

SYSTEM = """You write viral vertical short-form CAT DRAMAS. Think telenovela, but every
character is a cat. You return ONLY a JSON object. No prose, no markdown fence.

THE ONE RULE THAT MATTERS: the viewer decides in 1.5 seconds whether to keep watching.
So beat 1 is never a calm establishing shot - it is the most arresting image in the
whole story, dropped in cold. Start in the middle of the drama, not before it.

Structure the beats as a micro-drama, not as one continuous movement:
  beat 1        the hook - the shocking / funny image that opens a question
  beats 2..n-2  escalation - the situation gets worse or stranger
  beat n-1      the turn - something is revealed or reversed
  beat n        the payoff - reaction, comeuppance, or punchline

Rules:
- All visual text MUST be in English (image and video models are trained on English).
- The caption MUST be in Turkish, and it must invite a reply: a question, a hot take,
  or a "bunu yasayan var mi" energy. 1-2 short sentences, at most one emoji.
- The hook MUST be in Turkish, AT MOST 26 characters including spaces. It is burned onto
  the first seconds of the video, so it must fit. Write it as an open loop, not a summary:
  "Dolapta biri vardi" beats "Kedi sevgilisini aldatti". No emoji, no ending punctuation.
- The character field is the single most important one: one dense English sentence
  describing the cat(s) so precisely (breed, fur colour and pattern, eye colour, body
  shape, clothing/accessory) that the model draws the SAME cat every time. If there are
  two cats, describe BOTH distinctly in that one sentence. Never change it between beats.
- Each beat's action is ONE clear physical moment with visible emotion, in English,
  10-20 words. Name who is doing what, and show feeling through body language and face -
  no thought bubbles, no speech, no text in the image.
- Cats only. Keep it playful soap-opera drama, never cruel and never graphic.
"""

USER_TMPL = """Write a {shots}-beat vertical cat drama.

Theme: {theme}
Premise to dramatise: {seed_idea}
Visual style to keep in every beat: {style}
Do not repeat any of these recent titles: {recent}

Return exactly this JSON shape:
{{
  "title": "short English slug-like title",
  "hook": "Turkish, max 26 characters, an open loop, burned onto the video",
  "character": "one dense English sentence; if two cats, both described distinctly",
  "setting": "one English sentence describing the location and lighting",
  "beats": [
    {{"action": "English, one clear dramatic moment with visible emotion",
      "camera": "English camera note, e.g. low angle close-up, wide shot"}}
  ],
  "caption": "Turkish caption that invites a reply, 1-2 sentences, max one emoji",
  "hashtags": ["#kedi", "#cat", "8-14 mixed Turkish and English tags"]
}}

The beats array must contain exactly {shots} items, following hook -> escalation ->
turn -> payoff."""


# --- yerel yedek havuzlari (metin modeli hic calismasa bile drama cikar) ----

CHARACTERS = [
    ("a chubby orange tabby tomcat with white chest fur, huge round green eyes and a tiny "
     "red bow tie, and a slender white cat with long silky fur and ice-blue eyes wearing "
     "a thin gold chain"),
    ("a sleek black cat with bright yellow eyes and one white paw, in a rumpled office "
     "shirt, and a large grey British Shorthair with copper eyes in an expensive suit"),
    ("a small scruffy calico street cat with mismatched eyes and a torn ear, and a "
     "pampered fluffy white Persian with a diamond collar"),
    ("a cream Ragdoll cat with sapphire blue eyes wearing a knitted scarf, and a ginger "
     "tabby with a crooked whisker and a leather jacket"),
]

SETTINGS = {
    "aldatma": ["a dim apartment hallway at night, a single warm lamp and a half-open door",
                "a rainy city cafe window seat at dusk, neon reflections on wet glass"],
    "sevgili": ["a rooftop terrace at sunset, string lights and a small table for two",
                "a quiet beach at golden hour, long shadows on wet sand"],
    "kovulma": ["a grey open-plan office at night, one desk lamp still on",
                "a glass corner office at sunrise, city skyline behind"],
    "zengin": ["a marble hotel lobby with chandeliers and gold trim",
               "a narrow backstreet at night, then bright shop windows"],
    "intikam": ["a bright talent-show stage with a single spotlight and dark audience",
                "a cluttered neighbourhood courtyard at noon, harsh sunlight"],
    "komik": ["a cosy kitchen at midnight, only the open fridge lighting the room",
              "a messy living room full of snacks and blankets"],
}

HOOKS = {
    "aldatma": ["Dolapta biri vardi", "Kapiyi acmamaliydim", "Fotografi gordum"],
    "sevgili": ["Kutu bostu", "Saatlerce bekledi", "Tam soyleyecekti"],
    "kovulma": ["Bugun kovuldum", "Patron guldu", "Bir yil sonra dondu"],
    "zengin": ["Dun sokaktaydi", "Iceri almadilar", "Bileti cebindeydi"],
    "intikam": ["Hep guluyorlardi", "Sahneye cikti", "Tuzak geri teptii"],
    "komik": ["Diyet bugun basladi", "Buzdolabinda yakalandi", "Mikrofonu birakmadi"],
}

CAPTIONS = {
    "aldatma": ["Siz olsaniz ne yapardiniz?", "Bu sahneyi yasayan var mi?"],
    "sevgili": ["Bu kadar tatli olmasi yasak olmali.", "Siz hic bu kadar beklediniz mi?"],
    "kovulma": ["Herkesin bir patron hikayesi var. Seninki ne?", "Bu son var ya, tam hak etti."],
    "zengin": ["Kimseyi kucumsemeyin derler ya, iste tam bu.", "Sonu tahmin ettiniz mi?"],
    "intikam": ["En guzel cevap bu olsa gerek.", "Gulenlerin yuzunu gordunuz mu?"],
    "komik": ["Bu kedi hepimiziz.", "Diyet kac gun surdu sizce?"],
}

BEATS = [
    "the first cat freezes in the doorway, eyes wide, one paw still on the handle",
    "the second cat looks up sharply, caught, ears flattening in panic",
    "the first cat steps back slowly, tail low, jaw tight with disbelief",
    "the second cat reaches out a pleading paw, the first cat turns away",
    "the first cat lifts its chin, expression hardening into calm resolve",
    "the first cat walks out into the light, head high, not looking back",
]

CAMERAS = ["low angle close-up", "medium shot, eye level", "wide shot, slight high angle",
           "extreme close-up on the face", "over-the-shoulder medium shot"]


def _fallback(theme: str, seed_idea: str, style: str, shots: int) -> dict:
    """Metin modeli olmadan da calisan, kendi icinde cesitli yedek drama."""
    return {
        "title": seed_idea[:40],
        "hook": random.choice(HOOKS.get(theme, HOOKS["komik"])),
        "character": random.choice(CHARACTERS),
        "setting": random.choice(SETTINGS.get(theme, SETTINGS["komik"])),
        "beats": [{"action": BEATS[i % len(BEATS)], "camera": CAMERAS[i % len(CAMERAS)]}
                  for i in range(shots)],
        "caption": random.choice(CAPTIONS.get(theme, CAPTIONS["komik"])),
        "hashtags": ["#kedi", "#cat", "#catsofinstagram", "#kedistagram", "#aicat",
                     "#yapayzeka", "#reels", "#kedivideolari", "#drama", "#kedidrama",
                     "#funnycats", "#catlovers"],
        "_fallback": True,
    }


def generate(client, cfg, history: list[str]) -> dict:
    theme = random.choice(list(THEMES))
    seed_idea = random.choice(THEMES[theme])
    style = random.choice(STYLE_POOL)
    recent = ", ".join(history[-12:]) or "yok"

    prompt = USER_TMPL.format(shots=cfg.shots, theme=theme, seed_idea=seed_idea,
                              style=style, recent=recent)
    try:
        idea = concept_json(client, cfg, SYSTEM, prompt)
    except (TextGenError, json.JSONDecodeError) as exc:
        log.warn(f"fikir modeli kullanilamadi ({exc}); yerel sablona dusuluyor")
        idea = _fallback(theme, seed_idea, style, cfg.shots)

    idea = _normalise(idea, theme, seed_idea, style, cfg.shots)
    log.info(f"drama: [{theme}] {idea['title']} -- kanca: {idea['hook']!r}")
    return idea


def _normalise(idea: dict, theme: str, seed_idea: str, style: str, want: int) -> dict:
    """Modelin ne dondurdugune bakmaksizin kullanilabilir bir sozluk garanti eder."""
    base = _fallback(theme, seed_idea, style, want)
    out = {
        "theme": theme,
        "seed_idea": seed_idea,
        "style": style,
        "title": str(idea.get("title") or base["title"])[:80],
        # Kanca ekrana basiliyor: model uzun yazarsa kadraja sigmasi icin kirp.
        "hook": str(idea.get("hook") or base["hook"]).strip().rstrip(".!?")[:30],
        "character": str(idea.get("character") or base["character"]),
        "setting": str(idea.get("setting") or base["setting"]),
        "caption": str(idea.get("caption") or base["caption"]),
        "used_fallback": bool(idea.get("_fallback")),
    }

    # Model "beats" yerine "shots" dondurebilir; ikisini de kabul et.
    raw = idea.get("beats") or idea.get("shots") or []
    clean = []
    for s in raw:
        if isinstance(s, dict) and s.get("action"):
            clean.append({"action": str(s["action"]),
                          "camera": str(s.get("camera") or "medium shot")})
        elif isinstance(s, str) and s.strip():
            clean.append({"action": s.strip(), "camera": "medium shot"})
    i = 0
    while len(clean) < want:
        clean.append(base["beats"][i % len(base["beats"])])
        i += 1
    # Hat boyunca "shots" adiyla tasiniyor (backend'ler bu anahtari kullaniyor).
    out["shots"] = clean[:want]

    tags = idea.get("hashtags") or base["hashtags"]
    tags = [t if str(t).startswith("#") else f"#{t}" for t in tags if str(t).strip()]
    out["hashtags"] = list(dict.fromkeys(tags))[:15]
    return out


def story_beats(idea: dict, n: int) -> list[dict]:
    """Ucretli yol icin hikayeyi tasiyan n vurusu secer.

    Ilk n vurusu almak dramayi olduruyordu: 6 vuruslu bir hikayeden ilk 2'sini
    almak sadece kurulumu verir, twist'i hic gostermez. Bunun yerine kancayi ve
    finali her zaman koruyup arasini esit araliklarla dolduruyoruz.
    """
    beats = idea["shots"]
    if n >= len(beats):
        return beats
    if n == 1:
        return [beats[0]]
    step = (len(beats) - 1) / (n - 1)
    return [beats[round(i * step)] for i in range(n)]


def shot_prompt(idea: dict, shot: dict) -> str:
    """Tek bir vurusu ureten tam gorsel istemi."""
    return (
        f"{idea['character']}. {shot['action']}. "
        f"Scene: {idea['setting']}. Camera: {shot['camera']}. "
        f"{idea['style']}. Vertical 9:16 composition, subjects fully in frame, "
        f"expressive faces, no text, no watermark, no letters, no speech bubbles."
    )
