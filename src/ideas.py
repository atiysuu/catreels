"""Her calismada dizinin yeni bir BOLUMUNU yazar.

Tasarim degisikligi (ikinci tur): onceki surum her bolumde yeni kediler ve
yeni bir dunya uyduruyordu -- teknik olarak calisiyordu ama izleyen icin
birbirinden kopuk melodram parcalariydi. Baglanacak kimse yok, o yuzden
geri donmek icin sebep de yok.

Artik sitcom mantigi: sabit kadro (src/cast.py), sabit ev, gunluk hayattan
kucuk olaylar. Espri karakterden cikiyor -- Pasha'nin tembelligini bilince
kanepe sahnesinde ne yapacagini tahmin edip guluyorsun.

Model erisilemezse tamamen yerel sablonla devam edilir; hat asla durmaz.
"""
import json
import random

from . import cast, log
from .textgen import TextGenError, concept_json

# Gunluk hayattan sitcom durumlari. Melodram degil: kucuk, tanidik, komik.
SITUATIONS = [
    "the last treat in the bag and two cats who both want it",
    "someone knocked over the plant and nobody admits it",
    "a cardboard box arrives and becomes contested territory",
    "the sunny spot on the sofa is only big enough for one",
    "one of them starts a diet and the fridge disagrees",
    "the vet carrier comes out of the cupboard",
    "a fly gets into the flat and ruins everyone's afternoon",
    "someone ate the food that was clearly not theirs",
    "the vacuum cleaner comes on without warning",
    "a red laser dot appears and nobody can explain it",
    "the good blanket is claimed by the wrong cat",
    "a guest is coming and the flat is a disaster",
    "one of them gets stuck somewhere embarrassing",
    "the water bowl is empty and everyone blames everyone",
    "a new scratching post arrives and is immediately ignored",
    "someone is caught on the kitchen counter at midnight",
]

# Gorsel dil: FOTOGRAF dili, render dili degil.
#
# "photorealistic cinematic still" gibi ifadeler modeli CGI'a itiyordu --
# cikan kareler ust duzey render gibi duruyor, telefonla cekilmis kedi gibi
# degil. Cozum iki yonlu: (1) gercek ekipman ve isik dili, (2) KUSUR dili.
# AI hissinin asil kaynagi asiri kusursuzluk: fazla simetrik yuzler, fazla
# duzgun tuy. Bu yuzden hafif odak kaymasi, dogal grain, dagilmis tuy ve
# elde cekim gibi kusurlar acikca isteniyor.
STYLE_POOL = [
    "candid amateur photograph of real house cats, shot on a full-frame DSLR with "
    "a 50mm lens at f/2.0, available window light only, natural imperfect framing, "
    "slight handheld motion blur, visible sensor noise, real fur that is slightly "
    "messy and uneven, whisker detail, not CGI, not a 3D render, not an illustration",
    "documentary style photograph of real domestic cats in a real home, 35mm lens, "
    "mixed indoor lighting with a slightly blown-out window, subtle film grain, "
    "natural asymmetric faces, tufty uneven fur, a little dust in the air, "
    "candid unposed moment, not CGI, not a 3D render, not an illustration",
    "snapshot photograph of real cats caught mid-action, 50mm lens, slightly "
    "underexposed indoor light, mild motion blur on moving paws, realistic "
    "imperfect fur with small mats and stray hairs, believable everyday clutter, "
    "not CGI, not a 3D render, not an illustration",
]

SYSTEM = """You write episodes of an ongoing VERTICAL SITCOM in which all the characters
are cats sharing one small flat. You return ONLY a JSON object. No prose, no fence.

This is a SERIES, not a one-off. The same cats live in the same flat every episode.
You are given the cast; never invent new cats, never rename them, never change how they
look. Write them the way a sitcom writer writes regulars: the comedy comes from the
audience already knowing exactly how each one will react.

TONE: everyday domestic comedy. Small stakes, big reactions. Think flatmates arguing
over the last snack, not betrayal and revenge. Nothing tragic, nothing melodramatic,
no villains - just four cats being annoying to each other in a loving way.

THE FIRST BEAT MATTERS MOST: the viewer decides in 1.5 seconds. Open on the funniest or
most absurd image of the episode, mid-situation. Never a calm establishing shot.

Shape the beats like a joke, not like a tragedy:
  beat 1        the setup image - we see the problem immediately
  beats 2..n-2  escalation - it gets sillier, someone overreacts
  beat n-1      the turn - it goes wrong in an unexpected way
  beat n        the button - the final funny image, usually someone unbothered

Rules:
- EVERYTHING in ENGLISH. Global audience: no idioms or references that do not travel.
- Refer to the cats BY NAME in every beat, so the sequence reads as one story.
- SOMETHING MUST HAPPEN IN EVERY BEAT. A beat is never a cat holding a pose or simply
  looking at something. In each beat a cat MOVES and an OBJECT REACTS: something is
  knocked over, dragged, spilled, snatched, slammed, squeezed into, jumped onto, or
  sent rolling across the floor. Physical comedy, not portraits.
- Chain the beats by consequence: what an object does at the end of one beat causes
  the next one. The episode should feel like one accident gathering speed.
- Each beat is 12-22 words: who moves, what they do, what the object does, and the
  expression on their face. No speech, no thought bubbles, no text in the image.
- The cats are REAL, slightly overweight house cats caught on camera in a real flat.
  Never cartoon, never Pixar, never 3D render, never illustration. No clothing.
  Write the beats the way you would describe a real home video: cats land awkwardly,
  slip on smooth floors, knock things with their bodies rather than their paws, and
  their fur gets messed up. Avoid describing them as "adorable" or "cute" - let the
  situation be funny and let them look like actual animals.
- The caption should feel like a friend captioning their pets: light, funny, and it
  invites a reply. 1-2 short sentences, at most one emoji.
- The hook is AT MOST 26 characters including spaces, burned onto the video. Write it
  like a sitcom title card or a relatable complaint: "He sat on it again",
  "Nobody touched the plant". No emoji, no ending punctuation.
"""

