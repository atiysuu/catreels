"""UCRETLI yol: gercek AI video klipleri (Pollinations gen ucu, Pollen harcar).

Fiyat, model x saniye uzerinden hesaplanir. Ornek: wan-fast 0.01 Pollen/sn
-> 4 klip x 5 sn = 0.20 Pollen (~0.20 USD). veo ise ~0.08 Pollen/sn.
Butce asilirsa ucretsiz yola dusmek icin main.py fallback uygular.
"""
import pathlib

from .. import assemble, ideas, log
from ..pollinations import PollinationsError, new_seed

# Modellerin Pollen/saniye fiyatlari (bilgi amacli; canli liste /models ucunda).
PRICE_PER_SEC = {
    "wan-fast": 0.01, "p-video": 0.02, "seedance-pro": 0.025,
    "minimax-h3": 0.05, "grok-video-pro": 0.07, "seedance-2.0-fast": 0.07,
    "wan-3.0": 0.068, "veo": 0.08, "nova-reel": 0.08,
    "seedance-2.0-mini": 0.09, "happyhorse-1.1": 0.0988,
    "wan": 0.10, "wan-pro": 0.10, "seedance-2.5": 0.1028,
    "grok-imagine-video-1.5": 0.14, "seedance-2.0": 0.18,
}


def estimate_cost(cfg, n_clips: int) -> float:
    return PRICE_PER_SEC.get(cfg.video_model, 0.10) * cfg.video_clip_seconds * n_clips


def _normalise_clip(src: pathlib.Path, dest: pathlib.Path, cfg) -> pathlib.Path:
    """Model ciktisi 480p/720p ve degisik en-boy olabilir; 9:16'ya oturt."""
    vf = (
        f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={cfg.width}:{cfg.height},unsharp=5:5:0.4:5:5:0.0,"
        f"setsar=1,fps={cfg.fps},format=yuv420p"
    )
    assemble.run(
        ["-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dest)],
        what=f"klip normalizasyonu ({src.name})",
    )
    return dest


def produce(client, cfg, idea: dict, workdir: pathlib.Path) -> pathlib.Path:
    seed = new_seed(cfg)
    # Video pahali: her cekim icin klip uretmek maliyeti katliyor. VIDEO_CLIPS
    # cekim sayisindan bagimsiz tutulur -- 6 cekimlik bir konseptten 2 klip
    # uretmek 16sn/0.40 $ demek, 6 klip 48sn/1.20 $ olurdu.
    n = max(1, min(len(idea["shots"]), cfg.video_clips))
    picks = idea["shots"][:n]

    cost = estimate_cost(cfg, len(picks))
    log.info(f"ucretli yol: model={cfg.video_model}, {len(picks)} klip x "
             f"{cfg.video_clip_seconds}sn, tahmini ~{cost:.2f} Pollen")

    raw_dir = workdir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    clips: list[pathlib.Path] = []
    for i, shot in enumerate(picks):
        prompt = ideas.shot_prompt(idea, shot)
        raw = raw_dir / f"v{i:02d}.mp4"
        try:
            client.video(prompt, raw, seed=seed, seconds=cfg.video_clip_seconds,
                         aspect="9:16", width=cfg.width, height=cfg.height)
            log.info(f"  klip {i:02d} hazir ({raw.stat().st_size // 1024}KB)")
        except PollinationsError as exc:
            log.warn(f"  klip {i:02d} uretilemedi: {exc}")
            continue
        clips.append(_normalise_clip(raw, workdir / f"clip{i:02d}.mp4", cfg))

    if not clips:
        raise RuntimeError("hicbir AI video klibi uretilemedi")

    return assemble.join_clips(clips, workdir / "joined.mp4", cfg)
