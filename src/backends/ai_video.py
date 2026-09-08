"""UCRETLI yol: gercek AI video klipleri (Pollinations gen ucu, Pollen harcar).

Fiyat, model x saniye uzerinden hesaplanir. Ornek: wan-fast 0.01 Pollen/sn
-> 4 klip x 5 sn = 0.20 Pollen (~0.20 USD). veo ise ~0.08 Pollen/sn.
Butce asilirsa ucretsiz yola dusmek icin main.py fallback uygular.
"""
import pathlib

from .. import assemble, ideas, log
from ..pollinations import PollinationsError, new_seed

# Modellerin Pollen/saniye fiyatlari (bilgi amacli; canli liste /models ucunda).
# DIKKAT: bazi modellerde fiyat COZUNURLUGE gore degisiyor. seedance-2.5
# 480p'de 0.1028 $/sn, 720p'de 0.2312 $/sn -- iki katindan fazla.
# Varsayilan 480p; VIDEO_RESOLUTION=720p maliyeti 2.25x yapiyor.
PRICE_BY_RES = {
    ("seedance-2.5", "480p"): 0.1028,
    ("seedance-2.5", "720p"): 0.2312,
}

PRICE_PER_SEC = {
    "wan-fast": 0.01, "p-video": 0.02, "seedance-pro": 0.025,
    "minimax-h3": 0.05, "grok-video-pro": 0.07, "seedance-2.0-fast": 0.07,
    "wan-3.0": 0.068, "veo": 0.08, "nova-reel": 0.08,
    "seedance-2.0-mini": 0.09, "happyhorse-1.1": 0.0988,
    "wan": 0.10, "wan-pro": 0.10, "seedance-2.5": 0.1028,
    "grok-imagine-video-1.5": 0.14, "seedance-2.0": 0.18,
}


# Modellerin dikey (9:16) istek boyutu. Modelin desteklemedigi bir cozunurluk
# istemek ya hata veriyor ya sessizce dusuruluyor; ikisi de kotu. Cikti tuvali
# yine 1080x1920 kalir, klipler montajda lanczos+cas ile buyutulur -- Instagram
# 1080x1920 bekliyor ve kendi olceklemesini yapmasindansa biz yapalim.
RES_SIZE = {"480p": (480, 854), "720p": (720, 1280), "1080p": (1080, 1920)}


def request_size(cfg) -> tuple[int, int]:
    return RES_SIZE.get(cfg.video_resolution, (cfg.width, cfg.height))


def price_per_second(cfg) -> float:
    key = (cfg.video_model, cfg.video_resolution)
    if key in PRICE_BY_RES:
        return PRICE_BY_RES[key]
    return PRICE_PER_SEC.get(cfg.video_model, 0.10)


def estimate_cost(cfg, n_clips: int) -> float:
    return price_per_second(cfg) * cfg.video_clip_seconds * n_clips


def _normalise_clip(src: pathlib.Path, dest: pathlib.Path, cfg) -> pathlib.Path:
    """Model ciktisi 480p/720p ve degisik en-boy olabilir; 9:16'ya oturt."""
    vf = (
        f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={cfg.width}:{cfg.height},unsharp=5:5:0.4:5:5:0.0,"
        f"setsar=1,fps={cfg.fps},format=yuv420p"
    )
    # Modelin urettigi ses KORUNUYOR. seedance-2.5 gibi sesli modellerde bu
    # ses kullanicinin asil odedigi sey; -an ile atmak modeli anlamsiz kilardi.
    # Sessiz modellerde ses akisi zaten yok, "-c:a aac" zararsiz.
    assemble.run(
        ["-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         str(dest)],
        what=f"klip normalizasyonu ({src.name})",
    )
    return dest


def produce(client, cfg, idea: dict, workdir: pathlib.Path) -> pathlib.Path:
    seed = new_seed(cfg)
    # Video pahali: her vurus icin klip uretmek maliyeti katliyor. VIDEO_CLIPS
    # vurus sayisindan bagimsiz -- 6 vurusluk konseptten 2 klip 16sn/0.40 $,
    # 6 klip ise 48sn/1.20 $ olurdu.
    #
    # Vuruslar SECILMIYOR, PAYLASTIRILIYOR: model tek uretimde sahne kesmesi
    # yapabildigi icin her klip iki vurus tasiyabiliyor. 3 klip x 2 vurus =
    # 6 vurusun tamami, ayni fiyata iki kat hikaye. (Onceden story_beats ile
    # sadece n vurus seciliyordu, gerisi cope gidiyordu.)
    n = max(1, min(len(idea["shots"]), cfg.video_clips))
    groups = ideas.distribute_beats(idea, n)

    cost = estimate_cost(cfg, len(groups))
    total_beats = sum(len(g) for g in groups)
    log.info(f"ucretli yol: model={cfg.video_model}, {len(groups)} klip x "
             f"{cfg.video_clip_seconds}sn ({total_beats} vurus), "
             f"tahmini ~{cost:.2f} Pollen")

    rw, rh = request_size(cfg)
    if (rw, rh) != (cfg.width, cfg.height):
        log.info(f"  {cfg.video_model} en fazla {rw}x{rh} veriyor; "
                 f"montajda {cfg.width}x{cfg.height}'e buyutulecek")

    raw_dir = workdir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    clips: list[pathlib.Path] = []
    for i, beats in enumerate(groups):
        prompt = ideas.clip_prompt(idea, beats)
        raw = raw_dir / f"v{i:02d}.mp4"
        try:
            client.video(prompt, raw, seed=seed, seconds=cfg.video_clip_seconds,
                         aspect="9:16", width=rw, height=rh,
                         resolution=cfg.video_resolution)
            log.info(f"  klip {i:02d} hazir ({raw.stat().st_size // 1024}KB)")
        except PollinationsError as exc:
            log.warn(f"  klip {i:02d} uretilemedi: {exc}")
            continue
        clips.append(_normalise_clip(raw, workdir / f"clip{i:02d}.mp4", cfg))

    if not clips:
        raise RuntimeError("hicbir AI video klibi uretilemedi")

    # Gecis yok: 2 x 4sn klip tam 8.00sn kalsin ve kanca->odeme sert kessin.
    return assemble.join_clips(clips, workdir / "joined.mp4", cfg, transition=0)