USER_TMPL = """Write episode {episode} of the series.

Cast in this episode:
{roster}

Situation to build the episode around: {situation}
Location: {location}
Visual style for every beat: {style}
Do not repeat any of these recent episodes: {recent}

Return exactly this JSON shape:
{{
  "title": "short English slug-like title",
  "hook": "max 26 characters, sitcom title-card energy, burned onto the video",
  "beats": [
    {{"action": "English, one funny physical moment, cats named, visible expression",
      "camera": "English camera note, e.g. low angle close-up, wide shot"}}
  ],
  "caption": "light funny caption that invites a reply, 1-2 sentences, max one emoji",
  "hashtags": ["#cats", "#catsitcom", "8-14 English tags for a global audience"]
}}

The beats array must contain exactly {shots} items: setup -> escalation -> turn -> button."""


HOOKS = [
    "He sat on it again", "Nobody touched the plant", "It was not his food",
    "The box is mine now", "She panicked immediately", "Day one of the diet",
    "That was the last treat", "He has no regrets", "The sunny spot war",
]

CAPTIONS = [
    "Which one is your flatmate?", "Tell me you have this cat without telling me.",
    "This happens in my flat every single day.", "Whose side are you on?",
    "He is not even sorry.", "Rate the level of drama out of ten.",
]

# Yerel yedek: metin modeli hic calismasa bile kadro tanidik kalsin.
BEATS = [
    "{a} freezes mid-bite with the stolen snack still in his mouth, eyes enormous",
    "{b} stares at {a} without blinking, slowly tilting her head in disbelief",
    "{a} tries to casually sit on the evidence, pretending nothing happened",
    "{b} leans in closer, whiskers forward, refusing to look away",
    "{a} rolls onto his back in mock innocence, paws in the air",
    "{b} walks off with the last piece while {a} watches, defeated",
]

# Model "no text" ifadesini yalnizca EKRANA BINDIRILEN yazi olarak anliyor;
# sahnedeki kutu, poset ve kavanozlarin uzerine yine marka basiyor ve o
# yazilar bozuk cikiyor ("Oateth", "Roucitt"). Duran karede hemen belli
# oluyor, o yuzden ambalajin kendisini sade istiyoruz.
NO_TEXT = (
    "No text anywhere in the frame: no on-screen captions, no watermarks, no logos. "
    "All packaging, jars, boxes, bags and labels must be plain and unbranded with "
    "blank surfaces - never any printed words, letters or numbers on any object."
)

CAMERAS = ["low angle close-up", "medium shot, eye level", "wide shot, slight high angle",
           "extreme close-up on the face", "over-the-shoulder medium shot"]


def _fallback(pair, situation: str, location: str, style: str, shots: int) -> dict:
    a, b = (cast.CAST[pair[0]]["name"], cast.CAST[pair[1]]["name"])
    return {
        "title": situation[:40],
        "hook": random.choice(HOOKS),
        "beats": [{"action": BEATS[i % len(BEATS)].format(a=a, b=b),
                   "camera": CAMERAS[i % len(CAMERAS)]}
                  for i in range(shots)],
        "caption": random.choice(CAPTIONS),
        "hashtags": ["#cats", "#catsitcom", "#catsofinstagram", "#funnycats",
                     "#cutecats", "#chubbycat", "#catlovers", "#catreels",
                     "#catcomedy", "#catlife", "#aicat", "#catvideos"],
        "_fallback": True,
    }


