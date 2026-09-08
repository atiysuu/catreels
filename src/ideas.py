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
# Cizgi film / Pixar secenekleri KALDIRILDI -- istenen sey gercek kedi
# dokusuna sahip, sinematik isikta cekilmis tombik kediler.
STYLE_POOL = [
    "photorealistic cinematic still, 85mm lens, real fluffy cat fur with visible individual "
    "hairs, soft window light, creamy bokeh, shallow depth of field, natural colours",
    "hyperreal photograph, 50mm lens, moody telenovela lighting with warm key and cool "
    "shadows, real cat fur texture, subtle film grain, shallow depth of field",
    "photorealistic cinematic still, golden hour light through a window, real cat fur "
    "detail, warm natural tones, gentle rim light, shallow depth of field",
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
- EVERYTHING you write is in ENGLISH. The account is global, so avoid culture-specific
  references, idioms and wordplay that do not travel.
- The caption must invite a reply: a question, a hot take, or a "who else has been here"
  energy. 1-2 short sentences, at most one emoji.
- The hook is AT MOST 26 characters including spaces. It is burned onto the first seconds
  of the video, so it must fit. Write it as an open loop, not a summary:
  "Someone was in there" beats "The cat was cheating". No emoji, no ending punctuation.
- The character field is the single most important one: one dense sentence describing the
  cat(s) so precisely (breed, fur colour and pattern, eye colour, body shape) that the
  model draws the SAME cat every time. If there are two cats, describe BOTH distinctly in
  that one sentence. Never change it between beats.
- The cats MUST be CHUBBY, round-faced and adorable -- plush cheeks, soft bellies, big
  round eyes. They must look like REAL cats photographed on a real set: never cartoon,
  never Pixar, never 3D render, never illustration. Do not dress them in clothes;
  expressive faces and body language carry the drama.
- Each beat's action is ONE clear physical moment with visible emotion, 10-20 words.
  Name who is doing what, and show feeling through body language and face - no thought
  bubbles, no speech, no text in the image.
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
  "hook": "max 26 characters, an open loop, burned onto the video",
  "character": "one dense English sentence; if two cats, both described distinctly",
  "setting": "one English sentence describing the location and lighting",
  "beats": [
    {{"action": "English, one clear dramatic moment with visible emotion",
      "camera": "English camera note, e.g. low angle close-up, wide shot"}}
  ],
  "caption": "caption that invites a reply, 1-2 sentences, max one emoji",
  "hashtags": ["#cat", "#cats", "8-14 English tags for a global audience"]
}}

The beats array must contain exactly {shots} items, following hook -> escalation ->
turn -> payoff."""


# --- yerel yedek havuzlari (metin modeli hic calismasa bile drama cikar) ----

CHARACTERS = [
    ("a very chubby round orange tabby cat with plush cheeks, a soft belly and huge round "
     "amber eyes, and an equally chubby fluffy white cat with a rosy pink nose and big blue eyes"),
    ("a plump grey British Shorthair with round copper eyes and thick velvety fur, and a "
     "chubby cream Ragdoll with a fluffy tail and gentle blue eyes"),
    ("a roly-poly ginger cat with a big round face and short legs, and a small tubby "
     "tuxedo cat with white mittens and wide green eyes"),
    ("a fat fluffy calico cat with soft round cheeks and warm hazel eyes, and a stocky "
     "silver tabby with a broad face and big golden eyes"),
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
    "aldatma": ["Someone was in there", "I opened the door", "I saw the photo"],
    "sevgili": ["The box was empty", "He waited for hours", "She almost said it"],
    "kovulma": ["I got fired today", "The boss laughed", "He came back later"],
    "zengin": ["Yesterday he was broke", "They turned him away", "The ticket was real"],
    "intikam": ["They all laughed", "Then he stepped up", "The trap backfired"],
    "komik": ["The diet starts today", "Caught at midnight", "He never let go"],
}

CAPTIONS = {
    "aldatma": ["What would you have done?", "Has this ever happened to you?"],
    "sevgili": ["This should be illegal levels of cute.", "Ever waited this long?"],
    "kovulma": ["Everyone has a boss story. What is yours?", "That ending though."],
    "zengin": ["Never underestimate anyone.", "Did you see that coming?"],
    "intikam": ["Best comeback ever?", "Did you catch their faces?"],
    "komik": ["This cat is all of us.", "How long did your diet last?"],
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
        "hashtags": ["#cat", "#cats", "#catsofinstagram", "#catlovers", "#funnycats",
                     "#catdrama", "#cutecats", "#chubbycat", "#catreels", "#aicat",
                     "#catvideos", "#catlife"],
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


def distribute_beats(idea: dict, n_clips: int) -> list[list[dict]]:
    """6 vurusu n klibe pay eder -- her klip birden fazla sahne tasiyabilir.

    story_beats() vurus SECIYORDU, yani 3 klipte hikayenin yarisi cope
    gidiyordu. Video modeli tek uretimde sahne kesmesi yapabildigi icin
    artik vuruslari SIKISTIRIYORUZ: 3 klip x 2 vurus = 6 vurusun tamami,
    ayni fiyata iki kat hikaye.
    """
    beats = idea["shots"]
    n_clips = max(1, min(n_clips, len(beats)))
    per = len(beats) / n_clips
    groups: list[list[dict]] = []
    for i in range(n_clips):
        start = round(i * per)
        end = round((i + 1) * per) if i < n_clips - 1 else len(beats)
        chunk = beats[start:end] or [beats[min(start, len(beats) - 1)]]
        # Tek klipte ikiden fazla sahne 4 saniyede okunmuyor. Kirparken
        # ILK IKIYI degil, ILK ve SON vurusu aliyoruz: aksi halde 2 klipte
        # son grup [4,5] olup finali (6) dusuruyordu.
        if len(chunk) > 2:
            chunk = [chunk[0], chunk[-1]]
        groups.append(chunk)
    return groups


def clip_prompt(idea: dict, beats: list[dict]) -> str:
    """Bir video klibinin istemi. Birden fazla vurus varsa sahne kesmesi ister."""
    if len(beats) == 1:
        return shot_prompt(idea, beats[0])

    shots = " ".join(
        f"Shot {i}: {b['action']} ({b['camera']})."
        for i, b in enumerate(beats, 1)
    )
    return (
        f"{idea['character']}. A {len(beats)}-shot sequence with one hard cut between "
        f"the shots, each shot held for about half the clip. {shots} "
        f"Keep the same cats, the same room and the same lighting across both shots. "
        f"Scene: {idea['setting']}. {idea['style']}. "
        f"Vertical 9:16 composition, subjects fully in frame, expressive faces, "
        f"no text, no watermark, no letters, no speech bubbles."
    )


def shot_prompt(idea: dict, shot: dict) -> str:
    """Tek bir vurusu ureten tam gorsel istemi."""
    return (
        f"{idea['character']}. {shot['action']}. "
        f"Scene: {idea['setting']}. Camera: {shot['camera']}. "
        f"{idea['style']}. Vertical 9:16 composition, subjects fully in frame, "
        f"expressive faces, no text, no watermark, no letters, no speech bubbles."
    )
