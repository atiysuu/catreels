"""Her calismada yeni bir kedi konsepti uretir.

Once yerel bir tohum havuzundan rastgele bir cekirdek fikir secilir, sonra
metin modeli bunu tam bir cekim listesine + Turkce aciklamaya genisletir.
Model erisilemezse tamamen yerel sablonla devam edilir; hat asla durmaz.
"""
import json
import random

from . import log
from .textgen import TextGenError, concept_json

THEMES = {
    "dans": [
        "iki kedi disko toplari altinda senkronize dans ediyor",
        "smokinli bir kedi balo salonunda tek basina vals yapiyor",
        "sokak kedisi breakdance yapiyor, etrafinda hayran kediler",
        "kedi 1980ler aerobik dersinde bandana takmis dans ediyor",
        "yagmurda semsiyeyle tap dans yapan kedi",
    ],
    "ask": [
        "iki kedi mum isiginda spagetti paylasiyor",
        "kedi sevgilisine cati katinda gul uzatiyor",
        "yagmurda ayni semsiye altinda birbirine sokulan iki kedi",
        "kedi deniz kenarinda gun batiminda evlenme teklif ediyor",
        "sinemada patilerini tutan kedi cifti",
    ],
    "karikoca": [
        "kedi karisi kocasini gece yarisi buzdolabi basinda yakaliyor",
        "kedi cift televizyon kumandasi icin kavga ediyor",
        "kedi koca sabah kahvaltisini yakiyor, karisi kaslarini kaldiriyor",
        "kedi cift mobilya kurmaya calisiyor ve pes ediyor",
        "kedi karisi alisveris torbalariyla eve giriyor, koca faturaya bakiyor",
    ],
    "arkadas": [
        "dort kedi kanepede pizza yiyip mac izliyor",
        "kedi arkadaslar kamp atesinde korkunc hikaye anlatiyor",
        "kedi grubu karaoke yapiyor, biri mikrofonu birakmiyor",
        "kedi arkadaslar market arabasiyla yokus asagi kayiyor",
        "kedi cetesi gece yarisi mutfakta gizlice pasta yiyor",
    ],
}

# Gorsel dil: her cekimde ayni kalmali ki kedi ayni kedi gorunsun.
STYLE_POOL = [
    "cinematic 3D animated film still, Pixar-quality fur shading, soft rim light, shallow depth of field",
    "hyperreal photograph, 85mm lens, warm golden hour light, creamy bokeh, photorealistic cat fur",
    "cozy stop-motion felt puppet look, tilt-shift miniature set, practical lighting",
    "vibrant 2D-3D hybrid cartoon, bold outlines, saturated palette, studio lighting",
]

SYSTEM = """You are a viral short-form video director specialising in cute AI cat Reels.
You return ONLY a JSON object. No prose, no markdown fence.

Rules:
- All visual text MUST be in English (image models are trained on English).
- The caption MUST be in Turkish, warm and playful, 1-2 short sentences, at most one emoji.
- The hook MUST be in Turkish, AT MOST 26 characters including spaces. It is burned
  onto the first seconds of the video, so it has to fit on screen: 3-4 short words,
  no emoji, no punctuation at the end. Think of it as a thumbnail headline.
- The character field is the single most important one: one dense English sentence describing
  the cat(s) so precisely (breed, fur colour and pattern, eye colour, body shape,
  clothing/accessory) that a text-to-image model draws the SAME cat every time.
  Never change it between shots.
- Each shot action describes ONE clear physical pose or movement, in English, 8-18 words.
  Consecutive shots must be small steps of the same continuous motion, not unrelated scenes.
- Keep the whole thing wholesome and funny. No text or letters inside the image.
"""

USER_TMPL = """Build a {shots}-shot vertical Reel concept.

Theme: {theme}
Seed idea: {seed_idea}
Visual style to keep in every shot: {style}
Avoid repeating any of these recent titles: {recent}

Return exactly this JSON shape:
{{
  "title": "short English slug-like title",
  "hook": "Turkish, max 26 characters, burned onto the video",
  "character": "one dense English sentence, the same cat(s) in every shot",
  "setting": "one English sentence describing the location and lighting",
  "shots": [
    {{"action": "English, one clear pose or movement", "camera": "English camera note, e.g. medium shot, low angle"}}
  ],
  "caption": "Turkish caption, playful, 1-2 sentences, max one emoji",
  "hashtags": ["#kedi", "#cat", "8-14 mixed Turkish and English tags"]
}}

The shots array must contain exactly {shots} items."""


# --- yerel yedek havuzlari (metin modeli hic calismasa bile cesitlilik) ----

CHARACTERS = [
    "a chubby orange tabby cat with white chest fur, huge round green eyes, tiny pink nose, wearing a small red bow tie",
    "a fluffy grey British Shorthair cat with copper eyes, round cheeks, wearing a tiny denim jacket",
    "a sleek black cat with bright yellow eyes and one white paw, wearing gold hoop earrings",
    "a cream Ragdoll cat with sapphire blue eyes and long silky fur, wearing a knitted scarf",
    "a small calico kitten with mismatched eyes, orange and black patches, wearing oversized round glasses",
    "a plump Scottish Fold cat with folded ears, amber eyes, wearing a chef apron",
]