def generate(client, cfg, history: list[str], episode: int = 1,
             recent_casts: list[list[str]] | None = None) -> dict:
    # Rastgele secim ust uste ayni ikiliyi verebiliyor; dizide bu monotonluk
    # yaratir. Son iki bolumde kullanilan ikilileri eleyip oyle seciyoruz.
    used = {tuple(sorted(c)) for c in (recent_casts or [])[-2:]}
    havuz = [p for p in cast.PAIRINGS if tuple(sorted(p)) not in used] or cast.PAIRINGS
    pair = random.choice(havuz)
    situation = random.choice(SITUATIONS)
    location = random.choice(cast.LOCATIONS)
    style = random.choice(STYLE_POOL)
    recent = ", ".join(history[-12:]) or "none"

    prompt = USER_TMPL.format(episode=episode, roster=cast.roster(list(pair)),
                              situation=situation, location=location,
                              style=style, recent=recent, shots=cfg.shots)
    try:
        idea = concept_json(client, cfg, SYSTEM, prompt)
    except (TextGenError, json.JSONDecodeError) as exc:
        log.warn(f"fikir modeli kullanilamadi ({exc}); yerel sablona dusuluyor")
        idea = _fallback(pair, situation, location, style, cfg.shots)

    idea = _normalise(idea, pair, situation, location, style, cfg.shots, episode)
    log.info(f"bolum {episode}: {cast.names(list(pair))} -- {idea['title']} "
             f"| kanca: {idea['hook']!r}")
    return idea


def _normalise(idea: dict, pair, situation: str, location: str, style: str,
               want: int, episode: int) -> dict:
    base = _fallback(pair, situation, location, style, want)
    keys = list(pair)
    out = {
        "episode": episode,
        "cast": keys,
        "situation": situation,
        "style": style,
        "title": str(idea.get("title") or base["title"])[:80],
        "hook": str(idea.get("hook") or base["hook"]).strip().rstrip(".!?")[:30],
        # Karakter tarifi MODELDEN GELMEZ: kadro dosyasindan birebir gelir.
        # Diziyi dizi yapan sey bu -- her bolumde ayni kediler.
        "character": cast.describe(keys),
        "setting": location,
        "caption": str(idea.get("caption") or base["caption"]),
        "used_fallback": bool(idea.get("_fallback")),
    }

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
    out["shots"] = clean[:want]

    tags = idea.get("hashtags") or base["hashtags"]
    tags = [t if str(t).startswith("#") else f"#{t}" for t in tags if str(t).strip()]
    out["hashtags"] = list(dict.fromkeys(tags))[:15]
    return out


SECONDS_PER_SCENE = 2.0   # bir sahnenin okunabilmesi icin gereken en az sure


def distribute_beats(idea: dict, n_clips: int,
                     clip_seconds: float = 4.0) -> list[list[dict]]:
    """Vuruslari kliplere pay eder -- her klip birden fazla sahne tasiyabilir.

    Vurus SECMEK yerine PAYLASTIRIYORUZ: video modeli tek uretimde sahne
    kesmesi yapabildigi icin 3 klip x 2 vurus = 6 vurusun tamami, ayni
    fiyata iki kat hikaye.
    """
    beats = idea["shots"]
    n_clips = max(1, min(n_clips, len(beats)))
    per = len(beats) / n_clips
    groups: list[list[dict]] = []
    for i in range(n_clips):
        start = round(i * per)
        end = round((i + 1) * per) if i < n_clips - 1 else len(beats)
        chunk = beats[start:end] or [beats[min(start, len(beats) - 1)]]
        # Bir klibe kac sahne sigar: suresine bagli. 4sn'lik klip 2 sahne,
        # 15sn'lik tek klip 7 sahne tasiyabiliyor. Sabit 2 siniri, tek uzun
        # klip kullanildiginda bolumun buyuk kismini cope atiyordu.
        cap = max(1, int(clip_seconds / SECONDS_PER_SCENE))
        if len(chunk) > cap:
            # Kirparken ilk ve son mutlaka kalsin (kanca + button), arasi esit
            # araliklarla secilsin.
            step = (len(chunk) - 1) / (cap - 1) if cap > 1 else 1
            chunk = [chunk[round(i * step)] for i in range(cap)]
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
        f"{idea['character']} A fast-paced {len(beats)}-shot sequence with a hard cut "
        f"between every shot, each shot roughly equal length. {shots} "
        f"Keep the same cats, the same room and the same lighting across both shots. "
        f"Scene: {idea['setting']}. {idea['style']}. "
        f"Vertical 9:16 composition, subjects fully in frame, expressive faces. "
        f"{NO_TEXT}"
    )


def shot_prompt(idea: dict, shot: dict) -> str:
    """Tek bir vurusu ureten tam gorsel istemi."""
    return (
        f"{idea['character']} {shot['action']}. "
        f"Scene: {idea['setting']}. Camera: {shot['camera']}. "
        f"{idea['style']}. Vertical 9:16 composition, subjects fully in frame, "
        f"expressive faces. {NO_TEXT}"
    )