SETTINGS = {
    "dans": [
        "a neon-lit 1980s disco floor, mirror ball throwing light across the room",
        "a grand ballroom with chandeliers and polished marble floor",
        "a rain-slicked night street under a glowing lamp post",
    ],
    "ask": [
        "a rooftop terrace at sunset, string lights and a small table for two",
        "a candlelit italian restaurant, warm amber glow, soft shadows",
        "a quiet beach at golden hour, gentle waves in the background",
    ],
    "karikoca": [
        "a cosy kitchen at midnight, only the open fridge lighting the room",
        "a lived-in living room with a worn sofa and a flickering television",
        "a cluttered bedroom in the morning, sunlight through half-open blinds",
    ],
    "arkadas": [
        "a messy living room full of snacks, game controllers and blankets",
        "a campsite at night around a crackling fire, sparks rising",
        "a bright kitchen at 2am, cake crumbs everywhere",
    ],
}

# Ekrana basilan kanca: en fazla 26 karakter, yoksa kadraja sigmiyor.
HOOKS = {
    "dans": ["Bu ritme dayanamadi", "Kedi dansi basliyor", "Sesi acmadan izleme"],
    "ask": ["Bu kadar tatli olamaz", "Ask boyle bir sey", "Kalbim eridi"],
    "karikoca": ["Her evde bu sahne", "Evli olan anlar", "Tanidik geldi mi"],
    "arkadas": ["Grupta boyle biri var", "Kaos basliyor", "Bizim grup aynen bu"],
}

CAPTIONS = {
    "dans": ["Bu ritme dayanamadim.", "Kedi dans ederse boyle eder.",
             "Sesi ac, ayaklarin duramayacak."],
    "ask": ["Bu kadar tatli olmasi yasak olmali.", "Ask dedigin tam olarak bu.",
            "Kalbim eridi resmen."],
    "karikoca": ["Her evde yasanan sahne.", "Bu tartismayi hepimiz biliyoruz.",
                 "Evli olan anlar."],
    "arkadas": ["Arkadas grubunda mutlaka boyle biri var.",
                "Kaosun tanimi bu olsa gerek.", "Bizim grup aynen boyle."],
}

BEATS = [
    "standing still, looking at the camera, tail curled",
    "leaning to the left, one paw raised",
    "mid-motion, both paws up, joyful expression",
    "spinning, fur and whiskers in motion",
    "leaning to the right, head tilted",
    "jumping, all paws off the ground",
    "landing softly, big satisfied smile",
    "sitting down, blinking slowly at the camera",
]

CAMERAS = ["medium shot, eye level", "close-up, low angle",
           "wide shot, slight high angle", "medium close-up, eye level"]


def _fallback(theme: str, seed_idea: str, style: str, shots: int) -> dict:
    """Metin modeli olmadan da calisan, kendi icinde cesitli yedek konsept."""
    return {
        "title": seed_idea[:40],
        "hook": random.choice(HOOKS.get(theme, HOOKS["dans"])),
        "character": random.choice(CHARACTERS),
        "setting": random.choice(SETTINGS.get(theme, SETTINGS["dans"])),
        "shots": [{"action": BEATS[i % len(BEATS)], "camera": CAMERAS[i % len(CAMERAS)]}
                  for i in range(shots)],
        "caption": random.choice(CAPTIONS.get(theme, CAPTIONS["dans"])),
        "hashtags": ["#kedi", "#cat", "#catsofinstagram", "#kedistagram", "#aicat",
                     "#yapayzeka", "#reels", "#kedivideolari", "#funnycats", "#cute",
                     "#kedisevgisi", "#catlovers"],
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
    log.info(f"konsept: [{theme}] {idea['title']} ({len(idea['shots'])} cekim)")
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
        "hook": str(idea.get("hook") or base["hook"]).strip().rstrip(".!")[:30],
        "character": str(idea.get("character") or base["character"]),
        "setting": str(idea.get("setting") or base["setting"]),
        "caption": str(idea.get("caption") or base["caption"]),
        "used_fallback": bool(idea.get("_fallback")),
    }

    shots = idea.get("shots") or []
    clean = []
    for s in shots:
        if isinstance(s, dict) and s.get("action"):
            clean.append({"action": str(s["action"]),
                          "camera": str(s.get("camera") or "medium shot")})
        elif isinstance(s, str) and s.strip():
            clean.append({"action": s.strip(), "camera": "medium shot"})
    # Eksikse yedekten tamamla, fazlaysa kirp.
    i = 0
    while len(clean) < want:
        clean.append(base["shots"][i % len(base["shots"])])
        i += 1
    out["shots"] = clean[:want]

    tags = idea.get("hashtags") or base["hashtags"]
    tags = [t if str(t).startswith("#") else f"#{t}" for t in tags if str(t).strip()]
    out["hashtags"] = list(dict.fromkeys(tags))[:15]
    return out


def shot_prompt(idea: dict, shot: dict) -> str:
    """Tek bir kareyi ureten tam gorsel istemi."""
    return (
        f"{idea['character']}. {shot['action']}. "
        f"Scene: {idea['setting']}. Camera: {shot['camera']}. "
        f"{idea['style']}. Vertical 9:16 composition, subject fully in frame, "
        f"no text, no watermark, no letters, no signature."
    )
